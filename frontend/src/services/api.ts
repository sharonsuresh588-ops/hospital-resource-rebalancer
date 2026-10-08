import type {
  DashboardState,
  ReplayData,
  EvaluationData,
  NetworkRiskItem,
  AuditEvent,
  WhatIfScenarioResult,
} from '../types';

const API_BASE = (import.meta.env.VITE_API_BASE as string) || '';

export async function fetchState(): Promise<DashboardState> {
  const resp = await fetch(`${API_BASE}/api/state`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch state: ${resp.statusText}`);
  }
  return resp.json();
}

export async function startSimulation(): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/simulation/start`, { method: 'POST' });
  if (!resp.ok) {
    throw new Error(`Failed to start simulation: ${resp.statusText}`);
  }
}

export async function resetSimulation(): Promise<DashboardState> {
  const resp = await fetch(`${API_BASE}/api/simulation/reset`, { method: 'POST' });
  if (!resp.ok) {
    throw new Error(`Failed to reset simulation: ${resp.statusText}`);
  }
  const data = await resp.json();
  return data.state;
}

export async function injectSurge(): Promise<DashboardState> {
  const resp = await fetch(`${API_BASE}/api/simulation/surge`, { method: 'POST' });
  if (!resp.ok) {
    throw new Error(`Failed to inject surge: ${resp.statusText}`);
  }
  const data = await resp.json();
  return data.state;
}

export async function setSimulationScenario(scenarioName: string): Promise<DashboardState> {
  const resp = await fetch(`${API_BASE}/api/simulation/scenario`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_name: scenarioName }),
  });
  if (!resp.ok) {
    throw new Error(`Failed to set scenario: ${resp.statusText}`);
  }
  const data = await resp.json();
  return data.state;
}

export async function approveRecommendation(recId: string): Promise<DashboardState> {
  const resp = await fetch(`${API_BASE}/api/recommendations/${recId}/approve`, {
    method: 'POST',
  });
  if (!resp.ok) {
    const errorBody = await resp.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Approval failed with code ${resp.status}`);
  }
  const data = await resp.json();
  return data.state;
}

export async function fetchReplay(): Promise<ReplayData> {
  const resp = await fetch(`${API_BASE}/api/replay`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch replay: ${resp.statusText}`);
  }
  return resp.json();
}

export async function fetchEvaluation(): Promise<EvaluationData> {
  const resp = await fetch(`${API_BASE}/api/evaluation`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch evaluation: ${resp.statusText}`);
  }
  return resp.json();
}

export async function fetchNetworkRisk(): Promise<NetworkRiskItem[]> {
  const resp = await fetch(`${API_BASE}/api/network-risk`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch network risk: ${resp.statusText}`);
  }
  const data = await resp.json();
  return data.network_risk_ranking;
}

export async function fetchAuditTrail(): Promise<AuditEvent[]> {
  const resp = await fetch(`${API_BASE}/api/audit`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch audit trail: ${resp.statusText}`);
  }
  const data = await resp.json();
  return data.audit_trail;
}

export async function simulateWhatIfScenario(
  scenarioType: string,
  options?: {
    demand_multiplier?: number;
    excluded_donors?: string[];
    delay_minutes?: number;
    custom_quantity?: number;
  }
): Promise<WhatIfScenarioResult> {
  const resp = await fetch(`${API_BASE}/api/scenario/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      scenario_type: scenarioType,
      demand_multiplier: options?.demand_multiplier ?? 1.0,
      excluded_donors: options?.excluded_donors ?? [],
      delay_minutes: options?.delay_minutes ?? 0,
      custom_quantity: options?.custom_quantity,
    }),
  });
  if (!resp.ok) {
    throw new Error(`Failed to simulate scenario: ${resp.statusText}`);
  }
  return resp.json();
}

export async function executeCopilotAction(
  actionType: string,
  facts: Record<string, any>
): Promise<string> {
  const resp = await fetch(`${API_BASE}/api/copilot/action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action_type: actionType,
      facts,
    }),
  });
  if (!resp.ok) {
    throw new Error(`Failed to execute copilot action: ${resp.statusText}`);
  }
  const data = await resp.json();
  return data.content;
}
