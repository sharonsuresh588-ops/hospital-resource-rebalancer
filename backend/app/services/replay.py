from typing import Dict, Any, List

def run_counterfactual_replay(
    surge_ticks: int = 15,
    normal_rate_h_a: float = 4.0,
    surge_rate_h_a: float = 18.0,
    h_a_safety_threshold: int = 60,
    h_a_initial_stock: int = 145,
    h_b_initial_stock: int = 195,
    transfer_tick: int = 4,
    transfer_quantity: int = 40,
    hours_per_tick: float = 0.5,
) -> Dict[str, Any]:
    """
    Simulates the exact deterministic surge scenario twice (Sections 37 & 38):
    1. WITHOUT SYSTEM: No transfer occurs; Hospital A depletes below safety threshold.
    2. WITH SYSTEM: Calculated transfer (40 units B -> A) applied at intervention tick.
    Returns calculated shortage-hours and timeline comparison.
    """
    # 1. WITHOUT SYSTEM SCENARIO
    stock_a_without = h_a_initial_stock
    stock_b_without = h_b_initial_stock
    shortage_hours_without = 0.0
    critical_events_without = 0
    timeline_without = []

    for t in range(1, surge_ticks + 1):
        # Consumption for H-A: surge occurs from t >= 1
        stock_a_without = max(0, stock_a_without - surge_rate_h_a)
        stock_b_without = max(0, stock_b_without - 2.0)

        # Deficit check
        if stock_a_without < h_a_safety_threshold:
            critical_events_without += 1
            # Deficit duration in hours
            shortage_hours_without += hours_per_tick

        timeline_without.append({
            "tick": t,
            "h_a_stock": round(stock_a_without, 1),
            "h_b_stock": round(stock_b_without, 1),
            "is_critical": stock_a_without < h_a_safety_threshold,
            "system_active": False,
        })

    # 2. WITH SYSTEM SCENARIO
    stock_a_with = h_a_initial_stock
    stock_b_with = h_b_initial_stock
    shortage_hours_with = 0.0
    critical_events_with = 0
    timeline_with = []

    for t in range(1, surge_ticks + 1):
        stock_a_with = max(0, stock_a_with - surge_rate_h_a)
        stock_b_with = max(0, stock_b_with - 2.0)

        # Apply transfer at intervention tick
        transfer_applied_this_tick = False
        if t == transfer_tick:
            stock_a_with += transfer_quantity
            stock_b_with -= transfer_quantity
            transfer_applied_this_tick = True

        if stock_a_with < h_a_safety_threshold:
            critical_events_with += 1
            shortage_hours_with += hours_per_tick

        timeline_with.append({
            "tick": t,
            "h_a_stock": round(stock_a_with, 1),
            "h_b_stock": round(stock_b_with, 1),
            "is_critical": stock_a_with < h_a_safety_threshold,
            "transfer_applied": transfer_applied_this_tick,
            "system_active": True,
        })

    shortage_prevented = round(max(0.0, shortage_hours_without - shortage_hours_with), 1)

    combined_timeline = []
    for t in range(surge_ticks):
        w_out = timeline_without[t]
        w_in = timeline_with[t]
        combined_timeline.append({
            "tick": w_out["tick"],
            "without_system_a": w_out["h_a_stock"],
            "with_system_a": w_in["h_a_stock"],
            "safety_threshold": h_a_safety_threshold,
            "transfer_applied": w_in.get("transfer_applied", False),
        })

    return {
        "without_system": {
            "shortage_hours": round(shortage_hours_without, 1),
            "units_transferred": 0,
            "critical_events": critical_events_without,
            "timeline": timeline_without,
        },
        "with_system": {
            "shortage_hours": round(shortage_hours_with, 1),
            "units_transferred": transfer_quantity,
            "critical_events": critical_events_with,
            "timeline": timeline_with,
        },
        "shortage_hours_prevented": shortage_prevented,
        "units_transferred": transfer_quantity,
        "timeline": combined_timeline,
        "summary": (
            f"Deterministic intervention prevented {shortage_prevented} shortage-hours "
            f"by redistributing {transfer_quantity} cylinders before critical exhaustion."
        ),
    }
