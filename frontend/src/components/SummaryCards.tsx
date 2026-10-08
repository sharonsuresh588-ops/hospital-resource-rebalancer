import React from 'react';
import type { Metrics } from '../types';
import { Building2, AlertTriangle, GitPullRequest, ShieldCheck } from 'lucide-react';

interface SummaryCardsProps {
  metrics: Metrics;
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({ metrics }) => {
  const isCritical = metrics.critical_shortages > 0;
  const hasRecs = metrics.active_recommendations > 0;

  return (
    <div className="summary-cards-grid">
      <div className="summary-card">
        <div className="card-top">
          <span className="card-title">HOSPITALS MONITORED</span>
          <div className="card-icon-wrap icon-neutral">
            <Building2 size={18} />
          </div>
        </div>
        <div className="card-value">{metrics.hospitals_monitored || 6}</div>
        <div className="card-footnote">Continuously tracking oxygen stock</div>
      </div>

      <div className={`summary-card ${isCritical ? 'card-critical-alert' : ''}`}>
        <div className="card-top">
          <span className="card-title">CRITICAL SHORTAGES</span>
          <div className={`card-icon-wrap ${isCritical ? 'icon-critical' : 'icon-safe'}`}>
            <AlertTriangle size={18} />
          </div>
        </div>
        <div className={`card-value ${isCritical ? 'text-critical' : 'text-safe'}`}>
          {metrics.critical_shortages}
        </div>
        <div className="card-footnote">
          {isCritical ? 'Immediate intervention needed' : 'All facilities above threshold'}
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
          {hasRecs ? 'Awaiting human coordinator signoff' : 'No transfers pending'}
        </div>
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
