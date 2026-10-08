import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Path

from app.database import db_manager
from app.services.simulator import simulator
from app.services.predictor import compute_network_risk_ranking
from app.services.evaluation import DEFAULT_EVALUATION, generate_evaluation_dataset
from app.services.replay import run_counterfactual_replay
from app.services.gemini import generate_recommendation_explanation, generate_copilot_brief
from app.services.scenario_simulator import run_what_if_simulation
from app.services.audit import get_audit_trail
from app.models.schemas import (
    ExplainRequest,
    ScenarioSimulateRequest,
    CopilotActionRequest,
    SetScenarioRequest,
)

logger = logging.getLogger("api")
router = APIRouter()

@router.get("/hospitals")
async def get_hospitals():
    """Returns the 6 monitored hospitals and their current capacities/thresholds."""
    return {"hospitals": list(simulator.hospitals.values())}

@router.get("/state")
async def get_state():
    """Consolidated state payload powering the executive operations dashboard."""
    return simulator.get_consolidated_state()

@router.get("/predictions")
async def get_predictions():
    """Returns latest trend predictions and time-to-shortage metrics."""
    return {"predictions": simulator.latest_predictions}

@router.get("/network-risk")
async def get_network_risk():
    """Feature 4: Returns network-wide risk priority ranking across all hospitals."""
    ranking = compute_network_risk_ranking(
        hospitals=list(simulator.hospitals.values()),
        predictions=simulator.latest_predictions,
    )
    return {"network_risk_ranking": ranking}

@router.get("/recommendations")
async def get_recommendations():
    """Returns active and past recommendations."""
    return {"recommendations": simulator.active_recommendations}

@router.get("/evaluation")
async def get_evaluation():
    """Returns real held-out model evaluation against naive baseline."""
    eval_result = generate_evaluation_dataset()
    eval_col = db_manager.get_collection("evaluation_runs")
    eval_col.insert_one(eval_result)
    return eval_result

@router.get("/database/status")
async def get_database_status():
    """Returns detailed database connectivity and collection statistics."""
    return db_manager.get_status_info()

@router.get("/audit")
async def get_audit():
    """Feature 8: Returns decision audit trail logs."""
    logs = get_audit_trail(limit=30)
    return {"audit_trail": logs}

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

@router.post("/simulation/scenario")
async def set_simulation_scenario(req: SetScenarioRequest):
    """Feature 11: Demo Scenario Control preset activation."""
    simulator.set_scenario(req.scenario_name)
    return {
        "status": "scenario_set",
        "scenario": req.scenario_name,
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
    """Feature 7: Calculates advanced counterfactual replay comparing Without vs With System."""
    replay_data = run_counterfactual_replay()
    return replay_data

@router.post("/scenario/simulate")
async def simulate_scenario(req: ScenarioSimulateRequest):
    """Feature 6: Runs What-If scenario simulation."""
    result = run_what_if_simulation(
        scenario_type=req.scenario_type,
        hospitals=list(simulator.hospitals.values()),
        predictions=simulator.latest_predictions,
        demand_multiplier=req.demand_multiplier,
        excluded_donors=req.excluded_donors,
        delay_minutes=req.delay_minutes,
        custom_quantity=req.custom_quantity,
    )
    return result

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

@router.post("/copilot/action")
async def copilot_action(req: CopilotActionRequest):
    """Feature 9: Executes Gemini Operations Copilot briefing/explanation actions."""
    output = generate_copilot_brief(
        action_type=req.action_type,
        facts=req.facts,
    )
    return {
        "action_type": req.action_type,
        "content": output,
    }
