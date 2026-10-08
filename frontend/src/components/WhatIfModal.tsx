import React, { useState, useEffect } from 'react';
import type { WhatIfScenarioResult } from '../types';
import { simulateWhatIfScenario } from '../services/api';
import { X, Sliders, ShieldCheck, AlertTriangle, ArrowRight } from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
} from 'recharts';

interface WhatIfModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const WhatIfModal: React.FC<WhatIfModalProps> = ({ isOpen, onClose }) => {
  const [selectedScenario, setSelectedScenario] = useState<string>('demand_plus_20');
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<WhatIfScenarioResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async (type: string) => {
    try {
      setLoading(true);
      setError(null);
      const res = await simulateWhatIfScenario(type);
      setResult(res);
    } catch (err: any) {
      setError(err?.message || 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      runSimulation(selectedScenario);
    }
  }, [isOpen, selectedScenario]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-wrap">
            <Sliders size={20} className="text-accent" />
            <h2 className="modal-title">WHAT-IF COUNTERFACTUAL SCENARIO SIMULATOR</h2>
          </div>
          <button className="btn-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="whatif-body">
          <div className="scenario-selector-bar">
            <span className="selector-label">SELECT HYPOTHETICAL STRESS SCENARIO:</span>
            <div className="scenario-buttons">
              <button
                className={`btn-scenario ${selectedScenario === 'demand_plus_10' ? 'active' : ''}`}
                onClick={() => setSelectedScenario('demand_plus_10')}
              >
                Demand +10%
              </button>
              <button
                className={`btn-scenario ${selectedScenario === 'demand_plus_20' ? 'active' : ''}`}
                onClick={() => setSelectedScenario('demand_plus_20')}
              >
                Demand +20%
              </button>
              <button
                className={`btn-scenario ${selectedScenario === 'demand_plus_30' ? 'active' : ''}`}
                onClick={() => setSelectedScenario('demand_plus_30')}
              >
                Demand +30%
              </button>
              <button
                className={`btn-scenario ${selectedScenario === 'donor_unavailable' ? 'active' : ''}`}
                onClick={() => setSelectedScenario('donor_unavailable')}
              >
                Donor H-B Offline
              </button>
              <button
                className={`btn-scenario ${selectedScenario === 'delayed_transfer' ? 'active' : ''}`}
                onClick={() => setSelectedScenario('delayed_transfer')}
              >
                Transit Delayed (+30m)
              </button>
            </div>
          </div>

          {loading && (
            <div className="whatif-loading">
              <span className="btn-spinner"></span> Computing deterministic scenario trajectories...
            </div>
          )}

          {error && <div className="whatif-error">{error}</div>}

          {result && !loading && (
            <div className="whatif-results">
              <div className="whatif-summary-banner">
                <p className="summary-text">{result.summary}</p>
              </div>

              <div className="whatif-comparison-grid">
                <div className="comparison-card card-without">
                  <div className="card-header-sub text-critical">
                    <AlertTriangle size={16} /> WITHOUT INTERVENTION
                  </div>
                  <div className="stat-line">
                    <span>Time to Shortage:</span>
                    <strong>{result.without_intervention.time_to_shortage_hours} hrs</strong>
                  </div>
                  <div className="stat-line">
                    <span>Total Shortage Duration:</span>
                    <strong>{result.without_intervention.shortage_duration_hours} hrs</strong>
                  </div>
                  <div className="stat-line">
                    <span>Minimum Stock Reached:</span>
                    <strong className="text-critical">{result.without_intervention.min_stock} cylinders</strong>
                  </div>
                </div>

                <div className="comparison-arrow">
                  <ArrowRight size={24} className="text-accent" />
                </div>

                <div className="comparison-card card-with">
                  <div className="card-header-sub text-safe">
                    <ShieldCheck size={16} /> WITH RECOMMENDED INTERVENTION
                  </div>
                  <div className="stat-line">
                    <span>Selected Donor:</span>
                    <strong>{result.recommended_donor}</strong>
                  </div>
                  <div className="stat-line">
                    <span>Transfer Quantity:</span>
                    <strong>{result.transfer_quantity} cylinders</strong>
                  </div>
                  <div className="stat-line">
                    <span>New Shortage Horizon:</span>
                    <strong className="text-safe">{result.with_intervention.time_to_shortage_hours} hrs</strong>
                  </div>
                  <div className="stat-line">
                    <span>Shortage-Hours Prevented:</span>
                    <strong className="text-accent">+{result.shortage_hours_prevented} hrs</strong>
                  </div>
                </div>
              </div>

              <div className="whatif-chart-wrap">
                <h4 className="chart-title">8-HOUR STRESS TRAJECTORY (HOSPITAL A)</h4>
                <div style={{ width: '100%', height: 260 }}>
                  <ResponsiveContainer>
                    <LineChart data={result.timeline} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#233554" />
                      <XAxis dataKey="hour" stroke="#8892b0" unit="h" />
                      <YAxis stroke="#8892b0" />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#0a192f', border: '1px solid #233554', borderRadius: 4 }}
                      />
                      <Legend />
                      <ReferenceLine
                        y={result.timeline[0]?.safety_threshold || 60}
                        stroke="#e53e3e"
                        strokeDasharray="4 4"
                        label={{ value: 'Safety Threshold', fill: '#e53e3e', position: 'top' }}
                      />
                      <Line
                        type="monotone"
                        dataKey="stock_without"
                        name="Without System"
                        stroke="#e53e3e"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="stock_with"
                        name="With System Intervention"
                        stroke="#38b2ac"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
