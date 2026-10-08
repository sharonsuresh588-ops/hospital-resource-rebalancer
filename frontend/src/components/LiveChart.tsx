import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts';
import type { TimelinePoint, Hospital } from '../types';
import { TrendingDown } from 'lucide-react';

interface LiveChartProps {
  timeline: TimelinePoint[];
  hospitals: Hospital[];
  surgeActive: boolean;
}

const HOSPITAL_COLORS: { [id: string]: { stroke: string; width: number } } = {
  'H-A': { stroke: '#ef4444', width: 3 }, // Bold Red (Critical/Surge)
  'H-B': { stroke: '#06b6d4', width: 2.5 }, // Cyan (Key Donor)
  'H-C': { stroke: '#a855f7', width: 1.5 }, // Purple
  'H-D': { stroke: '#3b82f6', width: 1.5 }, // Blue
  'H-E': { stroke: '#10b981', width: 1.5 }, // Emerald
  'H-F': { stroke: '#f59e0b', width: 1.5 }, // Amber
};

export const LiveChart: React.FC<LiveChartProps> = ({
  timeline,
  hospitals,
  surgeActive,
}) => {
  return (
    <div className="live-chart-section">
      <div className="section-header">
        <div className="section-title-wrap">
          <TrendingDown size={20} className="section-icon-accent" />
          <h2 className="section-heading">REAL-TIME OXYGEN TRAJECTORIES</h2>
        </div>
        <span className="section-caption">
          {surgeActive
            ? 'ALERT: District Hospital A trajectory sharply declining under surge demand'
            : 'Monitoring multi-facility depletion trends against safety baseline (60 cylinders)'}
        </span>
      </div>

      <div className="chart-container-box">
        {timeline.length > 0 ? (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart
              data={timeline}
              margin={{ top: 15, right: 30, left: 10, bottom: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#262c36" />
              <XAxis
                dataKey="tick"
                stroke="#64748b"
                tick={{ fontSize: 12 }}
                tickFormatter={(val) => `Tick ${val}`}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fontSize: 12 }}
                domain={[30, 240]}
                unit=" cyl"
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '6px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                  fontSize: '12px',
                }}
                labelFormatter={(val) => `Simulation Tick: ${val}`}
              />
              <Legend wrapperStyle={{ paddingTop: '8px', fontSize: '12px' }} />

              {/* Safety Threshold Reference Line */}
              <ReferenceLine
                y={60}
                stroke="#dc2626"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{
                  value: 'CRITICAL SAFETY THRESHOLD (60)',
                  fill: '#ef4444',
                  fontSize: 11,
                  position: 'insideTopLeft',
                }}
              />

              {/* Six Hospital Lines */}
              {hospitals.map((h) => {
                const styling = HOSPITAL_COLORS[h.id] || { stroke: '#94a3b8', width: 1.5 };
                return (
                  <Line
                    key={h.id}
                    type="monotone"
                    dataKey={h.id}
                    name={`${h.id} (${h.name.replace('District Hospital ', 'Hosp ')})`}
                    stroke={styling.stroke}
                    strokeWidth={styling.width}
                    dot={false}
                    isAnimationActive={false}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="chart-loading-placeholder">
            <span>Collecting initial telemetry data...</span>
          </div>
        )}
      </div>
    </div>
  );
};
