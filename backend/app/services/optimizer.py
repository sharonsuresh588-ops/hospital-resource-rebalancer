import math
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from app.services.gemini import generate_recommendation_explanation
from app.services.audit import record_audit_event

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

def calculate_transit_time_minutes(distance_km: float) -> int:
    """
    Feature 2 — Travel Time & Network Awareness.
    Assumes emergency vehicle transit speed averaging 35 km/h plus 10 minutes dispatch preparation.
    """
    return max(15, int(round(10.0 + (distance_km / 35.0) * 60.0)))


def generate_rebalancing_recommendation(
    hospitals: List[Dict[str, Any]],
    predictions: List[Dict[str, Any]],
    planning_horizon_hours: float = 4.0,
    excluded_donors: Optional[List[str]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Features 1, 2, 3, 5 — Deterministic Feasibility-Aware Transfer Optimizer.
    Pure deterministic Python logic - Gemini is NEVER involved in transfer decision.
    
    Hard Constraints (Override all scoring):
      1. Immediate donor stock >= safety threshold after transfer.
      2. Future donor stock over planning horizon >= safety threshold (Feature 3).
      3. Transit time <= recipient dispatch deadline (Feature 2).
      4. Donor is not recipient and has sufficient stock.
    
    Donor Scoring:
      DONOR SCORE = (safe surplus * 10) + (future safety buffer * 8) - (travel penalty) + urgency compat.
    
    No-Safe-Transfer Intelligence (Feature 5):
      If no donor satisfies all constraints, returns a structured non-fabricated refusal
      with failure breakdown and external escalation directive.
    """
    excluded_set = set(excluded_donors or [])
    pred_by_id = {p["hospital_id"]: p for p in predictions}
    hosp_by_id = {h["id"]: h for h in hospitals}

    # 1. Identify recipient in critical need
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

        is_in_need = False
        urgency_score = 0.0

        if stock <= threshold:
            is_in_need = True
            urgency_score = 1000.0 + (threshold - stock) * 10.0
        elif shortage_hrs is not None and shortage_hrs <= 3.5:
            is_in_need = True
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

    # Dispatch deadline based on recipient urgency (between 30 and 60 minutes)
    if dest_shortage_hrs is not None and dest_shortage_hrs > 0:
        raw_deadline = int(dest_shortage_hrs * 60 * 0.45)
        deadline_minutes = max(30, min(60, raw_deadline))
    else:
        deadline_minutes = 45

    # Target replenishment: lot size 40 units (clamped between 35 and 50)
    arrival_horizon_hrs = 0.75
    reserve_horizon_hrs = 1.25
    projected_consumption_dest = dest_rate * (arrival_horizon_hrs + reserve_horizon_hrs)
    required_target = dest_thresh + projected_consumption_dest
    raw_quantity = required_target - dest_stock
    calc_quantity = int(math.ceil(max(40, raw_quantity) / 5.0) * 5)
    transfer_quantity = min(50, max(35, calc_quantity))

    # 2. Evaluate all candidate donor hospitals
    candidate_breakdown = []
    eligible_donors = []

    for h in hospitals:
        hid = h["id"]
        if hid == destination["id"]:
            continue  # cannot donate to self

        donor_pred = pred_by_id.get(hid, {})
        donor_stock = h["current_stock"]
        donor_threshold = h["safety_threshold"]
        donor_depletion = donor_pred.get("depletion_rate", 2.0)

        # Distance and travel time
        dist_km = haversine_distance_km(
            h.get("lat", 0.0), h.get("lng", 0.0),
            destination.get("lat", 0.0), destination.get("lng", 0.0)
        )
        travel_time_min = calculate_transit_time_minutes(dist_km)

        # Check exclusion flag (e.g. what-if scenario testing)
        is_excluded = hid in excluded_set

        # Immediate stock after transfer
        stock_after = donor_stock - transfer_quantity

        # Feature 3: Future donor demand projection
        projected_consumption = donor_depletion * planning_horizon_hours
        projected_4h_stock = round(stock_after - projected_consumption, 1)

        # Hard constraints evaluation
        failed_constraints = []
        if is_excluded:
            failed_constraints.append("EXCLUDED_BY_OPERATOR")
        if donor_stock < transfer_quantity:
            failed_constraints.append(f"INSUFFICIENT_STOCK ({donor_stock} < {transfer_quantity})")
        if stock_after < donor_threshold:
            failed_constraints.append(f"BREACH_IMMEDIATE_SAFETY (stock after {stock_after} < threshold {donor_threshold})")
        if projected_4h_stock < donor_threshold:
            failed_constraints.append(f"BREACH_FUTURE_DEMAND (projected 4h stock {projected_4h_stock} < threshold {donor_threshold})")
        if travel_time_min > deadline_minutes:
            failed_constraints.append(f"ARRIVAL_DEADLINE_BREACH (transit {travel_time_min}m > deadline {deadline_minutes}m)")

        passed = len(failed_constraints) == 0
        safe_surplus = max(0, stock_after - donor_threshold)
        future_buffer = max(0.0, projected_4h_stock - donor_threshold)

        # Feature 1: Deterministic donor score
        if passed:
            travel_penalty = travel_time_min * 1.5
            urgency_compat = 100.0 / (1.0 + (dest_shortage_hrs if dest_shortage_hrs is not None else 1.0))
            donor_score = round((safe_surplus * 10.0) + (future_buffer * 8.0) - travel_penalty + urgency_compat, 1)
        else:
            donor_score = 0.0

        candidate_info = {
            "hospital_id": hid,
            "hospital_name": h["name"],
            "current_stock": donor_stock,
            "safety_threshold": donor_threshold,
            "transfer_quantity": transfer_quantity,
            "stock_after_transfer": stock_after,
            "projected_4h_stock": projected_4h_stock,
            "distance_km": dist_km,
            "travel_time_minutes": travel_time_min,
            "safe_surplus": safe_surplus,
            "passed_all_constraints": passed,
            "failed_constraints": failed_constraints,
            "donor_score": donor_score,
            "rejection_reason": "; ".join(failed_constraints) if not passed else None,
        }
        candidate_breakdown.append(candidate_info)

        if passed:
            eligible_donors.append({
                "hospital": h,
                "candidate_info": candidate_info,
                "donor_score": donor_score,
                "safe_surplus": safe_surplus,
                "travel_time_minutes": travel_time_min,
                "projected_4h_stock": projected_4h_stock,
            })

    # Sort candidates by donor score descending for clear ranking view
    candidate_breakdown.sort(key=lambda x: x["donor_score"], reverse=True)

    # Feature 5: NO-SAFE-TRANSFER INTELLIGENCE
    if not eligible_donors:
        rejection_summaries = [
            f"{c['hospital_id']} ({c['rejection_reason']})"
            for c in candidate_breakdown if c["rejection_reason"]
        ]
        no_safe_justification = (
            f"NO SAFE TRANSFER AVAILABLE: All potential donors rejected by safety constraints. "
            f"Evaluated candidates: {', '.join(rejection_summaries[:3])}. "
            f"Regional network cannot donate without inducing secondary stockouts. External replenishment required."
        )
        rec_id = f"NO-SAFE-{uuid.uuid4().hex[:8].upper()}"
        no_safe_rec = {
            "id": rec_id,
            "from_hospital": "NONE",
            "to_hospital": destination["id"],
            "quantity": 0,
            "dispatch_deadline_minutes": deadline_minutes,
            "status": "no_safe_transfer",
            "justification": no_safe_justification,
            "created_at": datetime.utcnow().isoformat(),
            "donor_safety_margin_after": 0,
            "donor_score": 0.0,
            "winning_reason": "No regional hospital can safely donate without breaching reserves.",
            "candidate_breakdown": candidate_breakdown,
            "is_safe_transfer": False,
            "escalation_required": True,
            "escalation_message": (
                f"EMERGENCY MUTUAL-AID ESCALATION: Regional inventory exhausted. Dispatch external "
                f"depot supply truck to {destination['name']} immediately before {deadline_minutes}m deadline."
            ),
        }
        record_audit_event("NO_SAFE_TRANSFER_DETECTED", {
            "recommendation_id": rec_id,
            "recipient_id": destination["id"],
            "recipient_name": destination["name"],
            "rejected_candidates": candidate_breakdown,
            "justification": no_safe_justification,
        })
        return no_safe_rec, "No safe transfer available; all candidate donors violate hard constraints."

    # 3. Winning donor selection (highest deterministic score)
    eligible_donors.sort(key=lambda x: x["donor_score"], reverse=True)
    best = eligible_donors[0]
    donor_hosp = best["hospital"]
    best_info = best["candidate_info"]

    winning_reason = (
        f"{donor_hosp['name']} selected because it has {best['safe_surplus']} cylinders of safe surplus, "
        f"{int(best['projected_4h_stock'])} units projected 4-hour reserve, and a "
        f"{best['travel_time_minutes']}-minute transit time (Donor Score: {best['donor_score']})."
    )

    # Produce Gemini or fallback operational explanation
    justification = generate_recommendation_explanation(
        from_hospital=donor_hosp["name"],
        to_hospital=destination["name"],
        quantity=transfer_quantity,
        destination_shortage_hours=dest_shortage_hrs,
        source_safe_surplus=best["safe_surplus"],
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
        "donor_safety_margin_after": best["safe_surplus"],
        "donor_score": best["donor_score"],
        "distance_km": best_info["distance_km"],
        "estimated_transit_minutes": best_info["travel_time_minutes"],
        "donor_projected_4h_stock": best_info["projected_4h_stock"],
        "winning_reason": winning_reason,
        "candidate_breakdown": candidate_breakdown,
        "is_safe_transfer": True,
        "escalation_required": False,
    }

    record_audit_event("RECOMMENDATION_ISSUED", {
        "recommendation_id": rec_id,
        "recipient_id": destination["id"],
        "recipient_name": destination["name"],
        "donor_id": donor_hosp["id"],
        "donor_name": donor_hosp["name"],
        "quantity": transfer_quantity,
        "dispatch_deadline_minutes": deadline_minutes,
        "donor_score": best["donor_score"],
        "winning_reason": winning_reason,
        "gemini_explanation": justification,
    })

    return recommendation, None
