import React from 'react';
import type { AuditEvent } from '../types';
import { History, ShieldCheck, CheckCircle2, AlertOctagon, Flame, RotateCcw } from 'lucide-react';

interface DecisionAuditPanelProps {
  auditTrail: AuditEvent[];
}

export const DecisionAuditPanel: React.FC<DecisionAuditPanelProps> = ({ auditTrail }) => {
  if (!auditTrail || auditTrail.length === 0) return null;

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'RECOMMENDATION_ISSUED':
        return <ShieldCheck size={14} className="text-accent" />;
      case 'TRANSFER_APPROVED':
        return <CheckCircle2 size={14} className="text-safe" />;
      case 'NO_SAFE_TRANSFER_DETECTED':
        return <AlertOctagon size={14} className="text-critical" />;
      case 'SURGE_INJECTED':
        return <Flame size={14} className="text-critical" />;
      default:
        return <RotateCcw size={14} className="text-neutral" />;
    }
  };

  const formatTime = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return iso;
    }
  };

  return (
    <div className="audit-panel-root">
      <div className="section-header">
        <div className="section-title-wrap">
          <History className="section-icon-accent" size={20} />
          <h2 className="section-heading">DECISION AUDIT TRAIL</h2>
        </div>
        <span className="section-caption">
          Immutable event log tracking optimizer decisions, human approvals, and averted shortage metrics
        </span>
      </div>

      <div className="audit-timeline-container">
        {auditTrail.map((event) => (
          <div key={event.id} className="audit-event-card">
            <div className="event-meta">
              <span className="event-time">{formatTime(event.timestamp)}</span>
              <span className="event-type-badge">
                {getEventIcon(event.event_type)} {event.event_type.replace(/_/g, ' ')}
              </span>
              <span className="event-id">{event.id}</span>
            </div>

            <div className="event-details">
              {event.event_type === 'RECOMMENDATION_ISSUED' && (
                <p>
                  Recommended <strong>{event.quantity} cylinders</strong> from <strong>{event.donor_name}</strong> to{' '}
                  <strong>{event.recipient_name}</strong> (Donor Score: {event.donor_score}). Dispatch deadline:{' '}
                  {event.dispatch_deadline_minutes}m.
                </p>
              )}

              {event.event_type === 'TRANSFER_APPROVED' && (
                <p>
                  Human coordinator approved transfer of <strong>{event.quantity} units</strong> ({event.from_hospital} →{' '}
                  {event.to_hospital}). Stock synchronized across facilities.
                </p>
              )}

              {event.event_type === 'NO_SAFE_TRANSFER_DETECTED' && (
                <p className="text-critical">
                  Optimizer safely refused transfer for <strong>{event.recipient_name}</strong>: all potential donors
                  breached safety or transit limits. External mutual aid escalated.
                </p>
              )}

              {event.event_type === 'SURGE_INJECTED' && (
                <p>Demand surge injected into {event.target_hospital} at tick {event.tick}.</p>
              )}

              {event.event_type === 'SIMULATION_RESET' && (
                <p>{event.message || 'Simulator reset to deterministic baseline state.'}</p>
              )}

              {event.event_type === 'SCENARIO_SWITCHED' && (
                <p>Scenario switched to <strong>{event.scenario}</strong>.</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
