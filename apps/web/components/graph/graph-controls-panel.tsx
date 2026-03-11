'use client';

import {
  Snowflake, Play, SlidersHorizontal, Target,
  Route, BarChart3, Crosshair, X,
} from 'lucide-react';
import { ENTITY_COLORS, ENTITY_LABELS } from './styles';
import type { GraphControls, GraphNode, RankingMetric } from './types';

interface GraphControlsPanelProps {
  controls: GraphControls;
  nodes: GraphNode[];
  onClose: () => void;
}

function SliderRow({ label, value, min, max, step, onChange, displayValue }: {
  label: string; value: number; min: number; max: number; step: number;
  onChange: (v: number) => void; displayValue?: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-slate-400">{label}</span>
        <span className="text-[10px] font-medium tabular-nums text-cyan-400">{displayValue ?? value}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        className="h-1 w-full cursor-pointer appearance-none rounded-full bg-slate-700 accent-cyan-500 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-cyan-400"
      />
    </div>
  );
}

export function GraphControlsPanel({ controls, nodes, onClose }: GraphControlsPanelProps) {
  const {
    frozen, toggleFreeze,
    evidenceThreshold, setEvidenceThreshold,
    edgeDensityPercent, setEdgeDensityPercent,
    egoNodeId, egoHops, setEgoNodeId, setEgoHops,
    pathSourceId, pathTargetId, setPathSourceId, setPathTargetId, pathNodeIds,
    rankingMetric, setRankingMetric,
    zoomLevel,
  } = controls;

  const rankOptions: { value: RankingMetric; label: string }[] = [
    { value: 'none', label: 'Nenhum' },
    { value: 'degree', label: 'Grau' },
    { value: 'betweenness', label: 'Intermediacao' },
    { value: 'pagerank', label: 'PageRank' },
  ];

  return (
    <div className="flex w-56 flex-col border-l border-cyan-500/10 bg-[#0f1629] h-full overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-cyan-500/10 px-3 py-2 flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <SlidersHorizontal size={12} className="text-cyan-400" />
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Controles</span>
        </div>
        <button onClick={onClose} className="rounded p-0.5 text-slate-500 hover:text-white transition-colors">
          <X size={12} />
        </button>
      </div>

      <div className="px-3 py-2 space-y-4">
        {/* ── Freeze Physics ── */}
        <div>
          <button
            onClick={toggleFreeze}
            className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs font-medium transition-colors ${
              frozen
                ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
                : 'bg-slate-800/60 text-slate-400 border border-slate-700/50 hover:text-white'
            }`}
          >
            {frozen ? <Snowflake size={13} /> : <Play size={13} />}
            {frozen ? 'Layout Congelado' : 'Congelar Layout'}
          </button>
        </div>

        {/* ── Zoom Level Indicator ── */}
        <div>
          <span className="text-[10px] font-medium uppercase tracking-wider text-slate-500">Zoom</span>
          <div className="mt-1 flex gap-1">
            {(['macro', 'intermediate', 'detail'] as const).map(level => (
              <span
                key={level}
                className={`flex-1 text-center text-[9px] rounded py-0.5 ${
                  zoomLevel === level ? 'bg-cyan-500/20 text-cyan-400 font-semibold' : 'bg-slate-800/40 text-slate-600'
                }`}
              >
                {level === 'macro' ? 'Macro' : level === 'intermediate' ? 'Inter' : 'Detalhe'}
              </span>
            ))}
          </div>
        </div>

        {/* ── Evidence Threshold ── */}
        <div>
          <h4 className="text-[10px] font-medium uppercase tracking-wider text-slate-500 mb-2">
            Limiar de Evidencia
          </h4>
          <SliderRow
            label="Probabilidade minima"
            value={evidenceThreshold}
            min={0} max={1} step={0.05}
            onChange={setEvidenceThreshold}
            displayValue={`${Math.round(evidenceThreshold * 100)}%`}
          />
        </div>

        {/* ── Edge Density ── */}
        <div>
          <h4 className="text-[10px] font-medium uppercase tracking-wider text-slate-500 mb-2">
            Densidade de Arestas
          </h4>
          <SliderRow
            label="Top conexoes por forca"
            value={edgeDensityPercent}
            min={5} max={100} step={5}
            onChange={setEdgeDensityPercent}
            displayValue={`${edgeDensityPercent}%`}
          />
        </div>

        {/* ── Node Ranking ── */}
        <div>
          <h4 className="text-[10px] font-medium uppercase tracking-wider text-slate-500 mb-2">
            <BarChart3 size={10} className="inline mr-1" />
            Ranking de Nos
          </h4>
          <div className="space-y-1">
            {rankOptions.map(opt => (
              <label key={opt.value} className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="radio" name="ranking" value={opt.value}
                  checked={rankingMetric === opt.value}
                  onChange={() => setRankingMetric(opt.value)}
                  className="accent-cyan-500 h-3 w-3"
                />
                <span className={`text-[10px] ${rankingMetric === opt.value ? 'text-cyan-400 font-medium' : 'text-slate-400 group-hover:text-slate-300'}`}>
                  {opt.label}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* ── Ego Network ── */}
        <div>
          <h4 className="text-[10px] font-medium uppercase tracking-wider text-slate-500 mb-2">
            <Crosshair size={10} className="inline mr-1" />
            Rede Ego
          </h4>
          {egoNodeId ? (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 bg-slate-800/60 rounded px-2 py-1">
                <Target size={10} className="text-cyan-400 flex-shrink-0" />
                <span className="text-[10px] text-slate-300 truncate flex-1">
                  {nodes.find(n => n.id === egoNodeId)?.label || egoNodeId}
                </span>
                <button onClick={() => setEgoNodeId(null)} className="text-slate-500 hover:text-white">
                  <X size={10} />
                </button>
              </div>
              <SliderRow
                label="Profundidade"
                value={egoHops} min={1} max={4} step={1}
                onChange={v => setEgoHops(v)}
                displayValue={`${egoHops} hop${egoHops > 1 ? 's' : ''}`}
              />
            </div>
          ) : (
            <p className="text-[9px] text-slate-500 italic">
              Duplo-clique em um no para ativar
            </p>
          )}
        </div>

        {/* ── Path Finder ── */}
        <div>
          <h4 className="text-[10px] font-medium uppercase tracking-wider text-slate-500 mb-2">
            <Route size={10} className="inline mr-1" />
            Caminho Mais Curto
          </h4>
          <div className="space-y-1.5">
            <NodePicker
              label="Origem"
              value={pathSourceId}
              nodes={nodes}
              onChange={setPathSourceId}
            />
            <NodePicker
              label="Destino"
              value={pathTargetId}
              nodes={nodes}
              onChange={setPathTargetId}
            />
            {pathNodeIds.size > 0 && (
              <div className="text-[9px] text-green-400 font-medium">
                Caminho: {pathNodeIds.size} nos
              </div>
            )}
            {pathSourceId && pathTargetId && pathNodeIds.size === 0 && (
              <div className="text-[9px] text-red-400">
                Sem caminho encontrado
              </div>
            )}
            {(pathSourceId || pathTargetId) && (
              <button
                onClick={() => { setPathSourceId(null); setPathTargetId(null); }}
                className="text-[9px] text-slate-500 hover:text-white underline"
              >
                Limpar
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function NodePicker({ label, value, nodes, onChange }: {
  label: string; value: string | null; nodes: GraphNode[];
  onChange: (id: string | null) => void;
}) {
  return (
    <div>
      <span className="text-[9px] text-slate-500">{label}</span>
      <select
        value={value || ''}
        onChange={e => onChange(e.target.value || null)}
        className="mt-0.5 w-full rounded bg-slate-800/80 border border-slate-700/50 px-1.5 py-1 text-[10px] text-slate-300 outline-none focus:border-cyan-500/50"
      >
        <option value="">Selecionar no...</option>
        {nodes.map(n => (
          <option key={n.id} value={n.id}>
            {n.label} ({ENTITY_LABELS[n.type] || n.type})
          </option>
        ))}
      </select>
    </div>
  );
}
