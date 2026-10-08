import React from 'react';
import type { Hospital, Prediction } from '../types';
import { HospitalCard } from './HospitalCard';

interface HospitalGridProps {
  hospitals: Hospital[];
  predictions: Prediction[];
  surgeActive: boolean;
}

export const HospitalGrid: React.FC<HospitalGridProps> = ({
  hospitals,
  predictions,
  surgeActive,
}) => {
  const predMap = new Map<string, Prediction>();
  predictions.forEach((p) => predMap.set(p.hospital_id, p));

  return (
    <div className="hospital-grid-section">
      <div className="section-header">
        <h2 className="section-heading">FACILITIES STATUS GRID (6 HOSPITALS)</h2>
        <span className="section-caption">Live oxygen cylinder reserves & depletion projections</span>
      </div>
      <div className="hospitals-card-grid">
        {hospitals.map((h) => (
          <HospitalCard
            key={h.id}
            hospital={h}
            prediction={predMap.get(h.id)}
            isSurging={surgeActive && h.id === 'H-A'}
          />
        ))}
      </div>
    </div>
  );
};
