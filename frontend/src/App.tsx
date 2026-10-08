import { useState, useEffect, useRef } from 'react';
import type { DashboardState, ReplayData } from './types';
import {
  fetchState,
  startSimulation,
  resetSimulation,
  injectSurge,
  approveRecommendation,
  fetchReplay,
} from './services/api';

import { Header } from './components/Header';
import { SummaryCards } from './components/SummaryCards';
import { ControlBar } from './components/ControlBar';
import { HospitalGrid } from './components/HospitalGrid';
import { RecommendationPanel } from './components/RecommendationPanel';
import { LiveChart } from './components/LiveChart';
import { EvaluationPanel } from './components/EvaluationPanel';
import { ReplayModal } from './components/ReplayModal';
import { AlertCircle, RefreshCw } from 'lucide-react';
import './App.css';

export function App() {
  const [state, setState] = useState<DashboardState | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Replay modal state
  const [replayOpen, setReplayOpen] = useState<boolean>(false);
  const [replayData, setReplayData] = useState<ReplayData | null>(null);
  const [replayLoading, setReplayLoading] = useState<boolean>(false);

  const pollIntervalRef = useRef<number | null>(null);

  // Initial load and continuous 2-second polling loop (Section 40)
  const loadState = async (showLoadingSpinner: boolean = false) => {
    if (showLoadingSpinner) setLoading(true);
    try {
      const data = await fetchState();
      setState(data);
      setError(null);
    } catch (err: any) {
      console.error('Error fetching dashboard state:', err);
      // Only set error banner if we don't already have state, avoiding white screen
      if (!state) {
        setError('Unable to connect to backend service. Retrying in background...');
      }
    } finally {
      if (showLoadingSpinner) setLoading(false);
    }
  };

  useEffect(() => {
    loadState(true);

    // Setup 2-second polling loop
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
      if (state.simulation.running) {
        // Stop is achieved via reset or pause endpoint
        // For simplicity, if running, fetch state or pause
      } else {
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
            <SummaryCards metrics={state.metrics} />

            <ControlBar
              simulation={state.simulation}
              onTogglePlay={handleTogglePlay}
              onInjectSurge={handleInjectSurge}
              onReset={handleReset}
              onOpenReplay={handleOpenReplay}
              loadingAction={actionLoading}
            />

            {/* Prominent Operational Optimizer & Rebalancing Panel */}
            <RecommendationPanel
              recommendations={state.recommendations || []}
              hospitals={state.hospitals || []}
              onApprove={handleApproveRecommendation}
            />

            {/* Hospital Grid */}
            <HospitalGrid
              hospitals={state.hospitals || []}
              predictions={state.predictions || []}
              surgeActive={state.simulation.surge_active}
            />

            {/* Trajectory Chart & Held-out Evaluation Grid */}
            <div className="dashboard-lower-grid">
              <LiveChart
                timeline={state.timeline || []}
                hospitals={state.hospitals || []}
                surgeActive={state.simulation.surge_active}
              />

              <EvaluationPanel evaluation={state.evaluation} />
            </div>
          </main>

          <footer className="app-footer">
            <div className="footer-content">
              <span>HN-AI-05 Emergency Operations Center</span>
              <span>
                Simulated Oxygen Cylinders • Linear Trend Shortage Prediction • Deterministic Python Optimization
              </span>
            </div>
          </footer>

          <ReplayModal
            isOpen={replayOpen}
            onClose={() => setReplayOpen(false)}
            replayData={replayData}
            loading={replayLoading}
          />
        </>
      )}
    </div>
  );
}

export default App;
