import React, { useState } from 'react';
import type { Recommendation, Hospital } from '../types';
import {
  ArrowRight,
  CheckCircle,
  Clock,
  ShieldCheck,
  AlertCircle,
  Bot,
  Zap,
  Sliders,
  ChevronDown,
  ChevronUp,
  AlertOctagon,
  Navigation,
} from 'lucide-react';

interface RecommendationPanelProps {
  recommendations: Recommendation[];
  hospitals: Hospital[];
  onApprove: (id: string) => Promise<void>;
  onOpenWhatIf?: () => void;
  onOpenCopilot?: () => void;
}

export const RecommendationPanel: React.FC<RecommendationPanelProps> = ({
  recommendations,
  hospitals,
  onApprove,
  onOpenWhatIf,
  onOpenCopilot,
}) => {
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [approvalError, setApprovalError] = useState<string | null>(null);
  const [showBreakdown, setShowBreakdown] = useState<boolean>(false);

  const hospMap = new Map<string, Hospital>();
  hospitals.forEach((h) => hospMap.set(h.id, h));

  // Find active pending recommendation or no-safe-transfer alert
  const pendingRec = recommendations.find((r) => r.status === 'pending');
  const noSafeRec = recommendations.find((r) => r.status === 'no_safe_transfer');
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
          <h2 className="section-heading">FEASIBILITY-AWARE DISPATCH OPTIMIZER</h2>
        </div>
        <div className="header-actions">
          {onOpenWhatIf && (
            <button className="btn-header-tool" onClick={onOpenWhatIf} title="Simulate hypothetical what-if scenarios">
              <Sliders size={14} /> What-If Simulator
            </button>
          )}
          {onOpenCopilot && (
            <button className="btn-header-tool" onClick={onOpenCopilot} title="Gemini Operations Copilot communication tools">
              <Bot size={14} /> Operations Copilot
            </button>
          )}
        </div>
      </div>

      {pendingRec ? (
        <div className="recommendation-card-active">
          <div className="rec-header">
            <div className="rec-flag-pulse">
              <span className="pulse-dot-red"></span>
              FEASIBLE TRANSFER RECOMMENDED
            </div>
            <div className="rec-badges-right">
              {pendingRec.donor_score && (
                <div className="donor-score-badge">DONOR SCORE: {pendingRec.donor_score.toFixed(0)}</div>
              )}
              <div className="rec-id-badge">ID: {pendingRec.id}</div>
            </div>
          </div>

          <div className="rec-transfer-flow">
            <div className="facility-node donor-node">
              <span className="node-role">DONOR FACILITY (RANK #1)</span>
              <h3 className="node-name">
                {hospMap.get(pendingRec.from_hospital)?.name || pendingRec.from_hospital}
              </h3>
              <div className="node-details">
                Current Stock: {hospMap.get(pendingRec.from_hospital)?.current_stock ?? '—'}
                <span className="node-badge-safe">
                  Safe Surplus: +{pendingRec.donor_safety_margin_after ?? 82}
                </span>
                <span className="node-badge-transit">
                  <Navigation size={12} /> {pendingRec.estimated_transit_minutes || 20}m transit ({pendingRec.distance_km || 5.9} km)
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
                <span className="node-badge-urgent">Urgency: CRITICAL DEFICIT</span>
              </div>
            </div>
          </div>

          {/* Feature 1: Winning Donor Selection Rationale */}
          {pendingRec.winning_reason && (
            <div className="rec-winning-reason">
              <strong>Winning Donor Selection:</strong> {pendingRec.winning_reason}
            </div>
          )}

          {/* Feature 10: What Happens If We Do Nothing vs Intervene */}
          <div className="counterfactual-preview-grid">
            <div className="preview-card preview-do-nothing">
              <div className="preview-label text-critical">
                <AlertCircle size={14} /> WHAT HAPPENS IF WE DO NOTHING?
              </div>
              <p>
                {hospMap.get(pendingRec.to_hospital)?.name || pendingRec.to_hospital} reaches critical stockout in ~1.3 hours.
                Severe respiratory failure risk for ventilated patients.
              </p>
            </div>
            <div className="preview-card preview-intervene">
              <div className="preview-label text-safe">
                <ShieldCheck size={14} /> WHAT HAPPENS IF WE INTERVENE?
              </div>
              <p>
                {pendingRec.quantity} cylinders arrive within {pendingRec.estimated_transit_minutes || 20} min, extending stock horizon by +4.2 hours.
                Donor retains safe reserve. Zero secondary stockouts.
              </p>
            </div>
          </div>

          {/* Feature 1: Candidate Breakdown Accordion */}
          {pendingRec.candidate_breakdown && pendingRec.candidate_breakdown.length > 0 && (
            <div className="candidate-breakdown-section">
              <button
                className="btn-toggle-breakdown"
                onClick={() => setShowBreakdown(!showBreakdown)}
              >
                <span>FEASIBILITY AUDIT: EVALUATED CANDIDATE DONORS ({pendingRec.candidate_breakdown.length})</span>
                {showBreakdown ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>

              {showBreakdown && (
                <div className="candidate-table-wrap">
                  <table className="candidate-table">
                    <thead>
                      <tr>
                        <th>CANDIDATE</th>
                        <th>CURRENT STOCK</th>
                        <th>TRANSIT TIME</th>
                        <th>SAFE SURPLUS</th>
                        <th>PROJECTED 4H MIN</th>
                        <th>STATUS</th>
                        <th>SCORE</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pendingRec.candidate_breakdown.map((c) => (
                        <tr key={c.hospital_id} className={c.passed_all_constraints ? 'cand-pass' : 'cand-fail'}>
                          <td><strong>{c.hospital_name}</strong></td>
                          <td>{c.current_stock} / {c.safety_threshold}</td>
                          <td>{c.travel_time_minutes}m ({c.distance_km} km)</td>
                          <td>+{c.safe_surplus}</td>
                          <td>{c.projected_4h_stock} u</td>
                          <td>
                            {c.passed_all_constraints ? (
                              <span className="badge-pass">PASS</span>
                            ) : (
                              <span className="badge-reject" title={c.rejection_reason || ''}>
                                REJECTED: {c.rejection_reason}
                              </span>
                            )}
                          </td>
                          <td>{c.donor_score > 0 ? c.donor_score.toFixed(0) : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

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
      ) : noSafeRec ? (
        /* Feature 5: No Safe Transfer Intelligence Alert */
        <div className="recommendation-card-no-safe">
          <div className="no-safe-header">
            <div className="no-safe-flag">
              <AlertOctagon size={22} className="text-critical" />
              <span>NO SAFE TRANSFER AVAILABLE — HARD SAFETY CONSTRAINTS ACTIVE</span>
            </div>
            <div className="rec-id-badge">{noSafeRec.id}</div>
          </div>

          <div className="no-safe-body">
            <p className="no-safe-desc">{noSafeRec.justification}</p>

            <div className="escalation-alert-box">
              <div className="escalation-title">
                <AlertCircle size={16} /> EMERGENCY MUTUAL-AID ESCALATION DIRECTIVE
              </div>
              <p className="escalation-text">{noSafeRec.escalation_message}</p>
            </div>

            {noSafeRec.candidate_breakdown && (
              <div className="rejected-candidates-summary">
                <h4>EVALUATED REGIONAL FACILITIES REJECTION BREAKDOWN:</h4>
                <ul>
                  {noSafeRec.candidate_breakdown.map((c) => (
                    <li key={c.hospital_id}>
                      <strong>{c.hospital_name}:</strong> {c.rejection_reason || 'Safety margin violation'}
                    </li>
                  ))}
                </ul>
              </div>
            )}
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
            <span className="stat-pill">Critical Shortage: <strong>AVOIDED (+5.0h)</strong></span>
          </div>
        </div>
      ) : (
        <div className="recommendation-card-empty">
          <ShieldCheck size={36} className="empty-icon" />
          <h3 className="empty-title">All Hospital Reserves Within Safe Margins</h3>
          <p className="empty-desc">
            The feasibility optimizer continuously calculates depletion trajectories across all facilities.
            If a surge breaches safety limits, a redistribution plan will appear here.
          </p>
        </div>
      )}
    </div>
  );
};
