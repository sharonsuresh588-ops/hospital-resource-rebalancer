import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.database import db_manager
from app.services.simulator import simulator
from app.routes.api import router as api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence (Section 44)
    logger.info("Initializing Hospital Resource Rebalancer backend...")
    db_manager.connect()
    # Reset simulator to baseline initial state
    simulator.reset()
    logger.info("Startup complete. Simulator is in IDLE mode awaiting user start.")
    yield
    # Shutdown sequence
    simulator.stop()
    logger.info("Shutdown complete.")

app = FastAPI(
    title="Cross-Hospital Resource Rebalancer API",
    description="Deterministic emergency oxygen operations, shortage prediction, and redistribution optimizer",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["*"],
    allow_origin_regex=r"https://.*\.onrender\.com|http://localhost:\d+|http://127\.0\.0\.1:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix="/api")

@app.get("/health")
def health():
    """Health check endpoint indicating API and database readiness."""
    db_status = db_manager.get_status_info()
    return {
        "status": "HEALTHY",
        "service": "hospital-resource-rebalancer",
        "database": db_status,
        "simulator_state": "RUNNING" if simulator.running else "IDLE",
    }
