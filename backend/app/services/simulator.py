import asyncio
import logging
import math
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.database import db_manager
from app.services.predictor import predict_hospital_depletion, compute_network_risk_ranking
from app.services.optimizer import generate_rebalancing_recommendation
from app.services.evaluation import DEFAULT_EVALUATION
from app.services.audit import record_audit_event, get_audit_trail

logger = logging.getLogger("simulator")

# 6 Hospitals definition with deterministic baseline stocks
DEFAULT_HOSPITALS = [
    {
        "id": "H-A",
        "name": "District Hospital A",
        "lat": 13.0827,
        "lng": 80.2707,
        "capacity": 200,
        "safety_threshold": 60,
        "initial_stock": 145,
        "base_rate": 3.8,
    },
    {
        "id": "H-B",
        "name": "District Hospital B",
        "lat": 13.0358,
        "lng": 80.2443,
        "capacity": 220,
        "safety_threshold": 65,
        "initial_stock": 195,
        "base_rate": 2.0,
    },
    {
        "id": "H-C",
        "name": "District Hospital C",
        "lat": 13.0012,
        "lng": 80.2565,
        "capacity": 180,
        "safety_threshold": 50,
        "initial_stock": 130,
        "base_rate": 2.2,
    },
    {
        "id": "H-D",
        "name": "District Hospital D",
        "lat": 13.1147,
        "lng": 80.2124,
        "capacity": 210,
        "safety_threshold": 60,
        "initial_stock": 155,
        "base_rate": 2.5,
    },
    {
        "id": "H-E",
        "name": "District Hospital E",
        "lat": 12.9815,
        "lng": 80.2180,
        "capacity": 190,
        "safety_threshold": 55,
        "initial_stock": 125,
        "base_rate": 1.8,
    },
    {
        "id": "H-F",
        "name": "District Hospital F",
        "lat": 13.0500,
        "lng": 80.1800,
        "capacity": 175,
        "safety_threshold": 50,
        "initial_stock": 115,
        "base_rate": 2.0,
    },
]

class HospitalSimulator:
    def __init__(self):
        self.tick: int = 0
        self.running: bool = False
        self.surge_active: bool = False
        self.multi_surge: bool = False
        self.scenario_name: str = "standard_surge"
        self.hospitals: Dict[str, Dict[str, Any]] = {}
        self.history: Dict[str, List[Dict[str, Any]]] = {h["id"]: [] for h in DEFAULT_HOSPITALS}
        self.latest_predictions: List[Dict[str, Any]] = []
        self.active_recommendations: List[Dict[str, Any]] = []
        self.units_transferred: int = 0
        self.shortage_hours_prevented: float = 0.0
        self.transfers_completed: int = 0
        self._loop_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.reset()

    def reset(self):
        """Restores system to exact initial demo state."""
        self.tick = 0
        self.surge_active = False
        self.multi_surge = False
        self.scenario_name = "standard_surge"
        self.units_transferred = 0
        self.shortage_hours_prevented = 0.0
        self.transfers_completed = 0
        self.hospitals = {}
        self.history = {h["id"]: [] for h in DEFAULT_HOSPITALS}
        self.active_recommendations = []

        now_str = datetime.utcnow().isoformat()
        hospitals_col = db_manager.get_collection("hospitals")
        readings_col = db_manager.get_collection("readings")
        recs_col = db_manager.get_collection("recommendations")
        preds_col = db_manager.get_collection("predictions")

        # Clear active demo readings and recommendations
        readings_col.delete_many({})
        recs_col.delete_many({})
        preds_col.delete_many({})

        # Initialize hospitals and seed 3 baseline readings so regression has context
        for h in DEFAULT_HOSPITALS:
            init_stock = h["initial_stock"]
            self.hospitals[h["id"]] = {
                "id": h["id"],
                "name": h["name"],
                "lat": h["lat"],
                "lng": h["lng"],
                "capacity": h["capacity"],
                "safety_threshold": h["safety_threshold"],
                "current_stock": init_stock,
                "base_rate": h["base_rate"],
            }
            hospitals_col.update_one(
                {"id": h["id"]},
                {"$set": self.hospitals[h["id"]]},
                upsert=True
            )

            for offset in [-2, -1, 0]:
                historical_stock = init_stock - int(offset * h["base_rate"])
                reading = {
                    "hospital_id": h["id"],
                    "timestamp": now_str,
                    "tick": offset,
                    "stock": historical_stock,
                    "resource": "oxygen_cylinders",
                }
                self.history[h["id"]].append(reading)
                readings_col.insert_one(reading)

        # Record evaluation benchmark
        eval_col = db_manager.get_collection("evaluation_runs")
        eval_col.insert_one(DEFAULT_EVALUATION)

        # Calculate initial predictions
        self._recalculate_predictions()
        
        record_audit_event("SIMULATION_RESET", {
            "tick": 0,
            "scenario": "standard_surge",
            "message": "Simulator reset to deterministic baseline state.",
        })
        logger.info("Simulator reset to deterministic initial baseline state.")

    def _recalculate_predictions(self):
        """Runs trend regression and shortage estimation across all 6 hospitals."""
        preds = []
        preds_col = db_manager.get_collection("predictions")
        for hid, h in self.hospitals.items():
            h_readings = self.history.get(hid, [])
            p = predict_hospital_depletion(
                hospital_id=hid,
                safety_threshold=h["safety_threshold"],
                readings=h_readings,
                current_tick=self.tick,
            )
            preds.append(p)
            preds_col.insert_one(p)

        self.latest_predictions = preds
        return preds

    def step(self):
        """Executes one deterministic simulation tick."""
        self.tick += 1
        now_str = datetime.utcnow().isoformat()
        readings_col = db_manager.get_collection("readings")
        hospitals_col = db_manager.get_collection("hospitals")

        for hid, h in self.hospitals.items():
            base = h["base_rate"]
            variation = 0.3 * math.sin(self.tick * 0.8 + hash(hid) % 5)
            rate = base + variation

            # SURGE SCENARIO: Hospital A consumes rapidly (16-18 units/tick)
            if self.surge_active and hid == "H-A":
                rate = 17.5 + 0.5 * math.sin(self.tick)

            # MULTI-HOSPITAL STRESS SCENARIO
            if self.multi_surge and hid == "H-D":
                rate = 14.0 + 0.5 * math.cos(self.tick)

            new_stock = max(5, int(round(h["current_stock"] - rate)))
            h["current_stock"] = new_stock

            hospitals_col.update_one(
                {"id": hid},
                {"$set": {"current_stock": new_stock}},
                upsert=True
            )

            reading = {
                "hospital_id": hid,
                "timestamp": now_str,
                "tick": self.tick,
                "stock": new_stock,
                "resource": "oxygen_cylinders",
            }
            self.history[hid].append(reading)
            if len(self.history[hid]) > 50:
                self.history[hid] = self.history[hid][-50:]

            readings_col.insert_one(reading)

        # Recalculate predictions
        self._recalculate_predictions()

        # Check optimizer if shortage or surge is active
        has_pending = any(r.get("status") in ["pending", "no_safe_transfer"] for r in self.active_recommendations)
        if not has_pending:
            rec, reason = generate_rebalancing_recommendation(
                hospitals=list(self.hospitals.values()),
                predictions=self.latest_predictions,
            )
            if rec:
                self.active_recommendations.append(rec)
                recs_col = db_manager.get_collection("recommendations")
                recs_col.insert_one(rec)
                logger.info(f"Generated rebalancing recommendation: {rec.get('from_hospital')} -> {rec.get('to_hospital')} ({rec.get('quantity')} units)")

    async def _run_loop(self):
        """Continuous simulation loop ticking every 3.0 seconds."""
        logger.info("Simulation loop started.")
        try:
            while self.running:
                async with self._lock:
                    self.step()
                await asyncio.sleep(3.0)
        except asyncio.CancelledError:
            logger.info("Simulation loop task was cancelled.")
        except Exception as e:
            logger.error(f"Error in simulation loop: {e}", exc_info=True)
            self.running = False

    def start(self):
        """Starts the simulator if not already running."""
        if self.running and self._loop_task and not self._loop_task.done():
            logger.info("Simulator already running.")
            return
        self.running = True
        try:
            loop = asyncio.get_running_loop()
            self._loop_task = loop.create_task(self._run_loop())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop_task = loop.create_task(self._run_loop())

    def stop(self):
        """Stops the simulator loop."""
        self.running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            self._loop_task = None

    def inject_surge(self):
        """Activates surge scenario for Hospital A."""
        self.surge_active = True
        self.scenario_name = "standard_surge"
        logger.info("Demand surge injected into Hospital A!")
        record_audit_event("SURGE_INJECTED", {
            "target_hospital": "H-A",
            "tick": self.tick,
            "message": "Demand surge injected into District Hospital A.",
        })
        if not self.running:
            self.step()

    def set_scenario(self, scenario_name: str):
        """
        Feature 11 — Demo Scenario Control.
        Presets:
          - 'standard_surge': Hospital A surge, Hospital B donor (primary hackathon demo).
          - 'normal_operations': Normal calm telemetry across all facilities.
          - 'multi_hospital_stress': Simultaneous surges on H-A and H-D.
          - 'no_safe_donor': Severe regional depletion where no safe transfer is possible.
        """
        self.scenario_name = scenario_name
        if scenario_name == "normal_operations":
            self.surge_active = False
            self.multi_surge = False
            self.reset()
        elif scenario_name == "standard_surge":
            self.multi_surge = False
            self.inject_surge()
        elif scenario_name == "multi_hospital_stress":
            self.surge_active = True
            self.multi_surge = True
            self.step()
        elif scenario_name == "no_safe_donor":
            self.surge_active = True
            self.multi_surge = False
            # Reduce all potential donor surplus stocks close to safety threshold
            for hid, h in self.hospitals.items():
                if hid != "H-A":
                    h["current_stock"] = h["safety_threshold"] + 4
            self.step()

        record_audit_event("SCENARIO_SWITCHED", {
            "scenario": scenario_name,
            "tick": self.tick,
        })

    def approve_recommendation(self, rec_id: str) -> Dict[str, Any]:
        """
        Executes human approval of transfer.
        Re-validates donor safety, updates stocks, recalculates predictions, records metrics.
        """
        rec = None
        for r in self.active_recommendations:
            if r["id"] == rec_id:
                rec = r
                break

        if not rec:
            raise ValueError(f"Recommendation with ID '{rec_id}' not found.")

        if rec["status"] == "no_safe_transfer":
            raise ValueError("Cannot approve transfer: No safe donor exists. Immediate external escalation required.")

        if rec["status"] != "pending":
            raise ValueError(f"Recommendation is already {rec['status']}.")

        from_id = rec["from_hospital"]
        to_id = rec["to_hospital"]
        quantity = rec["quantity"]

        donor = self.hospitals.get(from_id)
        destination = self.hospitals.get(to_id)

        if not donor or not destination:
            raise ValueError("Hospital entities not found in simulator.")

        # Revalidate donor safety rule
        if (donor["current_stock"] - quantity) < donor["safety_threshold"]:
            rec["status"] = "rejected"
            raise ValueError(
                f"Donor safety violation: {donor['name']} stock ({donor['current_stock']}) "
                f"would fall below safety threshold ({donor['safety_threshold']}) after {quantity} transfer."
            )

        # Apply stock transfer
        donor["current_stock"] -= quantity
        destination["current_stock"] += quantity

        rec["status"] = "approved"
        rec["approved_at"] = datetime.utcnow().isoformat()

        self.units_transferred += quantity
        self.transfers_completed += 1
        self.shortage_hours_prevented += round(quantity / 8.0, 1)

        now_str = datetime.utcnow().isoformat()
        readings_col = db_manager.get_collection("readings")
        hospitals_col = db_manager.get_collection("hospitals")

        for hid in [from_id, to_id]:
            hospitals_col.update_one(
                {"id": hid},
                {"$set": {"current_stock": self.hospitals[hid]["current_stock"]}},
                upsert=True
            )
            reading = {
                "hospital_id": hid,
                "timestamp": now_str,
                "tick": self.tick,
                "stock": self.hospitals[hid]["current_stock"],
                "resource": "oxygen_cylinders",
                "transfer_event": True,
            }
            self.history[hid].append(reading)
            readings_col.insert_one(reading)

        recs_col = db_manager.get_collection("recommendations")
        recs_col.update_one(
            {"id": rec_id},
            {"$set": {"status": "approved", "approved_at": rec.get("approved_at", now_str)}},
            upsert=True
        )

        self._recalculate_predictions()

        record_audit_event("TRANSFER_APPROVED", {
            "recommendation_id": rec_id,
            "from_hospital": from_id,
            "to_hospital": to_id,
            "quantity": quantity,
            "approved_by": "Human Operations Coordinator",
            "stock_after": {
                from_id: donor["current_stock"],
                to_id: destination["current_stock"],
            },
            "shortage_hours_prevented": self.shortage_hours_prevented,
        })

        logger.info(f"Transfer approved: {quantity} units transferred from {from_id} to {to_id}.")
        return rec

    def get_consolidated_state(self) -> Dict[str, Any]:
        """Provides consolidated dashboard payload for /api/state."""
        critical_count = sum(
            1 for p in self.latest_predictions if p.get("status") == "CRITICAL"
        )
        active_recs_count = sum(
            1 for r in self.active_recommendations if r.get("status") == "pending"
        )

        # Feature 4: Network Risk Priority
        risk_ranking = compute_network_risk_ranking(
            hospitals=list(self.hospitals.values()),
            predictions=self.latest_predictions,
        )

        # Feature 8: Decision Audit Trail
        audit_trail = get_audit_trail(limit=15)

        db_info = db_manager.get_status_info()

        # Build clean history for charts
        timeline = []
        max_len = max((len(h) for h in self.history.values()), default=0)
        for i in range(max_len):
            point = {}
            for hid, h_list in self.history.items():
                if i < len(h_list):
                    point["tick"] = h_list[i].get("tick", i)
                    point[hid] = h_list[i].get("stock", 0)
            if "tick" in point:
                timeline.append(point)

        return {
            "simulation": {
                "running": self.running,
                "surge_active": self.surge_active,
                "tick": self.tick,
                "tick_interval_seconds": 3.0,
                "scenario_name": self.scenario_name,
            },
            "hospitals": list(self.hospitals.values()),
            "predictions": self.latest_predictions,
            "recommendations": self.active_recommendations,
            "network_risk_ranking": risk_ranking,
            "audit_trail": audit_trail,
            "evaluation": DEFAULT_EVALUATION,
            "metrics": {
                "shortage_hours_prevented": round(self.shortage_hours_prevented, 1),
                "units_transferred": self.units_transferred,
                "transfers_completed": self.transfers_completed,
                "hospitals_monitored": len(self.hospitals),
                "critical_shortages": critical_count,
                "active_recommendations": active_recs_count,
                "safe_transfer_opportunities": 1 if any(r.get("status") == "pending" and r.get("is_safe_transfer", True) for r in self.active_recommendations) else 0,
                "hospitals_at_risk": sum(1 for r in risk_ranking if r.get("risk_level") in ["CRITICAL", "WARNING", "NETWORK EMERGENCY"]),
            },
            "system_health": {
                "api": "HEALTHY",
                "database": db_info,
                "simulator": "RUNNING" if self.running else "IDLE",
            },
            "timeline": timeline[-25:],
        }


simulator = HospitalSimulator()
