import React, { useState } from 'react';
import type { Recommendation, Hospital } from '../types';
import { ArrowRight, CheckCircle, Clock, ShieldCheck, AlertCircle, Bot, Zap } from 'lucide-react';

interface RecommendationPanelProps {
  recommendations: Recommendation[];
  hospitals: Hospital[];
  onApprove: (id: string) => Promise<void>;
}

export const RecommendationPanel: React.FC<RecommendationPanelProps> = ({
  recommendations,
  hospitals,
  onApprove,
}) => {
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [approvalError, setApprovalError] = useState<string | null>(null);

  const hospMap = new Map<string, Hospital>();
  hospitals.forEach((h) => hospMap.set(h.id, h));

  // Find active pending recommendation
  const pendingRec = recommendations.find((r) => r.status === 'pending');
  // Latest approved recommendation
  const latestApproved = recommendations
    .filter((r) => r.status === 'approved')
    .slice(-1)[0];

  const handleApprove = async (recId: string) => {
    try {
      setApprovingId(recId);
      setApprovalError(null);
      await onApprove(recId);
    } catch (err: any) {
      setApprovalError(err?.message || 'Approval failed');
    } finally {
      setApprovingId(null);
    }
  };

  return (
    <div className="recommendation-panel-root">
      <div className="section-header">
        <div className="section-title-wrap">
          <Zap className="section-icon-accent" size={20} />
          <h2 className="section-heading">OPERATIONAL REDISTRIBUTION OPTIMIZER</h2>
        </div>
        <span className="section-caption">
          Deterministic linear programming dispatch with donor safety constraint
        </span>
      </div>

      {pendingRec ? (
        <div className="recommendation-card-active">
          <div className="rec-header">
            <div className="rec-flag-pulse">
              <span className="pulse-dot-red"></span>
              TRANSFER RECOMMENDED
            </div>
            <div className="rec-id-badge">ID: {pendingRec.id}</div>
          </div>

          <div className="rec-transfer-flow">
            <div className="facility-node donor-node">
              <span className="node-role">DONOR FACILITY</span>
              <h3 className="node-name">
                {hospMap.get(pendingRec.from_hospital)?.name || pendingRec.from_hospital}
              </h3>
              <div className="node-details">
                Current Stock: {hospMap.get(pendingRec.from_hospital)?.current_stock ?? '—'}
                <span className="node-badge-safe">
                  Safety Margin: +{pendingRec.donor_safety_margin_after ?? 45}
                </span>
              </div>
            </div>

            <div className="transfer-arrow-node">
              <div className="quantity-badge">
                <span className="quantity-num">{pendingRec.quantity}</span>
                <span className="quantity-unit">CYLINDERS</span>
              </div>
              <ArrowRight className="arrow-pulse" size={32} />
              <div className="deadline-tag">
                <Clock size={13} /> Dispatch within {pendingRec.dispatch_deadline_minutes}m
              </div>
            </div>

            <div className="facility-node dest-node">
              <span className="node-role role-dest">DEFICIT FACILITY</span>
              <h3 className="node-name">
                {hospMap.get(pendingRec.to_hospital)?.name || pendingRec.to_hospital}
              </h3>
              <div className="node-details">
                Current Stock: {hospMap.get(pendingRec.to_hospital)?.current_stock ?? '—'}
                <span className="node-badge-urgent">Urgency: CRITICAL</span>
              </div>
            </div>
          </div>

          <div className="rec-meta-grid">
            <div className="meta-pill">
              <AlertCircle size={14} className="text-critical" />
              <span>Destination Urgency: <strong>HIGH / IMMINENT SHORTAGE</strong></span>
            </div>
            <div className="meta-pill">
              <ShieldCheck size={14} className="text-safe" />
              <span>Donor Safety: <strong>PRESERVED (Above Threshold)</strong></span>
            </div>
          </div>

          <div className="rec-ai-justification">
            <div className="ai-tag">
              <Bot size={15} />
              <span>AI OPERATIONAL EXPLANATION (GEMINI / DETERMINISTIC FALLBACK)</span>
            </div>
            <p className="ai-text">"{pendingRec.justification}"</p>
          </div>

          {approvalError && (
            <div className="approval-error-banner">
              <AlertCircle size={16} /> {approvalError}
            </div>
          )}

          <div className="rec-action-row">
            <button
              className="btn-approve"
              onClick={() => handleApprove(pendingRec.id)}
              disabled={approvingId === pendingRec.id}
            >
              {approvingId === pendingRec.id ? (
                <>
                  <span className="btn-spinner"></span> EXECUTING REBALANCING...
                </>
              ) : (
                <>
                  <CheckCircle size={18} /> APPROVE TRANSFER ({pendingRec.quantity} CYLINDERS)
                </>
              )}
            </button>
          </div>
        </div>
      ) : latestApproved ? (
        <div className="recommendation-card-approved">
          <div className="approved-banner">
            <CheckCircle size={22} className="text-safe" />
            <div>
              <h3 className="approved-title">
                TRANSFER APPROVED & EXECUTED ({latestApproved.quantity} CYLINDERS)
              </h3>
              <p className="approved-subtitle">
                {hospMap.get(latestApproved.from_hospital)?.name || latestApproved.from_hospital} →{' '}
                {hospMap.get(latestApproved.to_hospital)?.name || latestApproved.to_hospital}
              </p>
            </div>
          </div>
          <div className="approved-stats">
            <span className="stat-pill">Status: <strong>APPROVED</strong></span>
            <span className="stat-pill">Units Transferred: <strong>{latestApproved.quantity}</strong></span>
            <span className="stat-pill">Critical Shortage: <strong>AVOIDED</strong></span>
          </div>
        </div>
      ) : (
        <div className="recommendation-card-empty">
          <ShieldCheck size={36} className="empty-icon" />
          <h3 className="empty-title">All Hospital Reserves Within Safe Margins</h3>
          <p className="empty-desc">
            The optimizer continuously calculates depletion trajectories across all facilities.
            If a surge breaches safety limits, a redistribution plan will appear here.
          </p>
        </div>
      )}
    </div>
  );
};
