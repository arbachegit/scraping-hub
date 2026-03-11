'use client';

import { useState } from 'react';
import {
  Flame,
  ThermometerSun,
  Snowflake,
  Target,
  ArrowUpRight,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import type { BiOpportunity } from '@/lib/api';

interface OpportunityTableProps {
  opportunities: BiOpportunity[];
  isLoading: boolean;
}

const TEMP_CONFIG = {
  quente: { icon: Flame, color: 'text-orange-400', bg: 'bg-orange-500/10', label: 'Quente' },
  morno: { icon: ThermometerSun, color: 'text-yellow-400', bg: 'bg-yellow-500/10', label: 'Morno' },
  frio: { icon: Snowflake, color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Frio' },
};

const PRIORITY_CONFIG: Record<string, { color: string; label: string }> = {
  critica: { color: 'text-red-400', label: 'CRITICA' },
  alta: { color: 'text-orange-400', label: 'ALTA' },
  media: { color: 'text-yellow-400', label: 'MEDIA' },
  baixa: { color: 'text-gray-400', label: 'BAIXA' },
};

export function OpportunityTable({ opportunities, isLoading }: OpportunityTableProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filterTemp, setFilterTemp] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="rounded-xl border border-gray-800 bg-[#0f1629]/60 p-4 animate-pulse">
        <div className="h-4 bg-gray-700 rounded w-1/4 mb-4" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-10 bg-gray-700/30 rounded mb-2" />
        ))}
      </div>
    );
  }

  const filtered = filterTemp
    ? opportunities.filter((o) => o.lead_temperatura === filterTemp)
    : opportunities;

  const quentes = opportunities.filter((o) => o.lead_temperatura === 'quente').length;
  const mornos = opportunities.filter((o) => o.lead_temperatura === 'morno').length;
  const frios = opportunities.filter((o) => o.lead_temperatura === 'frio').length;

  return (
    <div className="rounded-xl border border-cyan-500/20 bg-[#0f1629]/60">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-cyan-400" />
          <h3 className="text-sm font-medium text-white">
            Oportunidades ({opportunities.length})
          </h3>
        </div>

        {/* Temperature filters */}
        <div className="flex items-center gap-1">
          <FilterPill
            label={`${quentes}`}
            icon={Flame}
            color="text-orange-400"
            active={filterTemp === 'quente'}
            onClick={() => setFilterTemp(filterTemp === 'quente' ? null : 'quente')}
          />
          <FilterPill
            label={`${mornos}`}
            icon={ThermometerSun}
            color="text-yellow-400"
            active={filterTemp === 'morno'}
            onClick={() => setFilterTemp(filterTemp === 'morno' ? null : 'morno')}
          />
          <FilterPill
            label={`${frios}`}
            icon={Snowflake}
            color="text-blue-400"
            active={filterTemp === 'frio'}
            onClick={() => setFilterTemp(filterTemp === 'frio' ? null : 'frio')}
          />
        </div>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="px-4 py-8 text-center text-sm text-gray-500">
          {opportunities.length === 0
            ? 'Nenhuma oportunidade detectada. Execute o pipeline para gerar scoring.'
            : 'Nenhuma oportunidade com este filtro.'}
        </div>
      ) : (
        <div className="max-h-[400px] overflow-y-auto">
          {filtered.map((opp) => {
            const temp = TEMP_CONFIG[opp.lead_temperatura as keyof typeof TEMP_CONFIG] || TEMP_CONFIG.frio;
            const prio = PRIORITY_CONFIG[opp.prioridade] || PRIORITY_CONFIG.baixa;
            const TempIcon = temp.icon;
            const isExpanded = expandedId === opp.id;

            return (
              <div key={opp.id} className="border-b border-gray-800/50 last:border-0">
                <button
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-xs hover:bg-gray-800/30 transition-colors text-left"
                  onClick={() => setExpandedId(isExpanded ? null : opp.id)}
                >
                  {/* Temperature */}
                  <span className={`flex items-center gap-1 ${temp.color} flex-shrink-0 w-14`}>
                    <TempIcon className="h-3.5 w-3.5" />
                    <span className="font-medium">{temp.label}</span>
                  </span>

                  {/* Score */}
                  <span className="flex-shrink-0 w-10 text-right font-mono tabular-nums font-bold text-white">
                    {opp.score_oportunidade}
                  </span>

                  {/* Score bar */}
                  <div className="flex-shrink-0 w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        opp.score_oportunidade >= 80 ? 'bg-green-500' :
                        opp.score_oportunidade >= 60 ? 'bg-cyan-500' :
                        opp.score_oportunidade >= 40 ? 'bg-yellow-500' : 'bg-gray-500'
                      }`}
                      style={{ width: `${opp.score_oportunidade}%` }}
                    />
                  </div>

                  {/* Type */}
                  <span className="text-gray-400 flex-shrink-0 w-24 whitespace-nowrap overflow-hidden text-ellipsis">
                    {opp.tipo_oportunidade.replace(/_/g, ' ')}
                  </span>

                  {/* Priority */}
                  <span className={`${prio.color} flex-shrink-0 w-14 font-medium text-right`}>
                    {prio.label}
                  </span>

                  {/* Expand */}
                  {isExpanded ? (
                    <ChevronUp className="h-3.5 w-3.5 text-gray-500 flex-shrink-0" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5 text-gray-500 flex-shrink-0" />
                  )}
                </button>

                {/* Expanded details */}
                {isExpanded && (
                  <div className="px-4 pb-3 space-y-2 bg-gray-800/20">
                    {opp.justificativa && (
                      <p className="text-xs text-gray-400 leading-relaxed">{opp.justificativa}</p>
                    )}
                    {opp.acoes_recomendadas && opp.acoes_recomendadas.length > 0 && (
                      <div>
                        <span className="text-xs text-gray-500 font-medium">Ações recomendadas:</span>
                        <ul className="mt-1 space-y-0.5">
                          {opp.acoes_recomendadas.map((acao, i) => (
                            <li key={i} className="flex items-start gap-1.5 text-xs text-gray-400">
                              <ArrowUpRight className="h-3 w-3 text-cyan-500 flex-shrink-0 mt-0.5" />
                              {acao}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {/* Score breakdown */}
                    <div className="flex gap-4 pt-1 text-xs text-gray-500">
                      <span>Geo: <span className="text-gray-400">{opp.score_geografico ?? '-'}</span></span>
                      <span>CNAE: <span className="text-gray-400">{opp.score_cnae ?? '-'}</span></span>
                      <span>Trib: <span className="text-gray-400">{opp.score_tributario ?? '-'}</span></span>
                      <span>Temp: <span className="text-gray-400">{opp.score_temporal ?? '-'}</span></span>
                      <span>Evid: <span className="text-gray-400">{opp.score_evidencia ?? '-'}</span></span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function FilterPill({
  label,
  icon: Icon,
  color,
  active,
  onClick,
}: {
  label: string;
  icon: React.ElementType;
  color: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs transition-colors ${
        active ? 'bg-gray-700' : 'hover:bg-gray-800'
      } ${color}`}
      onClick={onClick}
    >
      <Icon className="h-3 w-3" />
      {label}
    </button>
  );
}
