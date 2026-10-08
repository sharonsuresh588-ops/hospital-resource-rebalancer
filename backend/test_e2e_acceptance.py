import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from app.main import app

def test_full_demo_acceptance_chain():
    print("==================================================")
    print("RUNNING AUTOMATED DEMO ACCEPTANCE TEST (SECTION 49)")
    print("==================================================")

    client = TestClient(app)

    # 1. Health check
    print("\n[Step 1] GET /health")
    resp = client.get("/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    health_data = resp.json()
    print(f"Health OK: status={health_data['status']}, db={health_data['database']['status_text']}")

    # 2. Reset
    print("\n[Step 2] POST /api/simulation/reset")
    resp = client.post("/api/simulation/reset")
    assert resp.status_code == 200
    state = resp.json()["state"]
    assert len(state["hospitals"]) == 6
    assert state["simulation"]["surge_active"] is False
    assert len(state["recommendations"]) == 0
    h_a_init = next(h for h in state["hospitals"] if h["id"] == "H-A")["current_stock"]
    h_b_init = next(h for h in state["hospitals"] if h["id"] == "H-B")["current_stock"]
    print(f"Reset OK: H-A stock={h_a_init}, H-B stock={h_b_init}, recommendations=0")

    # 3. Start Simulation
    print("\n[Step 3] POST /api/simulation/start")
    resp = client.post("/api/simulation/start")
    assert resp.status_code == 200
    print("Simulation started successfully.")

    # 4. Inject Surge
    print("\n[Step 4] POST /api/simulation/surge")
    resp = client.post("/api/simulation/surge")
    assert resp.status_code == 200
    state = resp.json()["state"]
    assert state["simulation"]["surge_active"] is True
    print("Surge injected into Hospital A.")

    # 5. Advance ticks until H-A becomes critical & recommendation appears
    print("\n[Step 5] Awaiting critical condition and recommendation...")
    from app.services.simulator import simulator

    # Step simulation 3 ticks to ensure H-A drops into critical window
    for _ in range(3):
        simulator.step()

    resp = client.get("/api/state")
    assert resp.status_code == 200
    state = resp.json()

    pred_a = next(p for p in state["predictions"] if p["hospital_id"] == "H-A")
    print(f"H-A Status: {pred_a['status']}, Stock: {pred_a['stock']}, Depletion: {pred_a['depletion_rate']} u/hr, Shortage in: {pred_a['time_to_shortage_hours']} hrs")
    assert pred_a["status"] == "CRITICAL", f"Expected CRITICAL, got {pred_a['status']}"

    # 6. Verify Recommendation exists: H-B -> H-A
    print("\n[Step 6] Verifying recommendation...")
    recs = [r for r in state["recommendations"] if r["status"] == "pending"]
    assert len(recs) > 0, "No pending recommendation generated!"
    rec = recs[0]
    print(f"Found Recommendation: ID={rec['id']}, {rec['from_hospital']} -> {rec['to_hospital']}, Qty={rec['quantity']}, Deadline={rec['dispatch_deadline_minutes']}m")
    assert rec["from_hospital"] == "H-B", f"Expected source H-B, got {rec['from_hospital']}"
    assert rec["to_hospital"] == "H-A", f"Expected destination H-A, got {rec['to_hospital']}"
    assert rec["quantity"] >= 30, f"Expected quantity >= 30, got {rec['quantity']}"
    print(f"Justification: '{rec['justification']}'")

    # 7. Approve Transfer
    print(f"\n[Step 7] POST /api/recommendations/{rec['id']}/approve")
    stock_a_before = next(h for h in state["hospitals"] if h["id"] == "H-A")["current_stock"]
    stock_b_before = next(h for h in state["hospitals"] if h["id"] == "H-B")["current_stock"]

    resp = client.post(f"/api/recommendations/{rec['id']}/approve")
    assert resp.status_code == 200, f"Approve failed: {resp.text}"
    approved_state = resp.json()["state"]

    stock_a_after = next(h for h in approved_state["hospitals"] if h["id"] == "H-A")["current_stock"]
    stock_b_after = next(h for h in approved_state["hospitals"] if h["id"] == "H-B")["current_stock"]

    print(f"Transfer applied: H-A stock {stock_a_before} -> {stock_a_after} (+{rec['quantity']})")
    print(f"Transfer applied: H-B stock {stock_b_before} -> {stock_b_after} (-{rec['quantity']})")
    assert stock_a_after == stock_a_before + rec["quantity"], "H-A stock did not increase by quantity"
    assert stock_b_after == stock_b_before - rec["quantity"], "H-B stock did not decrease by quantity"

    # Verify donor remained above safety threshold
    donor_thresh = next(h for h in approved_state["hospitals"] if h["id"] == "H-B")["safety_threshold"]
    assert stock_b_after >= donor_thresh, f"Donor stock {stock_b_after} fell below threshold {donor_thresh}!"
    print(f"Donor H-B stock {stock_b_after} safely above threshold {donor_thresh}.")

    # Verify H-A shortage improved
    pred_a_after = next(p for p in approved_state["predictions"] if p["hospital_id"] == "H-A")
    print(f"H-A new shortage horizon: {pred_a_after['time_to_shortage_hours']} hrs (was {pred_a['time_to_shortage_hours']} hrs)")
    print(f"Shortage hours prevented: {approved_state['metrics']['shortage_hours_prevented']}")
    assert approved_state["metrics"]["shortage_hours_prevented"] > 0

    # 8. Replay scenario
    print("\n[Step 8] GET /api/replay")
    resp = client.get("/api/replay")
    assert resp.status_code == 200
    replay = resp.json()
    print(f"Replay Results:")
    print(f"  Without system shortage hours: {replay['without_system']['shortage_hours']}h")
    print(f"  With system shortage hours:    {replay['with_system']['shortage_hours']}h")
    print(f"  Shortage prevented:            {replay['shortage_hours_prevented']}h")
    print(f"  Units transferred:             {replay['units_transferred']}")
    assert replay["shortage_hours_prevented"] > 0
    assert replay["units_transferred"] == 40

    # 9. Model Evaluation
    print("\n[Step 9] GET /api/evaluation")
    resp = client.get("/api/evaluation")
    assert resp.status_code == 200
    evaluation = resp.json()
    print(f"Model MAE:       {evaluation['model_mae']}")
    print(f"Baseline MAE:    {evaluation['baseline_mae']}")
    print(f"Relative Impv:   {evaluation['relative_improvement_pct']}%")
    assert evaluation["model_mae"] > 0
    assert evaluation["baseline_mae"] > 0

    print("\n==================================================")
    print("SUCCESS: AUTOMATED DEMO ACCEPTANCE TEST FULLY PASSED!")
    print("==================================================")

if __name__ == "__main__":
    test_full_demo_acceptance_chain()
