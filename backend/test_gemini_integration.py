import sys
import os
import requests

sys.path.insert(0, os.path.dirname(__file__))

from app.services.gemini import generate_recommendation_explanation, get_deterministic_fallback
from app.services.simulator import simulator
from app.services.optimizer import generate_rebalancing_recommendation
from app.config import GEMINI_API_KEY

def test_gemini_integration():
    print("=====================================================")
    print("TESTING GEMINI INTEGRATION (PHASE 2)")
    print("=====================================================")

    # 1. Verify GEMINI_API_KEY is present in backend configuration
    print("\n[Check 1] Checking Backend GEMINI_API_KEY Configuration")
    assert bool(GEMINI_API_KEY), "GEMINI_API_KEY is missing from backend configuration!"
    assert GEMINI_API_KEY.startswith("AIzaSy") or GEMINI_API_KEY.startswith("AQ."), "GEMINI_API_KEY does not have expected prefix"
    print(f"PASS: GEMINI_API_KEY is configured (Length: {len(GEMINI_API_KEY)}, Prefix: {GEMINI_API_KEY[:6]}...)")

    # 2. Test Live Gemini API Explanation Generation
    print("\n[Check 2] Generating Operational Explanation via Gemini API")
    explanation = generate_recommendation_explanation(
        from_hospital="District Hospital B",
        to_hospital="District Hospital A",
        quantity=40,
        destination_shortage_hours=1.3,
        source_safe_surplus=45,
        dispatch_deadline_minutes=45,
    )
    print("Gemini Generated Explanation:")
    print(f"  \"{explanation}\"")
    words = explanation.split()
    print(f"  Word count: {len(words)}")
    assert len(words) >= 6, f"Explanation too short: {explanation}"
    assert len(words) <= 30, f"Explanation exceeds 30 words: {explanation}"
    print("PASS: Gemini generated concise operational explanation.")

    # 3. Test Deterministic Fallback Mechanism (Section 24)
    print("\n[Check 3] Testing Deterministic Fallback on Gemini Failure / Fallback Trigger")
    fallback = generate_recommendation_explanation(
        from_hospital="District Hospital B",
        to_hospital="District Hospital A",
        quantity=40,
        destination_shortage_hours=1.3,
        source_safe_surplus=45,
        dispatch_deadline_minutes=45,
        force_fallback=True,
    )
    print("Fallback Explanation:")
    print(f"  \"{fallback}\"")
    assert "District Hospital B" in fallback
    assert "District Hospital A" in fallback
    assert "40" in fallback
    assert "reaches safety threshold first" in fallback
    print("PASS: Deterministic fallback explanation verified.")

    # 4. Invariant Check: Python owns the decision (Section 2)
    print("\n[Check 4] Invariant: Deterministic Python Optimizer Owns Transfer Decision")
    simulator.reset()
    simulator.inject_surge()
    simulator.step()
    simulator.step()

    rec, reason = generate_rebalancing_recommendation(
        list(simulator.hospitals.values()),
        simulator.latest_predictions
    )
    assert rec is not None, "Failed to generate recommendation"
    assert rec["from_hospital"] == "H-B", f"Expected H-B, got {rec['from_hospital']}"
    assert rec["to_hospital"] == "H-A", f"Expected H-A, got {rec['to_hospital']}"
    assert rec["quantity"] == 40, f"Expected 40 cylinders, got {rec['quantity']}"
    assert rec["status"] == "pending"
    assert bool(rec["justification"]), "Recommendation missing justification"
    print(f"Python Decision Parameters:")
    print(f"  Source: {rec['from_hospital']}")
    print(f"  Destination: {rec['to_hospital']}")
    print(f"  Quantity: {rec['quantity']} cylinders")
    print(f"  Dispatch Deadline: {rec['dispatch_deadline_minutes']} min")
    print(f"  Explanation attached: \"{rec['justification']}\"")
    print("PASS: Python logic strictly owns 100% of transfer parameters.")

    # 5. Security Check: API Key is never exposed in API endpoints (Section 42)
    print("\n[Check 5] Security: Verifying GEMINI_API_KEY is Never Leaked in API Responses")
    base_url = "http://127.0.0.1:8000"
    state_resp = requests.get(f"{base_url}/api/state").json()
    health_resp = requests.get(f"{base_url}/health").json()

    state_str = str(state_resp)
    health_str = str(health_resp)
    assert GEMINI_API_KEY not in state_str, "CRITICAL: GEMINI_API_KEY leaked in /api/state!"
    assert GEMINI_API_KEY not in health_str, "CRITICAL: GEMINI_API_KEY leaked in /health!"
    print("PASS: GEMINI_API_KEY is not exposed to frontend or API responses.")

    # 6. Test POST /api/gemini/explain Endpoint
    print("\n[Check 6] Testing POST /api/gemini/explain Endpoint")
    payload = {
        "from_hospital": "District Hospital B",
        "to_hospital": "District Hospital A",
        "quantity": 40,
        "destination_shortage_hours": 1.2,
        "source_safe_surplus": 45,
        "dispatch_deadline_minutes": 45
    }
    explain_resp = requests.post(f"{base_url}/api/gemini/explain", json=payload)
    assert explain_resp.status_code == 200, f"Explain endpoint failed: {explain_resp.text}"
    exp_data = explain_resp.json()
    assert "explanation" in exp_data
    print(f"Endpoint Explanation: \"{exp_data['explanation']}\"")
    print("PASS: POST /api/gemini/explain functions successfully.")

    print("\n=====================================================")
    print("ALL GEMINI INTEGRATION TESTS PASSED (100% SUCCESS)!")
    print("=====================================================")

if __name__ == "__main__":
    test_gemini_integration()
