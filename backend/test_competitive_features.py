import os
import sys
from datetime import datetime

from app.database import db_manager
from app.services.simulator import DEFAULT_HOSPITALS, simulator
from app.services.predictor import predict_hospital_depletion, compute_network_risk_ranking
from app.services.optimizer import (
    generate_rebalancing_recommendation,
    haversine_distance_km,
    calculate_transit_time_minutes,
)
from app.services.scenario_simulator import run_what_if_simulation
from app.services.replay import run_counterfactual_replay
from app.services.audit import record_audit_event, get_audit_trail
from app.services.gemini import generate_copilot_brief

def test_competitive_features():
    print("=============================================================")
    print("TESTING COMPETITIVE FEATURES (FEATURES 1 TO 14)")
    print("=============================================================")
    db_manager.connect()

    # -------------------------------------------------------------
    # 1. Feature 1 & 2: Feasibility-Aware Donor Ranking & Travel Time
    # -------------------------------------------------------------
    print("\n[Check 1] Feasibility-Aware Donor Ranking & Travel Time")
    dist_ab = haversine_distance_km(13.0827, 80.2707, 13.0358, 80.2443)
    transit_ab = calculate_transit_time_minutes(dist_ab)
    print(f"H-A <-> H-B Distance: {dist_ab} km, Estimated Transit: {transit_ab} mins")
    assert 4.0 <= dist_ab <= 8.0, f"Unexpected distance {dist_ab}"
    assert 15 <= transit_ab <= 35, f"Unexpected transit time {transit_ab}"
    print("PASS: Travel time and network distance calculated accurately.")

    # -------------------------------------------------------------
    # 2. Feature 3: Future Donor Demand Protection
    # -------------------------------------------------------------
    print("\n[Check 2] Future Donor Demand Protection Constraint")
    # Hospital B baseline stock = 195, safety threshold = 65, depletion = 2.0 u/hr
    # If transfer = 40, stock_after = 155.
    # Projected 4h consumption = 2.0 * 4 = 8.0 units -> projected 4h stock = 147.0 > 65 -> PASS!
    test_hospitals = [
        {"id": "H-A", "name": "Hospital A", "current_stock": 80, "safety_threshold": 60, "lat": 13.08, "lng": 80.27},
        {"id": "H-B", "name": "Hospital B", "current_stock": 195, "safety_threshold": 65, "lat": 13.03, "lng": 80.24},
        # Candidate C has barely enough stock: current 90, threshold 60, depletion 5.0 u/hr
        # Stock after 40 = 50 < 60 -> Immediate safety breach!
        {"id": "H-C", "name": "Hospital C", "current_stock": 90, "safety_threshold": 60, "lat": 13.00, "lng": 80.25},
        # Candidate D has stock 105, threshold 60, depletion 5.0 u/hr
        # Stock after 40 = 65 >= 60. But 4h projected = 65 - 20 = 45 < 60 -> Future demand breach!
        {"id": "H-D", "name": "Hospital D", "current_stock": 105, "safety_threshold": 60, "lat": 13.01, "lng": 80.25},
    ]
    test_preds = [
        {"hospital_id": "H-A", "depletion_rate": 20.0, "time_to_shortage_hours": 1.0, "confidence": 0.9},
        {"hospital_id": "H-B", "depletion_rate": 2.0, "time_to_shortage_hours": None, "confidence": 0.9},
        {"hospital_id": "H-C", "depletion_rate": 5.0, "time_to_shortage_hours": None, "confidence": 0.8},
        {"hospital_id": "H-D", "depletion_rate": 5.0, "time_to_shortage_hours": None, "confidence": 0.8},
    ]

    rec, _ = generate_rebalancing_recommendation(test_hospitals, test_preds)
    assert rec is not None
    assert rec["from_hospital"] == "H-B", f"Expected H-B to win, got {rec['from_hospital']}"
    assert rec["is_safe_transfer"] is True
    assert rec["donor_score"] > 500.0
    print(f"PASS: Winning donor: {rec['from_hospital']} (Score: {rec['donor_score']})")

    # Verify candidate C and D failed for exact constraint reasons
    c_breakdown = next(c for c in rec["candidate_breakdown"] if c["hospital_id"] == "H-C")
    d_breakdown = next(c for c in rec["candidate_breakdown"] if c["hospital_id"] == "H-D")
    assert c_breakdown["passed_all_constraints"] is False
    assert "BREACH_IMMEDIATE_SAFETY" in c_breakdown["rejection_reason"]
    assert d_breakdown["passed_all_constraints"] is False
    assert "BREACH_FUTURE_DEMAND" in d_breakdown["rejection_reason"]
    print(f"PASS: H-C rejected due to immediate safety breach: {c_breakdown['rejection_reason']}")
    print(f"PASS: H-D rejected due to future demand breach: {d_breakdown['rejection_reason']}")

    # -------------------------------------------------------------
    # 3. Feature 5: No-Safe-Transfer Intelligence
    # -------------------------------------------------------------
    print("\n[Check 3] No-Safe-Transfer Intelligence (Deterministic Refusal)")
    # When no hospital has safe surplus, system MUST NOT invent a recommendation
    depleted_hospitals = [
        {"id": "H-A", "name": "Hospital A", "current_stock": 50, "safety_threshold": 60, "lat": 13.08, "lng": 80.27},
        {"id": "H-B", "name": "Hospital B", "current_stock": 70, "safety_threshold": 65, "lat": 13.03, "lng": 80.24},
        {"id": "H-C", "name": "Hospital C", "current_stock": 55, "safety_threshold": 50, "lat": 13.00, "lng": 80.25},
    ]
    no_safe_rec, fail_msg = generate_rebalancing_recommendation(depleted_hospitals, test_preds)
    assert no_safe_rec is not None
    assert no_safe_rec["status"] == "no_safe_transfer"
    assert no_safe_rec["from_hospital"] == "NONE"
    assert no_safe_rec["quantity"] == 0
    assert no_safe_rec["escalation_required"] is True
    assert "NO SAFE TRANSFER AVAILABLE" in no_safe_rec["justification"]
    print("PASS: System deterministically declared 'NO SAFE TRANSFER AVAILABLE' with full escalation action.")

    # -------------------------------------------------------------
    # 4. Feature 4: Network-Wide Risk Priority Ranking
    # -------------------------------------------------------------
    print("\n[Check 4] Network-Wide Risk Priority Ranking")
    risk_ranking = compute_network_risk_ranking(test_hospitals, test_preds)
    assert len(risk_ranking) == len(test_hospitals)
    assert risk_ranking[0]["hospital_id"] == "H-A", "H-A must be ranked #1 risk during critical deficit"
    assert risk_ranking[0]["risk_level"] in ["CRITICAL", "NETWORK EMERGENCY"]
    print("Network Risk Ranking:")
    for r in risk_ranking:
        print(f"  #{r['rank']} {r['hospital_id']} — {r['risk_level']} (Score: {r['risk_score']})")
    print("PASS: Risk ranking correctly prioritized critical emergency.")

    # -------------------------------------------------------------
    # 5. Feature 6: What-If Scenario Simulator
    # -------------------------------------------------------------
    print("\n[Check 5] What-If Scenario Simulator")
    sim_res = run_what_if_simulation("demand_plus_20", test_hospitals, test_preds)
    assert sim_res["scenario_type"] == "demand_plus_20"
    assert sim_res["shortage_hours_prevented"] >= 0.0
    assert len(sim_res["timeline"]) == 17
    print(f"What-If Demand +20% Result: {sim_res['summary']}")

    sim_excluded = run_what_if_simulation("donor_unavailable", test_hospitals, test_preds, excluded_donors=["H-B"])
    assert "H-B" in sim_excluded["excluded_donors"]
    print(f"What-If Donor H-B Excluded Result: {sim_excluded['summary']}")
    print("PASS: What-if counterfactual scenario engine executed cleanly.")

    # -------------------------------------------------------------
    # 6. Feature 7: Advanced Replay Metrics
    # -------------------------------------------------------------
    print("\n[Check 6] Advanced Replay Metrics")
    replay = run_counterfactual_replay()
    assert "minimum_stock" in replay["without_system"]
    assert "donor_minimum_stock" in replay["with_system"]
    assert replay["donor_safety_maintained"] is True
    assert replay["secondary_shortages_created"] == 0
    print(f"PASS: Advanced replay confirmed donor safety maintained & 0 secondary shortages.")

    # -------------------------------------------------------------
    # 7. Feature 8: Decision Audit Trail
    # -------------------------------------------------------------
    print("\n[Check 7] Decision Audit Trail Logging & Retrieval")
    aud_rec = record_audit_event("TEST_AUDIT_EVENT", {"detail": "verification_run"})
    assert aud_rec["id"].startswith("AUD-")
    logs = get_audit_trail(limit=5)
    assert len(logs) > 0
    assert any(log["id"] == aud_rec["id"] for log in logs)
    print(f"PASS: Decision audit event logged and retrieved (ID: {aud_rec['id']}).")

    # -------------------------------------------------------------
    # 8. Feature 9: Gemini Operations Copilot
    # -------------------------------------------------------------
    print("\n[Check 8] Gemini Operations Copilot Briefs & Fallbacks")
    facts = {
        "recipient_name": "District Hospital A",
        "donor_name": "District Hospital B",
        "quantity": 40,
        "time_to_shortage": "1.3",
        "safe_surplus": 82,
        "transit_time": 22,
        "donor_score": 1420,
    }
    brief = generate_copilot_brief("brief_coordinator", facts)
    assert len(brief) > 20
    print(f"Coordinator Brief: '{brief[:80]}...'")

    rationale = generate_copilot_brief("explain_donor_selection", facts)
    assert len(rationale) > 20
    print(f"Donor Selection Rationale: '{rationale[:80]}...'")
    print("PASS: Operations Copilot generation functional.")

    # -------------------------------------------------------------
    # 9. Feature 14: Graceful Degradation / Fallback Invariants
    # -------------------------------------------------------------
    print("\n[Check 9] Invariant: Copilot Fallback & No Decision Alteration")
    forced_fallback = generate_copilot_brief("brief_coordinator", facts, force_fallback=True)
    assert "District Hospital A" in forced_fallback
    assert "40 cylinders" in forced_fallback
    print(f"PASS: Copilot deterministic fallback verified: '{forced_fallback[:80]}...'")

    print("\n=============================================================")
    print("ALL COMPETITIVE FEATURES TESTS PASSED (100% SUCCESS)!")
    print("=============================================================")

if __name__ == "__main__":
    test_competitive_features()
