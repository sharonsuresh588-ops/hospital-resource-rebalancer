from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class HospitalModel(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    capacity: int
    safety_threshold: int
    current_stock: int

class ReadingModel(BaseModel):
    hospital_id: str
    timestamp: str
    stock: int
    resource: str = "oxygen_cylinders"

class PredictionModel(BaseModel):
    hospital_id: str
    timestamp: str
    stock: int
    depletion_rate: float
    time_to_shortage_hours: Optional[float] = None
    confidence: float
    status: str = "SAFE"  # SAFE, WARNING, CRITICAL

class RecommendationModel(BaseModel):
    id: str
    from_hospital: str
    to_hospital: str
    quantity: int
    dispatch_deadline_minutes: int
    status: str = "pending"  # pending, approved, rejected
    justification: str
    created_at: str
    donor_safety_margin_after: int = 0

class SimulationStatusModel(BaseModel):
    running: bool
    surge_active: bool
    tick: int
    tick_interval_seconds: float = 3.0

class MetricsModel(BaseModel):
    shortage_hours_prevented: float
    units_transferred: int
    transfers_completed: int

class EvaluationModel(BaseModel):
    title: str = "Model evaluation — held-out simulated data"
    model_mae: float
    baseline_mae: float
    relative_improvement_pct: float
    evaluation_samples: int
    baseline_method: str = "Most recently observed depletion rate"
    model_method: str = "Multi-sample ordinary linear trend regression"
    timestamp: str

class SystemHealthModel(BaseModel):
    api: str = "HEALTHY"
    database: Dict[str, Any]
    simulator: str = "IDLE"

class DashboardStateModel(BaseModel):
    simulation: SimulationStatusModel
    hospitals: List[HospitalModel]
    predictions: List[PredictionModel]
    recommendations: List[RecommendationModel]
    evaluation: EvaluationModel
    metrics: MetricsModel
    system_health: SystemHealthModel
    history: Dict[str, List[Dict[str, Any]]] = {}

class ReplayScenarioResult(BaseModel):
    shortage_hours: float
    units_transferred: int
    critical_events: int
    timeline: List[Dict[str, Any]]

class ReplayResponse(BaseModel):
    without_system: ReplayScenarioResult
    with_system: ReplayScenarioResult
    shortage_hours_prevented: float
    units_transferred: int
    summary: str

class ExplainRequest(BaseModel):
    from_hospital: str
    to_hospital: str
    quantity: int
    destination_shortage_hours: Optional[float] = None
    source_safe_surplus: int
    dispatch_deadline_minutes: int

class ScenarioSimulateRequest(BaseModel):
    scenario_type: str = "demand_plus_20"
    demand_multiplier: float = 1.0
    excluded_donors: Optional[List[str]] = None
    delay_minutes: int = 0
    custom_quantity: Optional[int] = None

class CopilotActionRequest(BaseModel):
    action_type: str
    facts: Dict[str, Any]

class SetScenarioRequest(BaseModel):
    scenario_name: str
