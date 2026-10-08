import logging
from typing import Any, Dict, List, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from app.config import MONGODB_URI, MONGODB_DATABASE

logger = logging.getLogger("database")

REQUIRED_COLLECTIONS = [
    "hospitals",
    "readings",
    "predictions",
    "recommendations",
    "evaluation_runs",
    "audit_trail",
]

class InMemoryCollection:
    def __init__(self, name: str):
        self.name = name
        self.docs: List[Dict[str, Any]] = []

    def insert_one(self, doc: Dict[str, Any]):
        doc_copy = dict(doc)
        if "_id" not in doc_copy:
            doc_copy["_id"] = f"{self.name}_{len(self.docs) + 1}"
        self.docs.append(doc_copy)
        class Result:
            inserted_id = doc_copy["_id"]
        return Result()

    def insert_many(self, docs: List[Dict[str, Any]]):
        inserted_ids = []
        for doc in docs:
            res = self.insert_one(doc)
            inserted_ids.append(res.inserted_id)
        class Result:
            inserted_ids = inserted_ids
        return Result()

    def find(self, query: Optional[Dict[str, Any]] = None, sort: Optional[List] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        results = []
        for doc in self.docs:
            match = True
            if query:
                for k, v in query.items():
                    if doc.get(k) != v:
                        match = False
                        break
            if match:
                res = dict(doc)
                if "_id" in res and not isinstance(res["_id"], str):
                    res["_id"] = str(res["_id"])
                results.append(res)
        
        if sort:
            for key, direction in reversed(sort):
                results.sort(key=lambda x: x.get(key, 0), reverse=(direction == -1))
        
        if limit is not None:
            results = results[:limit]
        return results

    def find_one(self, query: Optional[Dict[str, Any]] = None, sort: Optional[List] = None) -> Optional[Dict[str, Any]]:
        res = self.find(query=query, sort=sort, limit=1)
        return res[0] if res else None

    def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False):
        set_vals = update.get("$set", {})
        for doc in self.docs:
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                doc.update(set_vals)
                class Result:
                    matched_count = 1
                    modified_count = 1
                    upserted_id = None
                return Result()
        
        # If no document matched and upsert=True, insert new document
        if upsert:
            new_doc = dict(query)
            new_doc.update(set_vals)
            if "_id" not in new_doc:
                new_doc["_id"] = f"{self.name}_{len(self.docs) + 1}"
            self.docs.append(new_doc)
            class Result:
                matched_count = 0
                modified_count = 0
                upserted_id = new_doc["_id"]
            return Result()

        class Result:
            matched_count = 0
            modified_count = 0
            upserted_id = None
        return Result()

    def delete_many(self, query: Optional[Dict[str, Any]] = None):
        if not query:
            count = len(self.docs)
            self.docs.clear()
            class Result:
                deleted_count = count
            return Result()
        new_docs = []
        deleted = 0
        for doc in self.docs:
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                deleted += 1
            else:
                new_docs.append(doc)
        self.docs = new_docs
        class Result:
            deleted_count = deleted
        return Result()

    def count_documents(self, query: Optional[Dict[str, Any]] = None) -> int:
        return len(self.find(query=query))

    def create_index(self, *args, **kwargs):
        return "index_created"


class MongoCollectionWrapper:
    """
    Wraps PyMongo collection to protect callers from in-place mutation with non-serializable ObjectId
    and normalize document formatting.
    """
    def __init__(self, raw_col):
        self.raw = raw_col

    def insert_one(self, doc: Dict[str, Any]):
        doc_copy = dict(doc)
        res = self.raw.insert_one(doc_copy)
        return res

    def insert_many(self, docs: List[Dict[str, Any]]):
        docs_copy = [dict(d) for d in docs]
        return self.raw.insert_many(docs_copy)

    def find(self, query: Optional[Dict[str, Any]] = None, sort: Optional[List] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        cursor = self.raw.find(query or {})
        if sort:
            cursor = cursor.sort(sort)
        if limit is not None:
            cursor = cursor.limit(limit)
        results = []
        for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results

    def find_one(self, query: Optional[Dict[str, Any]] = None, sort: Optional[List] = None) -> Optional[Dict[str, Any]]:
        res = self.raw.find_one(query or {}, sort=sort)
        if res and "_id" in res:
            res["_id"] = str(res["_id"])
        return res

    def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False):
        return self.raw.update_one(query, update, upsert=upsert)

    def delete_many(self, query: Optional[Dict[str, Any]] = None):
        return self.raw.delete_many(query or {})

    def count_documents(self, query: Optional[Dict[str, Any]] = None) -> int:
        return self.raw.count_documents(query or {})

    def create_index(self, *args, **kwargs):
        try:
            return self.raw.create_index(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Index creation notice: {e}")
            return str(e)


class DatabaseManager:
    def __init__(self):
        self.is_connected: bool = False
        self.mode: str = "DEMO FALLBACK"
        self.client: Optional[MongoClient] = None
        self.db = None
        self.last_error: Optional[str] = None
        self.in_memory_collections: Dict[str, InMemoryCollection] = {
            col: InMemoryCollection(col) for col in REQUIRED_COLLECTIONS
        }

    def connect(self, uri: Optional[str] = None):
        """Attempts connection to MongoDB Atlas with graceful fallback."""
        target_uri = uri if uri is not None else MONGODB_URI
        target_db_name = MONGODB_DATABASE
        if not target_uri:
            logger.info("No MONGODB_URI configured. Operating in DEMO FALLBACK mode (In-Memory).")
            self.is_connected = False
            self.mode = "DEMO FALLBACK"
            self.last_error = "MONGODB_URI not set"
            return

        try:
            logger.info(f"Connecting to MongoDB Atlas (database: {target_db_name})...")
            self.client = MongoClient(target_uri, serverSelectionTimeoutMS=3000)
            # Verify connectivity via ping command
            self.client.admin.command('ping')
            self.db = self.client[target_db_name]
            self.is_connected = True
            self.mode = "CONNECTED"
            self.last_error = None
            logger.info("Successfully connected to MongoDB Atlas!")

            # Initialize indexes on required collections
            self._ensure_indexes()

        except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
            self.last_error = str(e)
            logger.warning(f"Could not connect to MongoDB Atlas ({e}). Falling back safely to in-memory store.")
            self.is_connected = False
            self.mode = "DEMO FALLBACK"
            self.client = None
            self.db = None

    def _ensure_indexes(self):
        if not self.is_connected or self.db is None:
            return
        try:
            self.db["readings"].create_index([("hospital_id", 1), ("tick", -1)])
            self.db["readings"].create_index([("timestamp", -1)])
            self.db["predictions"].create_index([("hospital_id", 1), ("timestamp", -1)])
            self.db["recommendations"].create_index([("id", 1)])
            self.db["hospitals"].create_index([("id", 1)], unique=True)
            self.db["evaluation_runs"].create_index([("timestamp", -1)])
            self.db["audit_trail"].create_index([("timestamp", -1)])
            logger.info("MongoDB Atlas indexes verified on required collections.")
        except Exception as e:
            logger.warning(f"Could not initialize MongoDB indexes: {e}")

    def get_collection(self, name: str):
        if self.is_connected and self.db is not None:
            return MongoCollectionWrapper(self.db[name])
        return self.in_memory_collections.get(name, InMemoryCollection(name))

    def get_status_info(self) -> Dict[str, Any]:
        """Provides status details including document counts for dashboard and health check."""
        counts = {}
        for col_name in REQUIRED_COLLECTIONS:
            try:
                col = self.get_collection(col_name)
                counts[col_name] = col.count_documents({})
            except Exception:
                counts[col_name] = 0

        # Most recent reading timestamp if available
        last_reading = None
        try:
            readings = self.get_collection("readings").find(sort=[("tick", -1)], limit=1)
            if readings:
                last_reading = readings[0].get("timestamp")
        except Exception:
            pass

        return {
            "connected": self.is_connected,
            "status_text": "CONNECTED" if self.is_connected else "DEMO FALLBACK",
            "provider": "MongoDB Atlas" if self.is_connected else "In-Memory",
            "database": MONGODB_DATABASE if self.is_connected else "memory_store",
            "collections": counts,
            "last_reading_timestamp": last_reading,
            "error": self.last_error if not self.is_connected and MONGODB_URI else None,
        }


# Global database manager singleton
db_manager = DatabaseManager()
