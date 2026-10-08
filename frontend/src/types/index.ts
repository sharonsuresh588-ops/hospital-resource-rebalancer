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

export interface CandidateDonor {
  hospital_id: string;
  hospital_name: string;
  current_stock: number;
  safety_threshold: number;
  transfer_quantity: number;
  stock_after_transfer: number;
  projected_4h_stock: number;
  distance_km: number;
  travel_time_minutes: number;
  safe_surplus: number;
  passed_all_constraints: boolean;
  failed_constraints?: string[];
  donor_score: number;
  rejection_reason?: string | null;
}

export interface Recommendation {
  id: string;
  from_hospital: string;
  to_hospital: string;
  quantity: number;
  dispatch_deadline_minutes: number;
  status: 'pending' | 'approved' | 'rejected' | 'no_safe_transfer';
  justification: string;
  created_at: string;
  donor_safety_margin_after?: number;
  approved_at?: string;
  donor_score?: number;
  distance_km?: number;
  estimated_transit_minutes?: number;
  donor_projected_4h_stock?: number;
  winning_reason?: string;
  candidate_breakdown?: CandidateDonor[];
  is_safe_transfer?: boolean;
  escalation_required?: boolean;
  escalation_message?: string;
}

export interface SimulationStatus {
  running: boolean;
  surge_active: boolean;
  tick: number;
  tick_interval_seconds: number;
  scenario_name?: string;
}

export interface Metrics {
  shortage_hours_prevented: number;
  units_transferred: number;
  transfers_completed: number;
  hospitals_monitored: number;
  critical_shortages: number;
  active_recommendations: number;
  safe_transfer_opportunities?: number;
  hospitals_at_risk?: number;
}

export interface DatabaseStatus {
  connected: boolean;
  status_text: string;
  provider: string;
  database: string;
  collections?: Record<string, number>;
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
  held_out_steps?: number;
  intervention_success_rate?: number;
  shortage_hours_prevented?: number;
  donor_safety_violations?: number;
  secondary_shortages_caused?: number;
  no_safe_donor_detection_accuracy?: number;
  replay_consistency?: number;
}

export interface TimelinePoint {
  tick: number;
  [hospitalId: string]: number;
}

export interface NetworkRiskItem {
  hospital_id: string;
  hospital_name: string;
  current_stock: number;
  safety_threshold: number;
  depletion_rate: number;
  time_to_shortage_hours: number | null;
  projected_min_stock: number;
  confidence: number;
  risk_score: number;
  risk_level: 'NETWORK EMERGENCY' | 'CRITICAL' | 'WARNING' | 'WATCH' | 'NORMAL';
  rank: number;
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  event_type: string;
  [key: string]: any;
}

export interface DashboardState {
  simulation: SimulationStatus;
  hospitals: Hospital[];
  predictions: Prediction[];
  recommendations: Recommendation[];
  network_risk_ranking?: NetworkRiskItem[];
  audit_trail?: AuditEvent[];
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
    minimum_stock?: number;
    time_to_shortage?: number;
    timeline?: any[];
  };
  with_system: {
    shortage_hours: number;
    units_transferred: number;
    critical_events: number;
    minimum_stock?: number;
    donor_minimum_stock?: number;
    donor_safety_maintained?: boolean;
    recipient_recovery_time_hours?: number;
    secondary_shortages_created?: number;
    timeline?: any[];
  };
  shortage_hours_prevented: number;
  units_transferred: number;
  donor_safety_maintained?: boolean;
  secondary_shortages_created?: number;
  hospitals_affected?: string[];
  timeline: ReplayTimelinePoint[];
  summary: string;
}

export interface WhatIfScenarioResult {
  scenario_type: string;
  demand_multiplier: number;
  excluded_donors: string[];
  delay_minutes: number;
  transfer_feasible: boolean;
  recommended_donor: string;
  transfer_quantity: number;
  without_intervention: {
    initial_stock: number;
    depletion_rate: number;
    time_to_shortage_hours: number;
    shortage_duration_hours: number;
    min_stock: number;
  };
  with_intervention: {
    initial_stock: number;
    quantity_transferred: number;
    time_to_shortage_hours: number;
    shortage_duration_hours: number;
    min_stock: number;
    donor_safety_maintained: boolean;
  };
  shortage_hours_prevented: number;
  timeline: Array<{
    hour: number;
    stock_without: number;
    stock_with: number;
    safety_threshold: number;
  }>;
  summary: string;
}
