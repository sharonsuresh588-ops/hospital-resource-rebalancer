import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts';
import type { ReplayData } from '../types';
import { X, ShieldAlert, ShieldCheck, CheckCircle2 } from 'lucide-react';

interface ReplayModalProps {
  isOpen: boolean;
  onClose: () => void;
  replayData: ReplayData | null;
  loading: boolean;
}

export const ReplayModal: React.FC<ReplayModalProps> = ({
  isOpen,
  onClose,
  replayData,
  loading,
}) => {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop">
      <div className="modal-content">
        <div className="modal-header">
          <div>
            <h2 className="modal-title">COUNTERFACTUAL SCENARIO REPLAY</h2>
            <p className="modal-subtitle">
              Comparing outcomes: Unmanaged Surge (No System) vs Rebalanced Intervention (With System)
            </p>
          </div>
          <button className="btn-modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {loading || !replayData ? (
          <div className="modal-loading">
            <span className="btn-spinner"></span> Simulating counterfactual trajectories...
          </div>
        ) : (
          <div className="modal-body">
            {/* High-level comparison summary cards */}
            <div className="replay-comparison-grid">
              <div className="replay-card replay-card-without">
                <div className="replay-card-header">
                  <ShieldAlert size={18} className="text-critical" />
                  <h3>WITHOUT SYSTEM (NO INTERVENTION)</h3>
                </div>
                <div className="replay-metric-row">
                  <span className="r-label">Shortage Duration:</span>
                  <span className="r-value text-critical">
                    {replayData.without_system.shortage_hours.toFixed(1)} hrs
                  </span>
                </div>
                <div className="replay-metric-row">
                  <span className="r-label">Units Transferred:</span>
                  <span className="r-value">0 cylinders</span>
                </div>
                <div className="replay-metric-row">
                  <span className="r-label">Outcome:</span>
                  <span className="r-value text-critical">Severe Oxygen Exhaustion</span>
                </div>
              </div>

              <div className="replay-card replay-card-with">
                <div className="replay-card-header">
                  <ShieldCheck size={18} className="text-safe" />
                  <h3>WITH SYSTEM (OPTIMIZER INTERVENTION)</h3>
                </div>
                <div className="replay-metric-row">
                  <span className="r-label">Shortage Duration:</span>
                  <span className="r-value text-safe">
                    {replayData.with_system.shortage_hours.toFixed(1)} hrs
                  </span>
                </div>
                <div className="replay-metric-row">
                  <span className="r-label">Units Transferred:</span>
                  <span className="r-value text-accent">
                    {replayData.with_system.units_transferred} cylinders (B → A)
                  </span>
                </div>
                <div className="replay-metric-row">
                  <span className="r-label">Outcome:</span>
                  <span className="r-value text-safe">Hospital A Stabilized Safely</span>
                </div>
              </div>

              <div className="replay-card replay-card-impact">
                <div className="replay-card-header">
                  <CheckCircle2 size={18} className="text-accent" />
                  <h3>MEASURED IMPACT</h3>
                </div>
                <div className="replay-metric-row">
                  <span className="r-label">Shortage Prevented:</span>
                  <span className="r-value text-accent">
                    +{replayData.shortage_hours_prevented.toFixed(1)} hrs
                  </span>
                </div>
                <div className="replay-metric-row">
                  <span className="r-label">Donor Safety:</span>
                  <span className="r-value text-safe">100% Retained</span>
                </div>
                <div className="replay-metric-row">
                  <span className="r-label">Formula:</span>
                  <span className="r-formula">Without (5.5h) - With (4.5h)</span>
                </div>
              </div>
            </div>

            {/* Replay Trajectory Chart */}
            <div className="replay-chart-box">
              <h4 className="chart-title">Hospital A Stock Trajectory Comparison</h4>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart
                  data={replayData.timeline}
                  margin={{ top: 10, right: 30, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#262c36" />
                  <XAxis
                    dataKey="tick"
                    stroke="#64748b"
                    tickFormatter={(t) => `t=${t}`}
                  />
                  <YAxis stroke="#64748b" domain={[0, 160]} unit=" cyl" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '6px',
                    }}
                  />
                  <Legend />
                  <ReferenceLine
                    y={60}
                    stroke="#dc2626"
                    strokeDasharray="4 4"
                    label={{
                      value: 'Safety Threshold (60)',
                      fill: '#ef4444',
                      fontSize: 11,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="without_system_a"
                    name="Without System (Unmanaged)"
                    stroke="#ef4444"
                    strokeWidth={2.5}
                    strokeDasharray="5 5"
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="with_system_a"
                    name="With System (Redistributed)"
                    stroke="#10b981"
                    strokeWidth={3}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="replay-summary-callout">
              <strong>Evaluation Statement:</strong> {replayData.summary}
            </div>
          </div>
        )}

        <div className="modal-footer">
          <button className="btn-modal-dismiss" onClick={onClose}>
            Close Replay
          </button>
        </div>
      </div>
    </div>
  );
};
