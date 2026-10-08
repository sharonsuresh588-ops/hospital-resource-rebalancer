import React from 'react';
import type { Hospital, Prediction } from '../types';
import { AlertCircle, CheckCircle2, AlertTriangle, ShieldAlert } from 'lucide-react';

interface HospitalCardProps {
  hospital: Hospital;
  prediction?: Prediction;
  isSurging?: boolean;
}

export const HospitalCard: React.FC<HospitalCardProps> = ({
  hospital,
  prediction,
  isSurging = false,
}) => {
  const stock = hospital.current_stock;
  const capacity = hospital.capacity;
  const threshold = hospital.safety_threshold;
  const pct = Math.min(100, Math.max(0, Math.round((stock / capacity) * 100)));

  const status = prediction?.status || 'SAFE';
  const depletionRate = prediction?.depletion_rate ?? 0.0;
  const shortageHours = prediction?.time_to_shortage_hours;

  const getStatusBadge = () => {
    switch (status) {
      case 'CRITICAL':
        return (
          <span className="status-badge badge-critical">
            <AlertCircle size={13} /> CRITICAL
          </span>
        );
      case 'WARNING':
        return (
          <span className="status-badge badge-warning">
            <AlertTriangle size={13} /> WARNING
          </span>
        );
      case 'SAFE':
      default:
        return (
          <span className="status-badge badge-safe">
            <CheckCircle2 size={13} /> SAFE
          </span>
        );
    }
  };

  const getCardBorderClass = () => {
    if (status === 'CRITICAL') return 'border-critical';
    if (status === 'WARNING') return 'border-warning';
    return 'border-safe';
  };

  return (
    <div className={`hospital-card ${getCardBorderClass()} ${isSurging ? 'card-surging' : ''}`}>
      <div className="hosp-card-header">
        <div>
          <div className="hosp-id-tag">{hospital.id}</div>
          <h3 className="hosp-name">{hospital.name}</h3>
        </div>
        <div>{getStatusBadge()}</div>
      </div>

      <div className="hosp-stock-section">
        <div className="stock-label-row">
          <span className="stock-title">OXYGEN CYLINDERS</span>
          <span className="stock-count">
            <strong>{stock}</strong> / {capacity}
          </span>
        </div>

        {/* Progress bar with threshold indicator */}
        <div className="stock-progress-track">
          <div
            className={`stock-progress-fill ${
              status === 'CRITICAL'
                ? 'fill-critical'
                : status === 'WARNING'
                ? 'fill-warning'
                : 'fill-safe'
            }`}
            style={{ width: `${pct}%` }}
          />
          {/* Threshold marker */}
          <div
            className="threshold-marker"
            style={{ left: `${(threshold / capacity) * 100}%` }}
            title={`Safety Threshold: ${threshold} cylinders`}
          />
        </div>

        <div className="threshold-label-row">
          <span>0</span>
          <span className="threshold-tag">Safety Limit: {threshold}</span>
          <span>{capacity}</span>
        </div>
      </div>

      <div className="hosp-metrics-grid">
        <div className="metric-box">
          <span className="metric-box-title">Depletion</span>
          <span className="metric-box-value">
            {depletionRate.toFixed(1)}{' '}
            <small className="metric-sub">units/hr</small>
          </span>
        </div>

        <div className="metric-box">
          <span className="metric-box-title">Time to Shortage</span>
          <span
            className={`metric-box-value ${
              status === 'CRITICAL'
                ? 'text-critical'
                : status === 'WARNING'
                ? 'text-amber'
                : 'text-safe'
            }`}
          >
            {stock <= threshold ? (
              <span className="breach-warning">DEFICIT</span>
            ) : shortageHours !== null && shortageHours !== undefined ? (
              `${shortageHours.toFixed(1)} hr`
            ) : (
              'Adequate'
            )}
          </span>
        </div>
      </div>

      <div className="hosp-card-footer">
        <span className="confidence-tag">
          Confidence: {prediction ? `${Math.round(prediction.confidence * 100)}%` : '—'}
        </span>
        {isSurging && (
          <span className="surge-flag">
            <ShieldAlert size={12} /> SURGE ACTIVE
          </span>
        )}
      </div>
    </div>
  );
};
