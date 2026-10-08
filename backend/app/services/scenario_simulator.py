import math
from typing import Dict, Any, List, Optional
from app.services.optimizer import generate_rebalancing_recommendation, calculate_transit_time_minutes, haversine_distance_km

def run_what_if_simulation(
    scenario_type: str,
    hospitals: List[Dict[str, Any]],
    predictions: List[Dict[str, Any]],
    demand_multiplier: float = 1.0,
    excluded_donors: Optional[List[str]] = None,
    delay_minutes: int = 0,
    custom_quantity: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Feature 6 — What-If Scenario Simulator.
    Calculates deterministic counterfactual projections under operator-configured hypothetical conditions.
    Supports:
      - demand_plus_10, demand_plus_20, demand_plus_30
      - donor_unavailable (e.g. H-B offline)
      - delayed_transfer (+30m transit delay)
      - custom_transfer_qty (e.g. 25, 30, 50 units)
    """
    # 1. Parse scenario parameters
    multiplier = demand_multiplier
    if scenario_type == "demand_plus_10":
        multiplier = 1.10
    elif scenario_type == "demand_plus_20":
        multiplier = 1.20
    elif scenario_type == "demand_plus_30":
        multiplier = 1.30
    elif scenario_type == "donor_unavailable":
        excluded_donors = list(set((excluded_donors or []) + ["H-B"]))
    elif scenario_type == "delayed_transfer":
        delay_minutes = 30

    # 2. Adjust predictions based on demand multiplier
    adjusted_predictions = []
    for p in predictions:
        p_copy = dict(p)
        rate = float(p.get("depletion_rate", 2.0)) * multiplier
        p_copy["depletion_rate"] = round(rate, 2)
        stock = float(p.get("stock", 100))
        hosp = next((h for h in hospitals if h["id"] == p["hospital_id"]), None)
        thresh = float(hosp["safety_threshold"]) if hosp else 50.0

        if stock <= thresh:
            p_copy["time_to_shortage_hours"] = 0.0
        elif rate > 0.05:
            p_copy["time_to_shortage_hours"] = round(max(0.0, (stock - thresh) / rate), 2)
        else:
            p_copy["time_to_shortage_hours"] = None
        adjusted_predictions.append(p_copy)

    # 3. Target hospital in most critical state (Hospital A in surge)
    pred_h_a = next((p for p in adjusted_predictions if p["hospital_id"] == "H-A"), None)
    hosp_a = next((h for h in hospitals if h["id"] == "H-A"), None)

    if not pred_h_a or not hosp_a:
        dest_stock = 88.0
        dest_thresh = 60.0
        dest_rate = 18.0 * multiplier
    else:
        dest_stock = float(hosp_a["current_stock"])
        dest_thresh = float(hosp_a["safety_threshold"])
        dest_rate = float(pred_h_a["depletion_rate"])

    # 4. Run deterministic optimizer under scenario conditions
    rec, failure_msg = generate_rebalancing_recommendation(
        hospitals=hospitals,
        predictions=adjusted_predictions,
        excluded_donors=excluded_donors,
    )

    transfer_feasible = rec is not None and rec.get("status") != "no_safe_transfer"
    qty_to_use = custom_quantity if custom_quantity is not None else (rec["quantity"] if transfer_feasible else 0)
    donor_id = rec.get("from_hospital", "NONE") if transfer_feasible else "NONE"

    # 5. Simulate 8-hour horizon (step = 0.5 hr = 16 steps)
    timeline = []
    horizon_hours = 8.0
    steps = 16
    dt = 0.5  # hours per step

    # Transfer arrival time (default arrival ~ 45m = 0.75h + delay)
    arrival_time_hours = (0.75 + (delay_minutes / 60.0)) if transfer_feasible else 999.0

    stock_without = dest_stock
    stock_with = dest_stock
    shortage_time_without = None
    shortage_time_with = None
    shortage_hours_without = 0.0
    shortage_hours_with = 0.0
    transfer_applied = False

    for s in range(steps + 1):
        t_hr = s * dt

        # Consumption
        if s > 0:
            stock_without = max(0.0, stock_without - (dest_rate * dt))
            stock_with = max(0.0, stock_with - (dest_rate * dt))

            # Apply transfer when transit finishes
            if transfer_feasible and not transfer_applied and t_hr >= arrival_time_hours:
                stock_with += qty_to_use
                transfer_applied = True

        # Check shortage conditions
        if stock_without < dest_thresh:
            shortage_hours_without += dt
            if shortage_time_without is None:
                shortage_time_without = round(t_hr, 1)

        if stock_with < dest_thresh:
            shortage_hours_with += dt
            if shortage_time_with is None and transfer_applied:
                shortage_time_with = round(t_hr, 1)

        timeline.append({
            "hour": round(t_hr, 1),
            "stock_without": round(stock_without, 1),
            "stock_with": round(stock_with, 1),
            "safety_threshold": int(dest_thresh),
        })

    shortage_prevented = round(max(0.0, shortage_hours_without - shortage_hours_with), 1)

    summary_text = (
        f"Scenario [{scenario_type}]: "
        f"Without intervention, Hospital A reaches shortage in {shortage_time_without or 0.0}h "
        f"(total deficit duration {round(shortage_hours_without, 1)}h). "
    )
    if transfer_feasible:
        summary_text += (
            f"Transfer of {qty_to_use} units from {donor_id} delays shortage to {shortage_time_with or '>8.0'}h, "
            f"preventing {shortage_prevented} shortage-hours."
        )
    else:
        summary_text += "No safe donor available under these constraints. Immediate external stockpile escalation required."

    return {
        "scenario_type": scenario_type,
        "demand_multiplier": multiplier,
        "excluded_donors": excluded_donors or [],
        "delay_minutes": delay_minutes,
        "transfer_feasible": transfer_feasible,
        "recommended_donor": donor_id,
        "transfer_quantity": qty_to_use,
        "without_intervention": {
            "initial_stock": int(dest_stock),
            "depletion_rate": round(dest_rate, 2),
            "time_to_shortage_hours": shortage_time_without or 0.0,
            "shortage_duration_hours": round(shortage_hours_without, 1),
            "min_stock": round(min(p["stock_without"] for p in timeline), 1),
        },
        "with_intervention": {
            "initial_stock": int(dest_stock),
            "quantity_transferred": qty_to_use if transfer_feasible else 0,
            "time_to_shortage_hours": shortage_time_with if shortage_time_with is not None else 8.0,
            "shortage_duration_hours": round(shortage_hours_with, 1),
            "min_stock": round(min(p["stock_with"] for p in timeline), 1),
            "donor_safety_maintained": transfer_feasible,
        },
        "shortage_hours_prevented": shortage_prevented,
        "timeline": timeline,
        "summary": summary_text,
    }
