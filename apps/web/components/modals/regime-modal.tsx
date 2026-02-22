'use client';

import { X } from 'lucide-react';

interface RegimeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (codigo: string, descricao: string) => void;
}

const REGIMES = [
  {
    codigo: 'MEI',
    nome: 'Microempreendedor Individual',
    limite: 'Limite: R$ 81.000/ano',
    badge: 'MEI',
  },
  {
    codigo: 'SIMPLES_NACIONAL',
    nome: 'Simples Nacional',
    limite: 'Limite: R$ 4.800.000/ano',
    badge: 'SIMPLES',
  },
  {
    codigo: 'LUCRO_PRESUMIDO',
    nome: 'Lucro Presumido',
    limite: 'Limite: R$ 78.000.000/ano',
    badge: 'PRESUMIDO',
  },
  {
    codigo: 'LUCRO_REAL',
    nome: 'Lucro Real',
    limite: 'Obrigatorio acima de R$ 78 milhoes',
    badge: 'REAL',
  },
];

export function RegimeModal({ isOpen, onClose, onSelect }: RegimeModalProps) {
  function handleSelect(codigo: string, nome: string) {
    onSelect(codigo, nome);
    onClose();
  }

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/85"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="w-[95%] max-w-lg overflow-hidden rounded-2xl border border-green-500/20 bg-gradient-to-b from-[#0f1629] to-[#0a0e1a]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-green-500/15">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <span className="w-1 h-5 bg-gradient-to-b from-green-400 to-green-600 rounded" />
            Regime Tributario
          </h3>
          <button
            onClick={onClose}
            className="flex items-center justify-center w-9 h-9 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-400 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* List */}
        <div className="p-6 space-y-2">
          {REGIMES.map((regime) => (
            <div
              key={regime.codigo}
              onClick={() => handleSelect(regime.codigo, regime.nome)}
              className="flex items-center justify-between p-4 bg-white/[0.02] border border-white/5 rounded-lg cursor-pointer hover:bg-green-500/10 hover:border-green-500/30 transition-colors"
            >
              <div>
                <div className="text-white font-medium">{regime.nome}</div>
                <div className="text-slate-400 text-sm">{regime.limite}</div>
              </div>
              <span className="font-mono text-xs text-green-400 bg-green-500/10 px-2 py-1 rounded">
                {regime.badge}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
