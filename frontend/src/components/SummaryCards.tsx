import React from 'react';
import type { Metrics } from '../types';
import { AlertTriangle, GitPullRequest, ShieldCheck, Flame, Compass } from 'lucide-react';

interface SummaryCardsProps {
  metrics: Metrics;
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({ metrics }) => {
  const isCritical = metrics.critical_shortages > 0;
  const hasRecs = metrics.active_recommendations > 0;
  const hospitalsAtRisk = metrics.hospitals_at_risk ?? (isCritical ? 1 : 0);
  const safeOpportunities = metrics.safe_transfer_opportunities ?? (hasRecs ? 1 : 0);

  return (
    <div className="summary-cards-grid">
      <div className={`summary-card ${isCritical ? 'card-critical-alert' : ''}`}>
        <div className="card-top">
          <span className="card-title">CRITICAL HOSPITALS</span>
          <div className={`card-icon-wrap ${isCritical ? 'icon-critical' : 'icon-safe'}`}>
            <AlertTriangle size={18} />
          </div>
        </div>
        <div className={`card-value ${isCritical ? 'text-critical' : 'text-safe'}`}>
          {metrics.critical_shortages}
        </div>
        <div className="card-footnote">
          {isCritical ? 'Immediate redistribution required' : 'All facilities within threshold'}
        </div>
      </div>

      <div className={`summary-card ${hasRecs ? 'card-warning-alert' : ''}`}>
        <div className="card-top">
          <span className="card-title">ACTIVE RECOMMENDATIONS</span>
          <div className={`card-icon-wrap ${hasRecs ? 'icon-warning' : 'icon-neutral'}`}>
            <GitPullRequest size={18} />
          </div>
        </div>
        <div className={`card-value ${hasRecs ? 'text-amber' : ''}`}>
          {metrics.active_recommendations}
        </div>
        <div className="card-footnote">
          {hasRecs ? 'Awaiting human coordinator signoff' : 'Zero pending dispatches'}
        </div>
      </div>

      <div className="summary-card">
        <div className="card-top">
          <span className="card-title">SAFE TRANSFER OPPORTUNITIES</span>
          <div className="card-icon-wrap icon-neutral">
            <Compass size={18} />
          </div>
        </div>
        <div className="card-value">{safeOpportunities}</div>
        <div className="card-footnote">Feasible donors satisfying 4h reserve</div>
      </div>

      <div className={`summary-card ${hospitalsAtRisk > 0 ? 'card-warning-alert' : ''}`}>
        <div className="card-top">
          <span className="card-title">HOSPITALS AT RISK</span>
          <div className={`card-icon-wrap ${hospitalsAtRisk > 0 ? 'icon-warning' : 'icon-safe'}`}>
            <Flame size={18} />
          </div>
        </div>
        <div className={`card-value ${hospitalsAtRisk > 0 ? 'text-amber' : 'text-safe'}`}>
          {hospitalsAtRisk}
        </div>
        <div className="card-footnote">Facilities under Watch, Warning, or Critical</div>
      </div>

      <div className="summary-card card-accent">
        <div className="card-top">
          <span className="card-title">SHORTAGE-HOURS PREVENTED</span>
          <div className="card-icon-wrap icon-success">
            <ShieldCheck size={18} />
          </div>
        </div>
        <div className="card-value text-accent">
          {metrics.shortage_hours_prevented.toFixed(1)} <span className="value-unit">hrs</span>
        </div>
        <div className="card-footnote">
          {metrics.units_transferred} cylinders transferred safely
        </div>
      </div>
    </div>
  );
};
