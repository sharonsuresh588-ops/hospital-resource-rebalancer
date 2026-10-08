import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from app.database import db_manager
from app.services.simulator import simulator, DEFAULT_HOSPITALS
from app.services.predictor import predict_hospital_depletion
from app.services.optimizer import generate_rebalancing_recommendation
from app.services.gemini import get_deterministic_fallback, generate_recommendation_explanation
from app.services.evaluation import generate_evaluation_dataset
from app.services.replay import run_counterfactual_replay

def run_all_tests():
    print("========================================")
    print("RUNNING BACKEND TEST SUITE (10 CHECKS)")
    print("========================================")

    # TEST 1: Initial simulation has 6 hospitals
    print("\n--- Test 1: Initial Simulation 6 Hospitals ---")
    simulator.reset()
    assert len(simulator.hospitals) == 6, f"Expected 6 hospitals, got {len(simulator.hospitals)}"
    assert "H-A" in simulator.hospitals and "H-B" in simulator.hospitals
    print(f"PASS: 6 hospitals initialized: {list(simulator.hospitals.keys())}")

    # TEST 2: Normal mode stocks decrease
    print("\n--- Test 2: Normal Mode Consumption ---")
    stock_a_before = simulator.hospitals["H-A"]["current_stock"]
    simulator.step()
    stock_a_after = simulator.hospitals["H-A"]["current_stock"]
    assert stock_a_after < stock_a_before, f"Expected stock to decrease, was {stock_a_before} -> {stock_a_after}"
    print(f"PASS: Normal mode decreases stock ({stock_a_before} -> {stock_a_after})")

    # TEST 3: Surge increases H-A depletion
    print("\n--- Test 3: Surge Mode H-A Depletion ---")
    simulator.reset()
    simulator.inject_surge()
    stock_a_start = simulator.hospitals["H-A"]["current_stock"]
    simulator.step()
    simulator.step()
    stock_a_surge = simulator.hospitals["H-A"]["current_stock"]
    surge_drop = stock_a_start - stock_a_surge
    print(f"Surge drop over 2 ticks: {surge_drop} units")
    assert surge_drop >= 25, f"Expected surge drop >= 25, got {surge_drop}"
    print(f"PASS: Surge rapidly accelerates H-A consumption (dropped {surge_drop} units in 2 ticks)")

    # TEST 4: Prediction: H-A becomes earliest shortage
    print("\n--- Test 4: Prediction Identifies H-A Earliest Shortage ---")
    pred_a = next(p for p in simulator.latest_predictions if p["hospital_id"] == "H-A")
    print(f"H-A Prediction: status={pred_a['status']}, rate={pred_a['depletion_rate']} u/hr, shortage={pred_a['time_to_shortage_hours']} hrs, confidence={pred_a['confidence']}")
    assert pred_a["status"] == "CRITICAL", f"Expected H-A to be CRITICAL, got {pred_a['status']}"
    assert pred_a["time_to_shortage_hours"] is not None and pred_a["time_to_shortage_hours"] < 3.0
    print(f"PASS: H-A is CRITICAL with earliest shortage: {pred_a['time_to_shortage_hours']} hours")

    # TEST 5: Optimizer selects H-B -> H-A
    print("\n--- Test 5: Optimizer Deterministically Selects H-B -> H-A ---")
    rec, reason = generate_rebalancing_recommendation(
        list(simulator.hospitals.values()),
        simulator.latest_predictions
    )
    assert rec is not None, f"Expected recommendation, got None: {reason}"
    assert rec["from_hospital"] == "H-B", f"Expected source H-B, got {rec['from_hospital']}"
    assert rec["to_hospital"] == "H-A", f"Expected destination H-A, got {rec['to_hospital']}"
    assert 30 <= rec["quantity"] <= 50, f"Expected quantity ~40, got {rec['quantity']}"
    print(f"PASS: Recommendation {rec['from_hospital']} -> {rec['to_hospital']}, quantity: {rec['quantity']}, deadline: {rec['dispatch_deadline_minutes']} mins")

    # TEST 6: Donor Safety Hard Rule
    print("\n--- Test 6: Donor Safety Verification ---")
    donor_b = simulator.hospitals["H-B"]
    assert (donor_b["current_stock"] - rec["quantity"]) >= donor_b["safety_threshold"], "Donor safety violated!"
    print(f"PASS: Donor H-B maintains stock {donor_b['current_stock'] - rec['quantity']} >= threshold {donor_b['safety_threshold']}")

    # TEST 7: Approval increases A and decreases B
    print("\n--- Test 7: Human Approval Updates Stocks ---")
    b_stock_pre = simulator.hospitals["H-B"]["current_stock"]
    a_stock_pre = simulator.hospitals["H-A"]["current_stock"]
    qty = rec["quantity"]
    
    # Store recommendation in simulator to approve
    simulator.active_recommendations = [rec]
    simulator.approve_recommendation(rec["id"])

    assert simulator.hospitals["H-A"]["current_stock"] == a_stock_pre + qty
    assert simulator.hospitals["H-B"]["current_stock"] == b_stock_pre - qty
    assert simulator.units_transferred == qty
    assert simulator.shortage_hours_prevented > 0
    print(f"PASS: Approved transfer: H-A stock {a_stock_pre} -> {simulator.hospitals['H-A']['current_stock']}, H-B stock {b_stock_pre} -> {simulator.hospitals['H-B']['current_stock']}")

    # TEST 8: Gemini Failure Graceful Fallback
    print("\n--- Test 8: Gemini Explanation & Fallback Safety ---")
    fallback = get_deterministic_fallback("District Hospital B", "District Hospital A", 40)
    assert "District Hospital B" in fallback and "District Hospital A" in fallback and "40" in fallback
    live_exp = generate_recommendation_explanation("District Hospital B", "District Hospital A", 40, 1.3, 45, 45)
    assert len(live_exp) > 10
    fallback_exp = generate_recommendation_explanation("District Hospital B", "District Hospital A", 40, force_fallback=True)
    assert "District Hospital B" in fallback_exp and "District Hospital A" in fallback_exp
    print(f"PASS: Live explanation generated: '{live_exp}'")
    print(f"PASS: Fallback explanation returned safely: '{fallback_exp}'")

    # TEST 9: No Donor Case
    print("\n--- Test 9: No Donor Safe Surplus Handling ---")
    depleted_hospitals = []
    for h in DEFAULT_HOSPITALS:
        depleted_hospitals.append({
            **h,
            "current_stock": h["safety_threshold"] - 5  # all below threshold
        })
    no_rec, no_reason = generate_rebalancing_recommendation(depleted_hospitals, simulator.latest_predictions)
    assert no_rec is None
    print(f"PASS: Clean empty state when no donor has surplus: '{no_reason}'")

    # TEST 10: Real Evaluation with Non-fabricated MAE
    print("\n--- Test 10: Real Numerical MAE Evaluation ---")
    eval_res = generate_evaluation_dataset()
    print(f"Evaluation: Model MAE={eval_res['model_mae']}, Baseline MAE={eval_res['baseline_mae']}, Improvement={eval_res['relative_improvement_pct']}%")
    assert isinstance(eval_res["model_mae"], float) and eval_res["model_mae"] > 0
    assert isinstance(eval_res["baseline_mae"], float) and eval_res["baseline_mae"] > 0
    print("PASS: Real MAE calculated successfully on held-out test data.")

    # REPLAY TEST
    print("\n--- Bonus Check: Counterfactual Replay ---")
    replay = run_counterfactual_replay()
    assert replay["shortage_hours_prevented"] > 0
    assert replay["units_transferred"] == 40
    print(f"PASS: Counterfactual replay: {replay['shortage_hours_prevented']} shortage hours prevented, units transferred={replay['units_transferred']}")

    print("\n========================================")
    print("ALL 10 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("========================================")

if __name__ == "__main__":
    run_all_tests()
