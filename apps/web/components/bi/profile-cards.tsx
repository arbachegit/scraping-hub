'use client';

import {
  BarChart3,
  Building2,
  MapPin,
  TrendingUp,
  Users,
  DollarSign,
  Activity,
} from 'lucide-react';
import type { BiProfile } from '@/lib/api';

interface ProfileCardsProps {
  profile: BiProfile | null;
  isLoading: boolean;
}

export function ProfileCards({ profile, isLoading }: ProfileCardsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="rounded-xl border border-gray-800 bg-[#0f1629]/60 p-4 animate-pulse">
            <div className="h-4 bg-gray-700 rounded w-1/3 mb-3" />
            <div className="space-y-2">
              <div className="h-3 bg-gray-700/50 rounded w-2/3" />
              <div className="h-3 bg-gray-700/50 rounded w-1/2" />
              <div className="h-3 bg-gray-700/50 rounded w-3/4" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!profile) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      {/* CNAE Profile */}
      <div className="rounded-xl border border-blue-500/20 bg-[#0f1629]/60 p-4">
        <div className="flex items-center gap-2 mb-3">
          <BarChart3 className="h-4 w-4 text-blue-400" />
          <h3 className="text-sm font-medium text-blue-400">Perfil CNAE</h3>
        </div>
        {profile.cnae ? (
          <div className="space-y-2 text-xs">
            <KVRow label="Setor" value={profile.cnae.setor_economico} />
            <KVRow label="Cadeia" value={profile.cnae.cadeia_valor} />
            <KVRow label="Posição" value={profile.cnae.posicao_cadeia} />
            <KVRow label="CNAE" value={profile.cnae.cnae_principal} />
            {profile.cnae.total_empresas_mesmo_cnae_municipio != null && (
              <KVRow
                label="Concorrentes (cidade)"
                value={String(profile.cnae.total_empresas_mesmo_cnae_municipio)}
              />
            )}
            {profile.cnae.ranking_municipal != null && (
              <KVRow label="Ranking municipal" value={`#${profile.cnae.ranking_municipal}`} />
            )}
          </div>
        ) : (
          <p className="text-xs text-gray-500">Perfil CNAE não disponível</p>
        )}
      </div>

      {/* Tax Profile */}
      <div className="rounded-xl border border-purple-500/20 bg-[#0f1629]/60 p-4">
        <div className="flex items-center gap-2 mb-3">
          <Building2 className="h-4 w-4 text-purple-400" />
          <h3 className="text-sm font-medium text-purple-400">Perfil Tributário</h3>
        </div>
        {profile.tributario ? (
          <div className="space-y-2 text-xs">
            <KVRow label="Regime" value={profile.tributario.regime_tributario} />
            <KVRow label="Porte" value={profile.tributario.porte} />
            {profile.tributario.faturamento_estimado_min != null && (
              <KVRow
                label="Faturamento est."
                value={`${formatCurrency(profile.tributario.faturamento_estimado_min)} - ${formatCurrency(profile.tributario.faturamento_estimado_max || 0)}`}
              />
            )}
            <KVRow label="Perfil comprador" value={profile.tributario.perfil_comprador} />
            <KVRow label="Poder compra" value={profile.tributario.poder_compra_estimado} />
            {profile.tributario.score_saude_fiscal != null && (
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Saúde fiscal</span>
                <ScoreBar value={profile.tributario.score_saude_fiscal} />
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-gray-500">Perfil tributário não disponível</p>
        )}
      </div>

      {/* Geo Profile */}
      <div className="rounded-xl border border-green-500/20 bg-[#0f1629]/60 p-4">
        <div className="flex items-center gap-2 mb-3">
          <MapPin className="h-4 w-4 text-green-400" />
          <h3 className="text-sm font-medium text-green-400">Perfil Geográfico</h3>
        </div>
        {profile.geografico ? (
          <div className="space-y-2 text-xs">
            <KVRow label="Arco atuação" value={profile.geografico.arco_atuacao} />
            {profile.geografico.densidade_concorrentes != null && (
              <KVRow label="Concorrentes" value={String(profile.geografico.densidade_concorrentes)} />
            )}
            {profile.geografico.populacao_alcancavel != null && (
              <KVRow
                label="Pop. alcançável"
                value={formatNumber(profile.geografico.populacao_alcancavel)}
              />
            )}
            {profile.geografico.indice_saturacao != null && (
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Saturação</span>
                <ScoreBar value={profile.geografico.indice_saturacao} inverted />
              </div>
            )}
            {profile.geografico.oportunidades_geograficas?.cidades_oportunidade?.slice(0, 3).map((c) => (
              <div key={c.cidade} className="flex items-center justify-between text-gray-400">
                <span className="flex items-center gap-1">
                  <TrendingUp className="h-3 w-3 text-green-500" />
                  {c.cidade}
                </span>
                <span className="text-gray-500">{c.concorrentes_cnae} conc.</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-gray-500">Perfil geográfico não disponível</p>
        )}
      </div>
    </div>
  );
}

// ── Helpers ──

function KVRow({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-gray-500 whitespace-nowrap">{label}</span>
      <span className="text-gray-300 font-medium min-w-0 whitespace-nowrap overflow-hidden text-ellipsis text-right">
        {value}
      </span>
    </div>
  );
}

function ScoreBar({ value, inverted = false }: { value: number; inverted?: boolean }) {
  const pct = Math.round(value * 100);
  const color = inverted
    ? pct > 70 ? 'bg-red-500' : pct > 40 ? 'bg-yellow-500' : 'bg-green-500'
    : pct > 70 ? 'bg-green-500' : pct > 40 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-1.5">
      <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-gray-400 font-mono tabular-nums w-8 text-right">{pct}%</span>
    </div>
  );
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `R$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `R$${(value / 1_000).toFixed(0)}k`;
  return `R$${value}`;
}

function formatNumber(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}k`;
  return String(value);
}
