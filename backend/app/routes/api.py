import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Path

from app.database import db_manager
from app.services.simulator import simulator
from app.services.evaluation import DEFAULT_EVALUATION, generate_evaluation_dataset
from app.services.replay import run_counterfactual_replay
from app.services.gemini import generate_recommendation_explanation
from app.models.schemas import ExplainRequest

logger = logging.getLogger("api")
router = APIRouter()

@router.get("/hospitals")
async def get_hospitals():
    """Returns the 6 monitored hospitals and their current capacities/thresholds."""
    return {"hospitals": list(simulator.hospitals.values())}

@router.get("/state")
async def get_state():
    """Consolidated state payload powering the operations dashboard."""
    return simulator.get_consolidated_state()

@router.get("/predictions")
async def get_predictions():
    """Returns latest trend predictions and time-to-shortage metrics."""
    return {"predictions": simulator.latest_predictions}

@router.get("/recommendations")
async def get_recommendations():
    """Returns active and past recommendations."""
    return {"recommendations": simulator.active_recommendations}

@router.get("/evaluation")
async def get_evaluation():
    """Returns real held-out model evaluation against naive baseline."""
    eval_result = generate_evaluation_dataset()
    # Persist evaluation result to evaluation_runs collection (Task 5)
    eval_col = db_manager.get_collection("evaluation_runs")
    eval_col.insert_one(eval_result)
    return eval_result

@router.get("/database/status")
async def get_database_status():
    """Returns detailed database connectivity and collection statistics (Task 8)."""
    return db_manager.get_status_info()

@router.post("/simulation/start")
async def start_simulation():
    """Starts the 3-second simulation tick engine."""
    simulator.start()
    return {"status": "started", "running": True}

@router.post("/simulation/reset")
async def reset_simulation():
    """Stops surge mode, restores baseline stocks, clears recommendations."""
    simulator.stop()
    simulator.reset()
    return {
        "status": "reset",
        "running": False,
        "surge_active": False,
        "state": simulator.get_consolidated_state()
    }

@router.post("/simulation/surge")
async def inject_surge():
    """Injects surge scenario into Hospital A."""
    simulator.inject_surge()
    return {
        "status": "surge_injected",
        "surge_active": True,
        "state": simulator.get_consolidated_state()
    }

@router.post("/recommendations/{rec_id}/approve")
async def approve_recommendation(rec_id: str = Path(..., description="The ID of the recommendation to approve")):
    """Approves a transfer recommendation with hard donor safety validation."""
    try:
        updated_rec = simulator.approve_recommendation(rec_id)
        return {
            "status": "approved",
            "recommendation": updated_rec,
            "state": simulator.get_consolidated_state()
        }
    except ValueError as e:
        logger.warning(f"Transfer approval rejected: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during approval: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during transfer execution.")

@router.get("/replay")
async def get_replay():
    """Calculates counterfactual replay comparing Without vs With System."""
    replay_data = run_counterfactual_replay()
    return replay_data

@router.post("/gemini/explain")
async def explain_recommendation(req: ExplainRequest):
    """Explains an existing recommendation using Gemini or deterministic fallback."""
    explanation = generate_recommendation_explanation(
        from_hospital=req.from_hospital,
        to_hospital=req.to_hospital,
        quantity=req.quantity,
        destination_shortage_hours=req.destination_shortage_hours,
        source_safe_surplus=req.source_safe_surplus,
        dispatch_deadline_minutes=req.dispatch_deadline_minutes,
    )
    return {"explanation": explanation}
