import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from app.database import db_manager, DatabaseManager, REQUIRED_COLLECTIONS
from app.services.simulator import simulator
from app.services.evaluation import generate_evaluation_dataset
from app.services.replay import run_counterfactual_replay

def test_mongodb_integration():
    print("========================================================")
    print("TESTING MONGODB PERSISTENCE & ATLAS INTEGRATION (PHASE 1)")
    print("========================================================")

    # 1. Verify required collections
    print("\n[Check 1] Verifying 5 Required Collections Definition")
    for col_name in ["hospitals", "readings", "predictions", "recommendations", "evaluation_runs"]:
        assert col_name in REQUIRED_COLLECTIONS, f"Missing required collection: {col_name}"
        col = db_manager.get_collection(col_name)
        assert col is not None, f"Collection {col_name} could not be resolved"
    print("PASS: All 5 collections defined and accessible:", REQUIRED_COLLECTIONS)

    # 2. Reset simulator and check initial database documents
    print("\n[Check 2] Resetting Simulator and Verifying Database State")
    simulator.reset()
    status = db_manager.get_status_info()
    print(f"Database Mode: {status['status_text']} ({status['provider']})")
    print(f"Collections Document Counts: {status['collections']}")

    # hospitals collection must have 6 documents
    hosp_count = db_manager.get_collection("hospitals").count_documents({})
    assert hosp_count == 6, f"Expected 6 hospitals in database, found {hosp_count}"
    print(f"PASS: 'hospitals' collection contains 6 documents.")

    # readings collection must have initial seed readings (3 per hospital = 18)
    initial_readings_count = db_manager.get_collection("readings").count_documents({})
    assert initial_readings_count >= 18, f"Expected >= 18 readings, found {initial_readings_count}"
    print(f"PASS: 'readings' collection initialized with {initial_readings_count} baseline telemetry readings.")

    # predictions collection must have 6 predictions
    preds_count = db_manager.get_collection("predictions").count_documents({})
    assert preds_count >= 6, f"Expected >= 6 predictions, found {preds_count}"
    print(f"PASS: 'predictions' collection initialized with {preds_count} baseline predictions.")

    # evaluation_runs collection must have at least 1 benchmark
    eval_count = db_manager.get_collection("evaluation_runs").count_documents({})
    assert eval_count >= 1, f"Expected >= 1 evaluation runs, found {eval_count}"
    print(f"PASS: 'evaluation_runs' collection initialized with {eval_count} record.")

    # 3. Test Live Simulated Readings Persistence (Task 6)
    print("\n[Check 3] Evidence That Live Readings Are Being Persisted (Task 6)")
    readings_before = db_manager.get_collection("readings").count_documents({})
    
    # Step simulator 3 ticks
    ticks_to_step = 3
    for _ in range(ticks_to_step):
        simulator.step()

    readings_after = db_manager.get_collection("readings").count_documents({})
    new_readings = readings_after - readings_before
    expected_new = 6 * ticks_to_step  # 6 hospitals * 3 ticks = 18 new readings
    print(f"Readings before 3 ticks: {readings_before}")
    print(f"Readings after 3 ticks:  {readings_after} (+{new_readings} new readings)")
    assert new_readings == expected_new, f"Expected {expected_new} new readings, got {new_readings}"

    # Inspect the newest reading document
    latest_readings = db_manager.get_collection("readings").find(sort=[("tick", -1)], limit=1)
    assert len(latest_readings) > 0
    sample_reading = latest_readings[0]
    print(f"Sample Persisted Reading Document: {sample_reading}")
    assert "hospital_id" in sample_reading
    assert "stock" in sample_reading
    assert "timestamp" in sample_reading
    assert "tick" in sample_reading
    assert sample_reading.get("resource") == "oxygen_cylinders"
    assert isinstance(sample_reading.get("_id"), str), "Document _id must be serializable string"
    print("PASS: Live simulated readings are reliably persisted to database on every tick.")

    # 4. Test Surge Scenario & Recommendation Persistence
    print("\n[Check 4] Persisting Surge Predictions & Recommendations")
    simulator.inject_surge()
    simulator.step()
    simulator.step()

    # Verify recommendation was written to recommendations collection
    recs_col = db_manager.get_collection("recommendations")
    recs_in_db = recs_col.find(query={"status": "pending"})
    assert len(recs_in_db) > 0, "No pending recommendation persisted in database!"
    rec = recs_in_db[0]
    print(f"Persisted Recommendation in DB: ID={rec['id']}, {rec['from_hospital']} -> {rec['to_hospital']}, qty={rec['quantity']}, status={rec['status']}")
    assert rec["from_hospital"] == "H-B"
    assert rec["to_hospital"] == "H-A"
    assert rec["status"] == "pending"
    print("PASS: Optimizer recommendation persisted to 'recommendations' collection.")

    # 5. Test Transfer Approval Persistence
    print(f"\n[Check 5] Approving Recommendation {rec['id']} & Verifying State Update")
    simulator.approve_recommendation(rec["id"])
    
    # Check recommendations collection updated to approved
    approved_rec_doc = recs_col.find_one(query={"id": rec["id"]})
    assert approved_rec_doc is not None
    assert approved_rec_doc["status"] == "approved"
    print(f"PASS: Recommendation status updated in DB: {approved_rec_doc['status']}")

    # Check hospitals collection has updated stock for H-A and H-B
    h_a_doc = db_manager.get_collection("hospitals").find_one(query={"id": "H-A"})
    h_b_doc = db_manager.get_collection("hospitals").find_one(query={"id": "H-B"})
    assert h_a_doc is not None and h_b_doc is not None
    print(f"H-A stock in 'hospitals' collection: {h_a_doc['current_stock']}")
    print(f"H-B stock in 'hospitals' collection: {h_b_doc['current_stock']}")
    assert h_a_doc["current_stock"] == simulator.hospitals["H-A"]["current_stock"]
    assert h_b_doc["current_stock"] == simulator.hospitals["H-B"]["current_stock"]
    print("PASS: Facility stock updates synchronized in 'hospitals' collection.")

    # 6. Test Evaluation Persistence
    print("\n[Check 6] Persisting Evaluation Runs to 'evaluation_runs'")
    fresh_eval = generate_evaluation_dataset()
    eval_col = db_manager.get_collection("evaluation_runs")
    eval_col.insert_one(fresh_eval)
    eval_docs = eval_col.find(sort=[("timestamp", -1)], limit=1)
    assert len(eval_docs) > 0
    persisted_eval = eval_docs[0]
    print(f"Persisted Evaluation Run: Model MAE={persisted_eval['model_mae']}, Baseline MAE={persisted_eval['baseline_mae']}")
    assert persisted_eval["model_mae"] > 0
    print("PASS: Evaluation runs safely persisted.")

    # 7. Test Replay Scenario Unchanged & Operational
    print("\n[Check 7] Verifying Counterfactual Replay Operation")
    replay = run_counterfactual_replay()
    assert replay["shortage_hours_prevented"] > 0
    assert replay["units_transferred"] == 40
    print(f"PASS: Counterfactual replay verified: prevented={replay['shortage_hours_prevented']}h")

    # 8. Test In-Memory Fallback Resilience Under Connection Failure
    print("\n[Check 8] Verifying In-Memory Fallback Under Simulated Connection Failure")
    test_db = DatabaseManager()
    # Attempt connecting to invalid URI
    test_db.connect()  # with empty URI
    assert test_db.is_connected is False
    assert test_db.mode == "DEMO FALLBACK"
    test_hosp_col = test_db.get_collection("hospitals")
    test_hosp_col.insert_one({"id": "TEST", "name": "Test Hospital"})
    assert test_hosp_col.count_documents({"id": "TEST"}) == 1
    print("PASS: In-memory fallback functions seamlessly when MongoDB Atlas is unconfigured or unreachable.")

    print("\n========================================================")
    print("ALL MONGODB INTEGRATION CHECKS PASSED (100% SUCCESS)!")
    print("========================================================")

if __name__ == "__main__":
    test_mongodb_integration()
