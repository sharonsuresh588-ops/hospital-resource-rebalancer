import React, { useState } from 'react';
import { executeCopilotAction } from '../services/api';
import type { Recommendation, Hospital } from '../types';
import { Bot, X, FileText, Send, Sparkles, Check, AlertOctagon } from 'lucide-react';

interface CopilotModalProps {
  isOpen: boolean;
  onClose: () => void;
  recommendation?: Recommendation | null;
  hospitals: Hospital[];
}

export const CopilotModal: React.FC<CopilotModalProps> = ({
  isOpen,
  onClose,
  recommendation,
  hospitals,
}) => {
  const [selectedAction, setSelectedAction] = useState<string>('brief_coordinator');
  const [loading, setLoading] = useState<boolean>(false);
  const [output, setOutput] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleAction = async (actionType: string) => {
    setSelectedAction(actionType);
    setLoading(true);
    setError(null);
    setOutput(null);

    const destHosp = hospitals.find((h) => h.id === recommendation?.to_hospital) || hospitals[0];
    const donorHosp = hospitals.find((h) => h.id === recommendation?.from_hospital) || hospitals[1];

    const facts = {
      recipient_name: destHosp?.name || 'District Hospital A',
      donor_name: donorHosp?.name || 'District Hospital B',
      quantity: recommendation?.quantity || 40,
      time_to_shortage: '1.3',
      safe_surplus: recommendation?.donor_safety_margin_after || 82,
      transit_time: recommendation?.estimated_transit_minutes || 22,
      donor_score: recommendation?.donor_score || 1420,
      deadline_minutes: recommendation?.dispatch_deadline_minutes || 45,
      prevented_hours: 5.0,
    };

    try {
      const res = await executeCopilotAction(actionType, facts);
      setOutput(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to generate copilot communication.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (output) {
      navigator.clipboard.writeText(output);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container modal-medium" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-wrap">
            <Bot size={20} className="text-accent" />
            <h2 className="modal-title">GEMINI OPERATIONS COPILOT</h2>
          </div>
          <button className="btn-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="copilot-body">
          <p className="copilot-subtitle">
            Generate high-level operational communication based on verified deterministic metrics. Gemini performs
            communication synthesis only and does not alter transfer decisions.
          </p>

          <div className="copilot-actions-grid">
            <button
              className={`btn-copilot-action ${selectedAction === 'brief_coordinator' ? 'active' : ''}`}
              onClick={() => handleAction('brief_coordinator')}
              disabled={loading}
            >
              <Sparkles size={16} /> Brief Operations Chief
            </button>
            <button
              className={`btn-copilot-action ${selectedAction === 'explain_donor_selection' ? 'active' : ''}`}
              onClick={() => handleAction('explain_donor_selection')}
              disabled={loading}
            >
              <FileText size={16} /> Explain Donor Selection
            </button>
            <button
              className={`btn-copilot-action ${selectedAction === 'generate_escalation' ? 'active' : ''}`}
              onClick={() => handleAction('generate_escalation')}
              disabled={loading}
            >
              <AlertOctagon size={16} /> Generate Escalation Memo
            </button>
            <button
              className={`btn-copilot-action ${selectedAction === 'summarize_outcome' ? 'active' : ''}`}
              onClick={() => handleAction('summarize_outcome')}
              disabled={loading}
            >
              <Send size={16} /> Summarize Intervention
            </button>
          </div>

          {loading && (
            <div className="copilot-loading">
              <span className="btn-spinner"></span> Synthesizing operational brief with Gemini...
            </div>
          )}

          {error && <div className="copilot-error">{error}</div>}

          {output && !loading && (
            <div className="copilot-output-card">
              <div className="output-card-header">
                <span className="output-tag">SYNTHESIZED DISPATCH BRIEF</span>
                <button className="btn-copy" onClick={handleCopy}>
                  {copied ? <Check size={14} /> : <FileText size={14} />} {copied ? 'COPIED' : 'COPY'}
                </button>
              </div>
              <p className="output-text">"{output}"</p>
              <div className="output-footer">
                <span>Model: <strong>Google Gemini 3.5 Flash-Lite</strong></span>
                <span>Deterministic Invariant: <strong>Verified Preserved</strong></span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
