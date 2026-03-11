'use client';

import {
  Users,
  Truck,
  Swords,
  Handshake,
  ExternalLink,
  ShieldCheck,
} from 'lucide-react';
import type { EcosystemData } from '@/lib/api';

interface EcosystemMapProps {
  ecosystem: EcosystemData | null;
  isLoading: boolean;
}

const SECTION_CONFIG = {
  clientes: { icon: Users, color: 'text-green-400', border: 'border-green-500/20', label: 'Clientes' },
  fornecedores: { icon: Truck, color: 'text-blue-400', border: 'border-blue-500/20', label: 'Fornecedores' },
  concorrentes: { icon: Swords, color: 'text-red-400', border: 'border-red-500/20', label: 'Concorrentes' },
  parceiros: { icon: Handshake, color: 'text-purple-400', border: 'border-purple-500/20', label: 'Parceiros' },
};

export function EcosystemMap({ ecosystem, isLoading }: EcosystemMapProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="rounded-xl border border-gray-800 bg-[#0f1629]/60 p-4 animate-pulse">
            <div className="h-4 bg-gray-700 rounded w-1/3 mb-3" />
            <div className="space-y-2">
              <div className="h-3 bg-gray-700/50 rounded w-2/3" />
              <div className="h-3 bg-gray-700/50 rounded w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!ecosystem) return null;

  return (
    <div className="space-y-3">
      {/* Confirmed relationships */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {(Object.keys(SECTION_CONFIG) as Array<keyof typeof SECTION_CONFIG>).map((key) => {
          const config = SECTION_CONFIG[key];
          const Icon = config.icon;
          const items = ecosystem.confirmados[key] || [];

          return (
            <div key={key} className={`rounded-xl border ${config.border} bg-[#0f1629]/60 p-3`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5">
                  <Icon className={`h-3.5 w-3.5 ${config.color}`} />
                  <span className={`text-xs font-medium ${config.color}`}>{config.label}</span>
                </div>
                <span className="text-xs text-gray-500 font-mono tabular-nums">{items.length}</span>
              </div>

              {items.length === 0 ? (
                <p className="text-xs text-gray-600">Nenhum detectado</p>
              ) : (
                <div className="space-y-1 max-h-[150px] overflow-y-auto">
                  {items.map((item) => (
                    <div
                      key={item.id}
                      className="flex items-center justify-between gap-2 text-xs px-1.5 py-1 rounded hover:bg-gray-800/30"
                    >
                      <span className="text-gray-300 min-w-0 whitespace-nowrap overflow-hidden text-ellipsis">
                        {item.nome_empresa_relacionada}
                      </span>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        {/* Confidence */}
                        <ConfidenceDot value={item.confianca} />
                        {/* Source badge */}
                        <span className="text-gray-600 text-[10px]">{item.fonte_deteccao}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Potential CNAE-based relationships */}
      {ecosystem.potenciais_cnae && (
        <div className="rounded-xl border border-cyan-500/10 bg-[#0f1629]/40 p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <ShieldCheck className="h-3.5 w-3.5 text-cyan-400" />
            <span className="text-xs font-medium text-cyan-400">Relações potenciais (CNAE)</span>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {(['clientes', 'fornecedores', 'concorrentes'] as const).map((type) => {
              const items = ecosystem.potenciais_cnae[type] || [];
              return (
                <div key={type} className="text-xs">
                  <span className="text-gray-500 capitalize">{type} ({items.length})</span>
                  <div className="mt-1 space-y-0.5 max-h-[80px] overflow-y-auto">
                    {items.slice(0, 5).map((item) => (
                      <div key={item.id} className="text-gray-400 truncate" title={item.razao_social}>
                        {item.razao_social}
                      </div>
                    ))}
                    {items.length > 5 && (
                      <span className="text-gray-600">+{items.length - 5} mais</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function ConfidenceDot({ value }: { value: number }) {
  const color = value >= 0.8 ? 'bg-green-400' : value >= 0.5 ? 'bg-yellow-400' : 'bg-red-400';
  return (
    <span
      className={`inline-block w-1.5 h-1.5 rounded-full ${color}`}
      title={`Confiança: ${Math.round(value * 100)}%`}
    />
  );
}
