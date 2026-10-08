import React from 'react';
import type { EvaluationData } from '../types';
import { Award, CheckCircle, Database } from 'lucide-react';

interface EvaluationPanelProps {
  evaluation: EvaluationData;
}

export const EvaluationPanel: React.FC<EvaluationPanelProps> = ({ evaluation }) => {
  const isPositive = evaluation.relative_improvement_pct >= 0;

  return (
    <div className="evaluation-panel-section">
      <div className="section-header">
        <div className="section-title-wrap">
          <Award size={20} className="section-icon-accent" />
          <h2 className="section-heading">MODEL EVALUATION</h2>
        </div>
        <span className="section-caption">Held-out simulated data (non-fabricated benchmark)</span>
      </div>

      <div className="eval-metrics-grid">
        <div className="eval-metric-card">
          <span className="eval-metric-label">MODEL MAE</span>
          <div className="eval-metric-val text-accent">
            {evaluation.model_mae.toFixed(1)}
          </div>
          <span className="eval-metric-note">
            Multi-sample linear regression (filters observation noise)
          </span>
        </div>

        <div className="eval-metric-card">
          <span className="eval-metric-label">BASELINE MAE</span>
          <div className="eval-metric-val">
            {evaluation.baseline_mae.toFixed(1)}
          </div>
          <span className="eval-metric-note">
            Naive baseline (most recently observed step rate)
          </span>
        </div>

        <div className="eval-metric-card">
          <span className="eval-metric-label">RELATIVE IMPROVEMENT</span>
          <div className={`eval-metric-val ${isPositive ? 'text-safe' : 'text-amber'}`}>
            {isPositive ? `+${evaluation.relative_improvement_pct.toFixed(1)}%` : `${evaluation.relative_improvement_pct.toFixed(1)}%`}
          </div>
          <span className="eval-metric-note">
            Error reduction vs naive delta on held-out test data
          </span>
        </div>
      </div>

      <div className="eval-footer-info">
        <div className="eval-info-item">
          <Database size={13} />
          <span>Evaluation samples: {evaluation.evaluation_samples} held-out steps</span>
        </div>
        <div className="eval-info-item">
          <CheckCircle size={13} />
          <span>Evaluation protocol: Out-of-sample forward rolling error</span>
        </div>
      </div>
    </div>
  );
};
