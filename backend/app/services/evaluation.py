import math
from typing import Dict, Any, List
from datetime import datetime

def generate_evaluation_dataset() -> Dict[str, Any]:
    """
    Generates a deterministic synthetic time-series of hospital oxygen demand
    with realistic cyclical fluctuations and stochastic demand shocks,
    splits into train and held-out test sets, and compares linear trend regression
    against a naive baseline (most recently observed single-step change).
    """
    # Deterministic sequence: 60 sequential simulated time steps
    # Underlying dynamics: baseline consumption = 4.0 units/hr with slight periodic diurnal fluctuation
    # plus small deterministic noise.
    total_steps = 60
    train_steps = 40
    test_steps = 20

    base_stock = 450.0
    actual_stocks: List[float] = []
    
    current = base_stock
    for t in range(total_steps):
        # Deterministic variation: gradual consumption + cyclical diurnal variation
        diurnal = 0.8 * math.sin(2.0 * math.pi * t / 24.0)
        consumption = 4.0 + diurnal
        current = max(20.0, current - consumption)
        # Telemetry sensor noise on observed stock readings
        sensor_noise = 2.2 * math.cos(4.7 * t)
        observed_stock = current + sensor_noise
        actual_stocks.append(round(observed_stock, 2))

    train_data = actual_stocks[:train_steps]
    test_data = actual_stocks[train_steps:]

    # 1. Fit Multi-sample Linear Trend Model on Train Data (using last 15 readings to smooth noise)
    window_size = 15
    y_train = train_data[-window_size:]
    x_train = list(range(len(y_train)))
    n = len(x_train)
    sum_x = sum(x_train)
    sum_y = sum(y_train)
    sum_xy = sum(x * y for x, y in zip(x_train, y_train))
    sum_x2 = sum(x * x for x in x_train)
    
    denom = (n * sum_x2 - sum_x * sum_x)
    slope = (n * sum_xy - sum_x * sum_y) / denom if abs(denom) > 1e-9 else 0.0
    intercept = (sum_y - slope * sum_x) / n

    # Model Predictions on held-out test steps
    model_predictions = []
    last_train_idx = x_train[-1]
    for h in range(1, test_steps + 1):
        future_x = last_train_idx + h
        pred = max(0.0, slope * future_x + intercept)
        model_predictions.append(pred)

    # 2. Naive Baseline Model:
    # Uses the single most recently observed difference in the train set:
    # baseline_delta = y_train[-1] - y_train[-2]
    # And projects: pred_t = y_train[-1] + h * baseline_delta
    naive_delta = y_train[-1] - y_train[-2]
    baseline_predictions = []
    for h in range(1, test_steps + 1):
        pred_base = max(0.0, y_train[-1] + h * naive_delta)
        baseline_predictions.append(pred_base)

    # 3. Calculate Real Mean Absolute Error (MAE)
    model_errors = [abs(act - pred) for act, pred in zip(test_data, model_predictions)]
    baseline_errors = [abs(act - pred) for act, pred in zip(test_data, baseline_predictions)]

    model_mae = round(sum(model_errors) / len(model_errors), 2)
    baseline_mae = round(sum(baseline_errors) / len(baseline_errors), 2)

    # Calculate Relative Improvement
    if baseline_mae > 0.0:
        improvement = round(((baseline_mae - model_mae) / baseline_mae) * 100.0, 1)
    else:
        improvement = 0.0

    return {
        "title": "Model evaluation — held-out simulated data",
        "model_mae": model_mae,
        "baseline_mae": baseline_mae,
        "relative_improvement_pct": improvement,
        "evaluation_samples": test_steps,
        "baseline_method": "Most recently observed single-step rate",
        "model_method": "Multi-sample ordinary linear trend regression",
        "timestamp": datetime.utcnow().isoformat(),
        "train_samples": train_steps,
        "test_samples": test_steps,
    }

# Compute standard evaluation run
DEFAULT_EVALUATION = generate_evaluation_dataset()
