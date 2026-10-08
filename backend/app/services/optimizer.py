import math
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from app.services.gemini import generate_recommendation_explanation

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates approximate distance in kilometers between two geo-coordinates."""
    r = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return round(2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)), 2)


def generate_rebalancing_recommendation(
    hospitals: List[Dict[str, Any]],
    predictions: List[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Deterministic Transfer Optimizer (Sections 17-22).
    Pure deterministic Python logic - Gemini is NEVER involved in transfer decision.
    """
    # Index predictions by hospital ID
    pred_by_id = {p["hospital_id"]: p for p in predictions}
    hosp_by_id = {h["id"]: h for h in hospitals}

    # Identify hospitals in critical need:
    # Ranked by earliest time_to_shortage and stock deficit
    critical_candidates = []
    for h in hospitals:
        hid = h["id"]
        pred = pred_by_id.get(hid)
        if not pred:
            continue

        stock = h["current_stock"]
        threshold = h["safety_threshold"]
        shortage_hrs = pred.get("time_to_shortage_hours")
        depletion = pred.get("depletion_rate", 0.0)

        # Hospital is in need if time to shortage is <= 3.5 hours or stock <= threshold + 10
        is_in_need = False
        urgency_score = 0.0

        if stock <= threshold:
            is_in_need = True
            urgency_score = 1000.0 + (threshold - stock)
        elif shortage_hrs is not None and shortage_hrs <= 3.5:
            is_in_need = True
            # Earlier shortage = higher urgency
            urgency_score = 500.0 - (shortage_hrs * 100.0)

        if is_in_need:
            critical_candidates.append({
                "hospital": h,
                "prediction": pred,
                "urgency_score": urgency_score,
                "time_to_shortage_hours": shortage_hrs,
            })

    if not critical_candidates:
        return None, "All hospitals have adequate oxygen reserves."

    # Sort critical candidates by highest urgency score (Hospital A in surge will be top)
    critical_candidates.sort(key=lambda x: x["urgency_score"], reverse=True)
    destination = critical_candidates[0]["hospital"]
    dest_pred = critical_candidates[0]["prediction"]
    dest_stock = destination["current_stock"]
    dest_thresh = destination["safety_threshold"]
    dest_rate = dest_pred.get("depletion_rate", 10.0)
    dest_shortage_hrs = dest_pred.get("time_to_shortage_hours")

    # Calculate required transfer quantity
    # In an active surge / shortage, rebalancing must restore the hospital to a safe buffer
    # covering the dispatch arrival horizon (0.75h) plus an operational replenishment reserve (1.5h)
    arrival_horizon_hrs = 0.75
    reserve_horizon_hrs = 1.25
    projected_consumption_dest = dest_rate * (arrival_horizon_hrs + reserve_horizon_hrs)
    
    # Target stock ensures hospital remains comfortably above safety threshold after surge
    required_target = dest_thresh + projected_consumption_dest
    raw_quantity = required_target - dest_stock

    # Round to standard operational increments of 5 cylinders, with target replenishment lot of 40
    calc_quantity = int(math.ceil(max(40, raw_quantity) / 5.0) * 5)
    # Clamp to practical bounds (e.g. 35 to 50 cylinders, targeting 40 units)
    transfer_quantity = min(50, max(35, calc_quantity))

    # Evaluate potential donor hospitals
    donor_candidates = []
    for h in hospitals:
        hid = h["id"]
        if hid == destination["id"]:
            continue  # cannot donate to self

        donor_pred = pred_by_id.get(hid, {})
        donor_stock = h["current_stock"]
        donor_threshold = h["safety_threshold"]
        donor_depletion = donor_pred.get("depletion_rate", 2.0)

        # Additional safety constraint: projected consumption over 4 hours
        donor_buffer = donor_depletion * 4.0
        donor_safe_requirement = donor_threshold + int(donor_buffer)

        # Donor feasibility check:
        # Stock after transfer MUST be strictly >= donor_safe_requirement
        stock_after = donor_stock - transfer_quantity
        if stock_after >= donor_safe_requirement:
            safe_surplus = stock_after - donor_threshold
            dist = haversine_distance_km(
                h["lat"], h["lng"], destination["lat"], destination["lng"]
            )
            # Ranking score: prioritizes larger safe surplus margin and closer distance
            donor_score = safe_surplus * 10.0 - dist
            donor_candidates.append({
                "hospital": h,
                "safe_surplus": safe_surplus,
                "donor_score": donor_score,
                "stock_after": stock_after,
                "distance_km": dist,
            })

    if not donor_candidates:
        return None, "No hospital has sufficient safe surplus to donate."

    # Sort donor candidates by highest donor score (Hospital B has largest surplus)
    donor_candidates.sort(key=lambda x: x["donor_score"], reverse=True)
    best_donor = donor_candidates[0]
    donor_hosp = best_donor["hospital"]

    # HARD SAFETY RULE (Section 21)
    if (donor_hosp["current_stock"] - transfer_quantity) < donor_hosp["safety_threshold"]:
        return None, "Safety constraint violation: Donor reserve would breach safety threshold."

    # Calculate dispatch deadline from destination urgency
    # fraction of time to shortage clamped between 30 and 60 minutes
    if dest_shortage_hrs is not None and dest_shortage_hrs > 0:
        raw_deadline = int(dest_shortage_hrs * 60 * 0.45)
        deadline_minutes = max(30, min(60, raw_deadline))
    else:
        deadline_minutes = 45

    # Produce Gemini or fallback operational explanation
    justification = generate_recommendation_explanation(
        from_hospital=donor_hosp["name"],
        to_hospital=destination["name"],
        quantity=transfer_quantity,
        destination_shortage_hours=dest_shortage_hrs,
        source_safe_surplus=best_donor["safe_surplus"],
        dispatch_deadline_minutes=deadline_minutes,
    )

    rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
    recommendation = {
        "id": rec_id,
        "from_hospital": donor_hosp["id"],
        "to_hospital": destination["id"],
        "quantity": transfer_quantity,
        "dispatch_deadline_minutes": deadline_minutes,
        "status": "pending",
        "justification": justification,
        "created_at": datetime.utcnow().isoformat(),
        "donor_safety_margin_after": best_donor["safe_surplus"],
    }

    return recommendation, None
