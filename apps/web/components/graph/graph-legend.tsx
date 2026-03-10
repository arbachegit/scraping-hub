'use client';

import { useState } from 'react';
import { Info } from 'lucide-react';
import { ENTITY_COLORS, ENTITY_LABELS, EDGE_STYLES } from './styles';

const EDGE_STYLE_LABELS: Record<string, string[]> = {
  solid: ['Societaria', 'Fundador', 'Diretor'],
  dashed: ['Fornecedor', 'Empregado', 'Beneficiario'],
  dotted: ['Mencionado', 'Noticia menciona'],
};

export function GraphLegend() {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div className="absolute bottom-3 left-3 z-10">
      <button
        onClick={() => setIsVisible((prev) => !prev)}
        className="rounded bg-[#0f1629]/90 p-1.5 text-slate-400 shadow-lg transition-colors hover:text-white"
        title="Toggle legend"
      >
        <Info size={16} />
      </button>

      {isVisible && (
        <div className="mt-1 max-h-[70vh] overflow-y-auto rounded border border-cyan-500/20 bg-[#0f1629]/95 px-3 py-2.5 shadow-xl">
          {/* Entity colors */}
          <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">
            Categorias
          </h4>
          <div className="mb-3 space-y-1">
            {Object.entries(ENTITY_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center gap-2 text-xs">
                <div
                  className="h-3 w-3 flex-shrink-0 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <span className="text-slate-300">{ENTITY_LABELS[type] || type}</span>
              </div>
            ))}
          </div>

          {/* Edge styles */}
          <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">
            Conexoes
          </h4>
          <div className="mb-3 space-y-1">
            {Object.entries(EDGE_STYLE_LABELS).map(([style, labels]) => (
              <div key={style} className="flex items-center gap-2 text-xs">
                <svg width="24" height="8" className="flex-shrink-0">
                  <line
                    x1="0"
                    y1="4"
                    x2="24"
                    y2="4"
                    stroke="#94a3b8"
                    strokeWidth="2"
                    strokeDasharray={
                      style === 'dashed' ? '4,3' : style === 'dotted' ? '1,3' : undefined
                    }
                  />
                </svg>
                <span className="text-slate-300">{labels.join(', ')}</span>
              </div>
            ))}
          </div>

          {/* Strength / distance explanation */}
          <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">
            Forca da Conexao
          </h4>
          <div className="space-y-1.5 text-[10px] leading-tight text-slate-400">
            <div className="flex items-start gap-2">
              <div className="mt-0.5 flex gap-0.5">
                <div className="h-3 w-3 rounded-full bg-cyan-400" />
              </div>
              <span><strong className="text-slate-300">Perto do centro</strong> = conexao forte (referencia direta ao nome)</span>
            </div>
            <div className="flex items-start gap-2">
              <div className="mt-0.5 flex gap-0.5">
                <div className="h-2 w-2 rounded-full bg-cyan-400/40" />
              </div>
              <span><strong className="text-slate-300">Longe do centro</strong> = conexao fraca (poucas mencoes)</span>
            </div>
            <div className="flex items-start gap-2">
              <svg width="24" height="8" className="mt-0.5 flex-shrink-0">
                <line x1="0" y1="4" x2="24" y2="4" stroke="#06b6d4" strokeWidth="3" />
              </svg>
              <span><strong className="text-slate-300">Linha grossa</strong> = mais mencoes</span>
            </div>
            <div className="flex items-start gap-2">
              <svg width="24" height="8" className="mt-0.5 flex-shrink-0">
                <line x1="0" y1="4" x2="24" y2="4" stroke="#06b6d4" strokeWidth="0.8" strokeOpacity="0.3" />
              </svg>
              <span><strong className="text-slate-300">Linha fina</strong> = poucas mencoes</span>
            </div>
            <div className="flex items-start gap-2">
              <div className="mt-0.5 flex gap-0.5">
                <div className="h-4 w-4 rounded-full border border-cyan-400/50 bg-cyan-400/20" />
              </div>
              <span><strong className="text-slate-300">Circulo grande</strong> = no forte</span>
            </div>
            <div className="mt-1 border-t border-slate-700/50 pt-1 text-slate-500">
              Nos conectados entre si = nome de um aparece no conteudo do outro
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
