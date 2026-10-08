import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.database import db_manager

logger = logging.getLogger("audit")

def record_audit_event(
    event_type: str,
    details: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Persists an immutable decision audit log entry to MongoDB Atlas / fallback.
    Feature 8 — Decision Audit Trail.
    """
    event_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.utcnow().isoformat()
    record = {
        "id": event_id,
        "timestamp": timestamp,
        "event_type": event_type,
        **details,
    }
    try:
        col = db_manager.get_collection("audit_trail")
        col.insert_one(record)
        logger.info(f"Audit event recorded: [{event_type}] {event_id}")
    except Exception as e:
        logger.warning(f"Could not persist audit record: {e}")
    return record

def get_audit_trail(limit: int = 25) -> List[Dict[str, Any]]:
    """Retrieves recent decision audit trail entries sorted by newest first."""
    try:
        col = db_manager.get_collection("audit_trail")
        records = col.find({}, sort=[("timestamp", -1)], limit=limit)
        return records
    except Exception as e:
        logger.warning(f"Could not read audit trail: {e}")
        return []
