import React from 'react';
import { Play, Pause, Flame, RotateCcw, FastForward, Sliders, Bot, Layers } from 'lucide-react';
import type { SimulationStatus } from '../types';

interface ControlBarProps {
  simulation: SimulationStatus;
  onTogglePlay: () => void;
  onInjectSurge: () => void;
  onReset: () => void;
  onOpenReplay: () => void;
  onOpenWhatIf: () => void;
  onOpenCopilot: () => void;
  onSelectScenario: (scenarioName: string) => void;
  loadingAction: string | null;
}

export const ControlBar: React.FC<ControlBarProps> = ({
  simulation,
  onTogglePlay,
  onInjectSurge,
  onReset,
  onOpenReplay,
  onOpenWhatIf,
  onOpenCopilot,
  onSelectScenario,
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
              <Pause size={16} /> PAUSE
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
          title="Inject demand surge into Hospital A"
        >
          <Flame size={16} className={simulation.surge_active ? 'surge-flame-anim' : ''} />
          {simulation.surge_active ? 'SURGE ACTIVE (H-A)' : 'INJECT SURGE'}
        </button>

        <button
          className="btn-control btn-reset"
          onClick={onReset}
          disabled={loadingAction !== null}
          title="Reset simulation to initial baseline"
        >
          <RotateCcw size={16} /> RESET
        </button>

        {/* Feature 11: Demo Scenario Control Preset Selector */}
        <div className="scenario-preset-selector">
          <Layers size={14} className="text-accent" />
          <select
            className="preset-dropdown"
            value={simulation.scenario_name || 'standard_surge'}
            onChange={(e) => onSelectScenario(e.target.value)}
            disabled={loadingAction !== null}
          >
            <option value="standard_surge">Scenario: Standard Surge (Main Demo)</option>
            <option value="normal_operations">Scenario: Normal Operations (Calm)</option>
            <option value="multi_hospital_stress">Scenario: Multi-Hospital Stress (H-A & H-D)</option>
            <option value="no_safe_donor">Scenario: No-Safe-Donor (Refusal Test)</option>
          </select>
        </div>
      </div>

      <div className="control-bar-right">
        <button
          className="btn-control btn-tool-action"
          onClick={onOpenWhatIf}
          disabled={loadingAction !== null}
          title="Interactive What-If Scenario Simulator"
        >
          <Sliders size={15} /> WHAT-IF
        </button>

        <button
          className="btn-control btn-tool-action"
          onClick={onOpenCopilot}
          disabled={loadingAction !== null}
          title="Gemini Operations Copilot"
        >
          <Bot size={15} /> COPILOT
        </button>

        <button
          className="btn-control btn-replay"
          onClick={onOpenReplay}
          disabled={loadingAction !== null}
          title="Run counterfactual evaluation: Without System vs With System"
        >
          <FastForward size={15} /> REPLAY SCENARIO
        </button>
      </div>
    </div>
  );
};
