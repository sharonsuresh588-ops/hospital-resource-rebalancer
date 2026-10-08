import type { DashboardState, ReplayData, EvaluationData } from '../types';

const API_BASE = (import.meta.env.VITE_API_BASE as string) || ''; // Configurable for Render deployment, defaults to relative proxy in development

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
