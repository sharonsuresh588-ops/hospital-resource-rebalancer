import React from 'react';
import type { NetworkRiskItem } from '../types';
import { ShieldAlert, AlertTriangle, Eye, CheckCircle, Flame } from 'lucide-react';

interface NetworkRiskPanelProps {
  ranking: NetworkRiskItem[];
}

export const NetworkRiskPanel: React.FC<NetworkRiskPanelProps> = ({ ranking }) => {
  if (!ranking || ranking.length === 0) return null;

  const getBadgeClass = (level: string) => {
    switch (level) {
      case 'NETWORK EMERGENCY':
        return 'risk-emergency';
      case 'CRITICAL':
        return 'risk-critical';
      case 'WARNING':
        return 'risk-warning';
      case 'WATCH':
        return 'risk-watch';
      default:
        return 'risk-normal';
    }
  };

  const getIcon = (level: string) => {
    switch (level) {
      case 'NETWORK EMERGENCY':
        return <Flame size={14} className="risk-icon-flame" />;
      case 'CRITICAL':
        return <ShieldAlert size={14} className="text-critical" />;
      case 'WARNING':
        return <AlertTriangle size={14} className="text-amber" />;
      case 'WATCH':
        return <Eye size={14} className="text-watch" />;
      default:
        return <CheckCircle size={14} className="text-safe" />;
    }
  };

  return (
    <div className="network-risk-panel-root">
      <div className="section-header">
        <div className="section-title-wrap">
          <ShieldAlert className="section-icon-accent" size={20} />
          <h2 className="section-heading">NETWORK-WIDE RISK PRIORITY</h2>
        </div>
        <span className="section-caption">
          Deterministic multi-factor risk scoring: stock deficit, depletion velocity, and 4h forward vulnerability
        </span>
      </div>

      <div className="risk-table-container">
        <table className="risk-table">
          <thead>
            <tr>
              <th>RANK</th>
              <th>FACILITY</th>
              <th>STOCK / THRESHOLD</th>
              <th>DEPLETION VELOCITY</th>
              <th>TIME TO SHORTAGE</th>
              <th>PROJECTED 4H MIN</th>
              <th>RISK LEVEL</th>
              <th>SCORE</th>
            </tr>
          </thead>
          <tbody>
            {ranking.map((item) => (
              <tr key={item.hospital_id} className={`risk-row ${getBadgeClass(item.risk_level)}`}>
                <td className="rank-cell">#{item.rank}</td>
                <td className="facility-cell">
                  <strong>{item.hospital_name}</strong>
                  <span className="id-sub">({item.hospital_id})</span>
                </td>
                <td>
                  <span className={item.current_stock <= item.safety_threshold ? 'text-critical font-bold' : ''}>
                    {item.current_stock}
                  </span>{' '}
                  / {item.safety_threshold}
                </td>
                <td>{item.depletion_rate.toFixed(1)} u/hr</td>
                <td>
                  {item.time_to_shortage_hours !== null ? (
                    <span className={item.time_to_shortage_hours <= 2.5 ? 'shortage-crit' : 'shortage-warn'}>
                      {item.time_to_shortage_hours.toFixed(1)} hrs
                    </span>
                  ) : (
                    <span className="text-safe">Adequate</span>
                  )}
                </td>
                <td>{item.projected_min_stock.toFixed(0)} u</td>
                <td>
                  <span className={`risk-pill ${getBadgeClass(item.risk_level)}`}>
                    {getIcon(item.risk_level)} {item.risk_level}
                  </span>
                </td>
                <td className="score-cell">{item.risk_score.toFixed(0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
