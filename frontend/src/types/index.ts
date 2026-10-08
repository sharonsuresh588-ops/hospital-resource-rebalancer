export interface Hospital {
  id: string;
  name: string;
  lat: number;
  lng: number;
  capacity: number;
  safety_threshold: number;
  current_stock: number;
  base_rate?: number;
}

export interface Prediction {
  hospital_id: string;
  timestamp: string;
  stock: number;
  depletion_rate: number;
  time_to_shortage_hours: number | null;
  confidence: number;
  status: 'SAFE' | 'WARNING' | 'CRITICAL';
}

export interface Recommendation {
  id: string;
  from_hospital: string;
  to_hospital: string;
  quantity: number;
  dispatch_deadline_minutes: number;
  status: 'pending' | 'approved' | 'rejected';
  justification: string;
  created_at: string;
  donor_safety_margin_after?: number;
  approved_at?: string;
}

export interface SimulationStatus {
  running: boolean;
  surge_active: boolean;
  tick: number;
  tick_interval_seconds: number;
}

export interface Metrics {
  shortage_hours_prevented: number;
  units_transferred: number;
  transfers_completed: number;
  hospitals_monitored: number;
  critical_shortages: number;
  active_recommendations: number;
}

export interface DatabaseStatus {
  connected: boolean;
  status_text: string;
  provider: string;
  database: string;
}

export interface SystemHealth {
  api: string;
  database: DatabaseStatus;
  simulator: string;
}

export interface EvaluationData {
  title: string;
  model_mae: number;
  baseline_mae: number;
  relative_improvement_pct: number;
  evaluation_samples: number;
  baseline_method: string;
  model_method: string;
  timestamp: string;
}

export interface TimelinePoint {
  tick: number;
  [hospitalId: string]: number;
}

export interface DashboardState {
  simulation: SimulationStatus;
  hospitals: Hospital[];
  predictions: Prediction[];
  recommendations: Recommendation[];
  evaluation: EvaluationData;
  metrics: Metrics;
  system_health: SystemHealth;
  timeline: TimelinePoint[];
}

export interface ReplayTimelinePoint {
  tick: number;
  without_system_a: number;
  with_system_a: number;
  safety_threshold: number;
  transfer_applied: boolean;
}

export interface ReplayData {
  without_system: {
    shortage_hours: number;
    units_transferred: number;
    critical_events: number;
  };
  with_system: {
    shortage_hours: number;
    units_transferred: number;
    critical_events: number;
  };
  shortage_hours_prevented: number;
  units_transferred: number;
  timeline: ReplayTimelinePoint[];
  summary: string;
}
