import { useState, useEffect, useRef } from 'react';
import type { DashboardState, ReplayData } from './types';
import {
  fetchState,
  startSimulation,
  resetSimulation,
  injectSurge,
  approveRecommendation,
  fetchReplay,
  setSimulationScenario,
} from './services/api';

import { Header } from './components/Header';
import { SummaryCards } from './components/SummaryCards';
import { ControlBar } from './components/ControlBar';
import { NetworkRiskPanel } from './components/NetworkRiskPanel';
import { HospitalGrid } from './components/HospitalGrid';
import { RecommendationPanel } from './components/RecommendationPanel';
import { LiveChart } from './components/LiveChart';
import { EvaluationPanel } from './components/EvaluationPanel';
import { DecisionAuditPanel } from './components/DecisionAuditPanel';
import { ReplayModal } from './components/ReplayModal';
import { WhatIfModal } from './components/WhatIfModal';
import { CopilotModal } from './components/CopilotModal';
import { AlertCircle, RefreshCw } from 'lucide-react';
import './App.css';

export function App() {
  const [state, setState] = useState<DashboardState | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Modals state
  const [replayOpen, setReplayOpen] = useState<boolean>(false);
  const [replayData, setReplayData] = useState<ReplayData | null>(null);
  const [replayLoading, setReplayLoading] = useState<boolean>(false);

  const [whatIfOpen, setWhatIfOpen] = useState<boolean>(false);
  const [copilotOpen, setCopilotOpen] = useState<boolean>(false);

  const pollIntervalRef = useRef<number | null>(null);

  // Polling loop (2-second interval)
  const loadState = async (showLoadingSpinner: boolean = false) => {
    if (showLoadingSpinner) setLoading(true);
    try {
      const data = await fetchState();
      setState(data);
      setError(null);
    } catch (err: any) {
      console.error('Error fetching dashboard state:', err);
      if (!state) {
        setError('Unable to connect to backend service. Retrying in background...');
      }
    } finally {
      if (showLoadingSpinner) setLoading(false);
    }
  };

  useEffect(() => {
    loadState(true);

    pollIntervalRef.current = window.setInterval(() => {
      loadState(false);
    }, 2000);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const handleTogglePlay = async () => {
    if (!state) return;
    setActionLoading('play');
    try {
      if (!state.simulation.running) {
        await startSimulation();
      }
      await loadState();
    } catch (err: any) {
      console.error('Play toggle failed:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleInjectSurge = async () => {
    setActionLoading('surge');
    try {
      const updated = await injectSurge();
      setState(updated);
    } catch (err: any) {
      console.error('Surge injection failed:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReset = async () => {
    setActionLoading('reset');
    try {
      const resetState = await resetSimulation();
      setState(resetState);
      setError(null);
    } catch (err: any) {
      console.error('Reset failed:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleSelectScenario = async (scenarioName: string) => {
    setActionLoading('scenario');
    try {
      const updated = await setSimulationScenario(scenarioName);
      setState(updated);
    } catch (err: any) {
      console.error('Scenario selection failed:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleApproveRecommendation = async (recId: string) => {
    setActionLoading('approve');
    try {
      const updated = await approveRecommendation(recId);
      setState(updated);
    } catch (err: any) {
      throw err;
    } finally {
      setActionLoading(null);
    }
  };

  const handleOpenReplay = async () => {
    setReplayOpen(true);
    setReplayLoading(true);
    try {
      const data = await fetchReplay();
      setReplayData(data);
    } catch (err: any) {
      console.error('Failed to load replay data:', err);
    } finally {
      setReplayLoading(false);
    }
  };

  if (loading && !state) {
    return (
      <div className="app-loading-screen">
        <div className="loading-card">
          <RefreshCw className="spin text-accent" size={32} />
          <h2>Initializing Emergency Control System...</h2>
          <p>Connecting to hospital telemetry network and simulator.</p>
        </div>
      </div>
    );
  }

  const activeRec = state?.recommendations?.find((r) => r.status === 'pending') || null;

  return (
    <div className="app-container">
      {state && (
        <>
          <Header
            health={state.system_health}
            simulation={state.simulation}
            onReset={handleReset}
            resetting={actionLoading === 'reset'}
          />

          {error && (
            <div className="connection-error-banner">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <main className="dashboard-content">
            {/* Feature 10: Executive Command Center Overview */}
            <SummaryCards metrics={state.metrics} />

            {/* Feature 11: Control Bar with Presets */}
            <ControlBar
              simulation={state.simulation}
              onTogglePlay={handleTogglePlay}
              onInjectSurge={handleInjectSurge}
              onReset={handleReset}
              onOpenReplay={handleOpenReplay}
              onOpenWhatIf={() => setWhatIfOpen(true)}
              onOpenCopilot={() => setCopilotOpen(true)}
              onSelectScenario={handleSelectScenario}
              loadingAction={actionLoading}
            />

            {/* Feature 4: Network-Wide Risk Priority */}
            {state.network_risk_ranking && (
              <NetworkRiskPanel ranking={state.network_risk_ranking} />
            )}

            {/* Features 1, 2, 3, 5: Feasibility Dispatch Optimizer */}
            <RecommendationPanel
              recommendations={state.recommendations || []}
              hospitals={state.hospitals || []}
              onApprove={handleApproveRecommendation}
              onOpenWhatIf={() => setWhatIfOpen(true)}
              onOpenCopilot={() => setCopilotOpen(true)}
            />

            {/* Monitored Facilities Grid */}
            <HospitalGrid
              hospitals={state.hospitals || []}
              predictions={state.predictions || []}
              surgeActive={state.simulation.surge_active}
            />

            {/* Real-time Trajectory Chart & Robust Evaluation */}
            <div className="dashboard-lower-grid">
              <LiveChart
                timeline={state.timeline || []}
                hospitals={state.hospitals || []}
                surgeActive={state.simulation.surge_active}
              />

              <EvaluationPanel evaluation={state.evaluation} />
            </div>

            {/* Feature 8: Decision Audit Trail */}
            {state.audit_trail && (
              <DecisionAuditPanel auditTrail={state.audit_trail} />
            )}
          </main>

          <footer className="app-footer">
            <div className="footer-content">
              <span>HN-AI-05 Emergency Operations Center</span>
              <span>
                Deterministic Python Optimizer • Feasibility-Aware Donor Scoring • MongoDB Atlas Persisted • Gemini Copilot
              </span>
            </div>
          </footer>

          {/* Feature 7: Advanced Counterfactual Replay Modal */}
          <ReplayModal
            isOpen={replayOpen}
            onClose={() => setReplayOpen(false)}
            replayData={replayData}
            loading={replayLoading}
          />

          {/* Feature 6: What-If Scenario Modal */}
          <WhatIfModal
            isOpen={whatIfOpen}
            onClose={() => setWhatIfOpen(false)}
          />

          {/* Feature 9: Gemini Operations Copilot Modal */}
          <CopilotModal
            isOpen={copilotOpen}
            onClose={() => setCopilotOpen(false)}
            recommendation={activeRec}
            hospitals={state.hospitals || []}
          />
        </>
      )}
    </div>
  );
}

export default App;
