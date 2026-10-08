import React from 'react';
import { Play, Pause, Flame, RotateCcw, FastForward } from 'lucide-react';
import type { SimulationStatus } from '../types';

interface ControlBarProps {
  simulation: SimulationStatus;
  onTogglePlay: () => void;
  onInjectSurge: () => void;
  onReset: () => void;
  onOpenReplay: () => void;
  loadingAction: string | null;
}

export const ControlBar: React.FC<ControlBarProps> = ({
  simulation,
  onTogglePlay,
  onInjectSurge,
  onReset,
  onOpenReplay,
  loadingAction,
}) => {
  return (
    <div className="control-bar-container">
      <div className="control-bar-left">
        <button
          className={`btn-control btn-play ${simulation.running ? 'btn-active' : ''}`}
          onClick={onTogglePlay}
          disabled={loadingAction !== null}
        >
          {simulation.running ? (
            <>
              <Pause size={16} /> PAUSE SIMULATION
            </>
          ) : (
            <>
              <Play size={16} /> START SIMULATION
            </>
          )}
        </button>

        <button
          className={`btn-control btn-surge ${simulation.surge_active ? 'btn-surge-active' : ''}`}
          onClick={onInjectSurge}
          disabled={loadingAction !== null}
          title="Inject sudden consumption surge at District Hospital A"
        >
          <Flame size={16} className={simulation.surge_active ? 'surge-flame-anim' : ''} />
          {simulation.surge_active ? 'SURGE ACTIVE (H-A)' : 'INJECT SURGE'}
        </button>

        <button
          className="btn-control btn-reset"
          onClick={onReset}
          disabled={loadingAction !== null}
          title="Reset simulation and restore deterministic starting stocks"
        >
          <RotateCcw size={16} /> RESET
        </button>
      </div>

      <div className="control-bar-right">
        <button
          className="btn-control btn-replay"
          onClick={onOpenReplay}
          disabled={loadingAction !== null}
          title="Run counterfactual evaluation: Without System vs With System"
        >
          <FastForward size={16} /> REPLAY SCENARIO
        </button>
      </div>
    </div>
  );
};
