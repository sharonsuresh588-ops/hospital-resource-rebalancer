import math
from typing import List, Dict, Any, Optional
from datetime import datetime

# Simulation scale: 1 simulation tick represents 0.5 hours (30 minutes)
SIMULATION_HOURS_PER_TICK = 0.5

def calculate_linear_regression(x_vals: List[float], y_vals: List[float]):
    """
    Computes slope (a) and intercept (b) for y = a*x + b.
    Returns (slope, intercept, r_squared)
    """
    n = len(x_vals)
    if n < 2:
        return 0.0, y_vals[-1] if y_vals else 0.0, 0.5

    sum_x = sum(x_vals)
    sum_y = sum(y_vals)
    sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
    sum_x2 = sum(x * x for x in x_vals)
    sum_y2 = sum(y * y for y in y_vals)

    denominator = (n * sum_x2 - sum_x * sum_x)
    if abs(denominator) < 1e-9:
        return 0.0, sum_y / n, 0.5

    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n

    # Compute R^2 (coefficient of determination)
    y_mean = sum_y / n
    ss_tot = sum((y - y_mean) ** 2 for y in y_vals)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_vals, y_vals))

    if ss_tot < 1e-9:
        r_squared = 1.0 if ss_res < 1e-9 else 0.0
    else:
        r_squared = max(0.0, min(1.0, 1.0 - (ss_res / ss_tot)))

    return slope, intercept, r_squared


def predict_hospital_depletion(
    hospital_id: str,
    safety_threshold: int,
    readings: List[Dict[str, Any]],
    current_tick: int,
) -> Dict[str, Any]:
    """
    Calculates depletion rate (units/hr), time-to-shortage (hours), and confidence.
    Follows Sections 13, 14, and 15 of specification.
    """
    now_str = datetime.utcnow().isoformat()

    if not readings:
        return {
            "hospital_id": hospital_id,
            "timestamp": now_str,
            "stock": 0,
            "depletion_rate": 0.0,
            "time_to_shortage_hours": None,
            "confidence": 0.0,
            "status": "CRITICAL"
        }

    # Take up to last 8 readings
    recent_readings = readings[-8:]
    current_stock = recent_readings[-1].get("stock", 0)

    # Use ticks as time axis (1 tick = SIMULATION_HOURS_PER_TICK hours)
    # If readings have tick, use it; otherwise use indexed step
    x_hours = []
    y_stocks = []
    
    for idx, r in enumerate(recent_readings):
        t = r.get("tick", current_tick - (len(recent_readings) - 1 - idx))
        x_hours.append(t * SIMULATION_HOURS_PER_TICK)
        y_stocks.append(float(r.get("stock", 0)))

    slope, _, r_squared = calculate_linear_regression(x_hours, y_stocks)

    # In stock = slope * time + b, decrease in stock means negative slope.
    # Therefore, depletion_rate = -slope. Only consider positive depletion rates.
    depletion_rate = max(0.0, -slope)
    depletion_rate = round(depletion_rate, 2)

    # Calculate time-to-shortage
    time_to_shortage_hours: Optional[float] = None
    if current_stock <= safety_threshold:
        time_to_shortage_hours = 0.0
    elif depletion_rate > 0.05:
        calc_hours = (current_stock - safety_threshold) / depletion_rate
        if not math.isnan(calc_hours) and not math.isinf(calc_hours):
            time_to_shortage_hours = max(0.0, round(calc_hours, 2))
        else:
            time_to_shortage_hours = None
    else:
        # Stock is steady or growing, no imminent shortage
        time_to_shortage_hours = None

    # Calculate confidence based on sample count and trend stability (R^2)
    sample_factor = min(1.0, len(recent_readings) / 6.0)
    stability_factor = 0.5 + 0.5 * r_squared
    confidence = round(max(0.1, min(0.98, sample_factor * stability_factor)), 2)

    # Determine status:
    # RED = CRITICAL: current stock <= threshold OR time_to_shortage <= 2.5 hours
    # AMBER = WARNING: time_to_shortage <= 5.0 hours OR current stock <= threshold + 15
    # GREEN = SAFE: adequate time to shortage and stock above buffer
    if current_stock <= safety_threshold or (time_to_shortage_hours is not None and time_to_shortage_hours <= 2.5):
        status = "CRITICAL"
    elif (time_to_shortage_hours is not None and time_to_shortage_hours <= 5.0) or (current_stock <= safety_threshold + 20):
        status = "WARNING"
    else:
        status = "SAFE"

    return {
        "hospital_id": hospital_id,
        "timestamp": now_str,
        "stock": current_stock,
        "depletion_rate": depletion_rate,
        "time_to_shortage_hours": time_to_shortage_hours,
        "confidence": confidence,
        "status": status,
    }
