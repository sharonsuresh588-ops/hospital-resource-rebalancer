import React from 'react';
import type { SystemHealth, SimulationStatus } from '../types';
import { Activity, Database, Server, Flame, RefreshCw } from 'lucide-react';

interface HeaderProps {
  health: SystemHealth;
  simulation: SimulationStatus;
  onReset: () => void;
  resetting: boolean;
}

export const Header: React.FC<HeaderProps> = ({ health, simulation, onReset, resetting }) => {
  const dbStatus = health.database;
  const isDbAtlas = dbStatus.status_text === 'CONNECTED';

  return (
    <header className="app-header">
      <div className="header-brand">
        <div className="brand-logo-container">
          <Activity className="brand-icon" size={26} />
        </div>
        <div>
          <div className="brand-eyebrow">HACK NEXUS • EMERGENCY OPERATIONS</div>
          <h1 className="brand-title">Cross-Hospital Resource Rebalancer</h1>
        </div>
      </div>

      <div className="header-meta">
        <div className="sim-mode-badge">
          <span className="pulse-indicator"></span>
          SIMULATION MODE
          {simulation.surge_active && (
            <span className="surge-badge">
              <Flame size={12} /> SURGE ACTIVE
            </span>
          )}
        </div>

        <div className="health-badges">
          <div className="health-item" title="FastAPI Backend Health">
            <Server size={14} className="health-icon" />
            <span className="health-label">API</span>
            <span className="health-dot dot-healthy"></span>
          </div>

          <div 
            className="health-item" 
            title={`Database: ${dbStatus.provider} (${dbStatus.database})`}
          >
            <Database size={14} className="health-icon" />
            <span className="health-label">DATABASE</span>
            <span className={`status-pill ${isDbAtlas ? 'pill-connected' : 'pill-fallback'}`}>
              {isDbAtlas ? 'CONNECTED (Atlas)' : 'DEMO FALLBACK'}
            </span>
          </div>

          <div className="health-item" title={`Simulator Tick: ${simulation.tick}`}>
            <span className="health-label">TICK #{simulation.tick}</span>
            <span className={`health-dot ${simulation.running ? 'dot-running' : 'dot-idle'}`}></span>
          </div>

          <button 
            className="btn-quick-reset" 
            onClick={onReset} 
            disabled={resetting}
            title="Reset simulation to initial baseline"
          >
            <RefreshCw size={13} className={resetting ? 'spin' : ''} />
            Reset
          </button>
        </div>
      </div>
    </header>
  );
};
