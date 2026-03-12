'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  Receipt,
  Search,
  ChevronDown,
  ChevronUp,
  ArrowLeft,
  Filter,
  X,
  DollarSign,
  Users,
  TrendingUp,
  FileText,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Percent,
  Building2,
  MapPin,
  Landmark,
  Zap,
  Handshake,
  UserCheck,
  Newspaper,
  ExternalLink,
  Tag,
} from 'lucide-react';
import {
  listEmendas,
  getEmendasAggregation,
  getEmendaContext,
  type Emenda,
  type EmendasAggregation,
  type EmendaContext,
} from '@/lib/api';
import { isAuthenticated } from '@/lib/auth';

// ============================================
// HELPERS
// ============================================

function formatCurrency(value: number | undefined | null): string {
  if (!value) return 'R$ 0';
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    notation: value >= 1_000_000 ? 'compact' : 'standard',
    maximumFractionDigits: value >= 1_000_000 ? 1 : 0,
  }).format(value);
}

function formatNumber(value: number | undefined | null): string {
  if (!value) return '0';
  return new Intl.NumberFormat('pt-BR').format(value);
}

function formatPercent(value: number | undefined | null): string {
  if (value == null) return '0%';
  return `${value}%`;
}

const BENEFICIARY_LABELS: Record<string, { label: string; color: string }> = {
  'Pessoa Jurídica': { label: 'Mercado (PJ)', color: 'cyan' },
  'Pessoa Juridica': { label: 'Mercado (PJ)', color: 'cyan' },
  'Pessoa Física': { label: 'Cidadao (PF)', color: 'emerald' },
  'Pessoa Fisica': { label: 'Cidadao (PF)', color: 'emerald' },
  'Unidade Gestora': { label: 'Governo (UG)', color: 'purple' },
  'Inscrição Genérica': { label: 'Inscr. Generica', color: 'slate' },
  'Inscricao Generica': { label: 'Inscr. Generica', color: 'slate' },
  'Inscrição Genéric': { label: 'Inscr. Generica', color: 'slate' },
  'Inscricao Generic': { label: 'Inscr. Generica', color: 'slate' },
  'Inválido': { label: 'Invalido', color: 'slate' },
  'Invalido': { label: 'Invalido', color: 'slate' },
  'Sem informação': { label: 'Sem Info', color: 'slate' },
  'Sem informacao': { label: 'Sem Info', color: 'slate' },
};

// ============================================
// MAIN PAGE
// ============================================

export default function EmendasPage() {
  const router = useRouter();
  const [authReady, setAuthReady] = useState(false);
  const [search, setSearch] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [funcaoFilter, setFuncaoFilter] = useState('');
  const [anoFilter, setAnoFilter] = useState('');
  const [tipoFilter, setTipoFilter] = useState('');
  const [localidadeFilter, setLocalidadeFilter] = useState('');
  const [sortColumn, setSortColumn] = useState<string>('');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/');
      return;
    }
    setAuthReady(true);
  }, [router]);

  // Data queries
  const aggQuery = useQuery({
    queryKey: ['emendas-aggregation'],
    queryFn: getEmendasAggregation,
    enabled: authReady,
    staleTime: 60_000,
  });

  const listQuery = useQuery({
    queryKey: ['emendas-list'],
    queryFn: () => listEmendas({ limit: 100 }),
    enabled: authReady,
    staleTime: 30_000,
  });

  const emendas = listQuery.data?.emendas || [];
  const agg = aggQuery.data;

  function handleSort(col: string) {
    if (sortColumn === col) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(col);
      setSortDirection('asc');
    }
  }

  // Filtered + sorted data
  const filteredData = useMemo(() => {
    let data = emendas;
    if (search) {
      const q = search.toLowerCase();
      data = data.filter(
        (e) =>
          e.autor?.toLowerCase().includes(q) ||
          e.funcao?.toLowerCase().includes(q) ||
          e.localidade?.toLowerCase().includes(q) ||
          e.tipo_emenda?.toLowerCase().includes(q)
      );
    }
    if (funcaoFilter) data = data.filter((e) => e.funcao === funcaoFilter);
    if (anoFilter) data = data.filter((e) => String(e.ano) === anoFilter);
    if (tipoFilter) data = data.filter((e) => e.tipo_emenda === tipoFilter);
    if (localidadeFilter) data = data.filter((e) => e.localidade === localidadeFilter);

    if (sortColumn) {
      const dir = sortDirection === 'asc' ? 1 : -1;
      data = [...data].sort((a, b) => {
        const av = a[sortColumn as keyof Emenda];
        const bv = b[sortColumn as keyof Emenda];
        if (av == null && bv == null) return 0;
        if (av == null) return 1;
        if (bv == null) return -1;
        if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir;
        return String(av).localeCompare(String(bv), 'pt-BR') * dir;
      });
    }

    return data;
  }, [emendas, search, funcaoFilter, anoFilter, tipoFilter, localidadeFilter, sortColumn, sortDirection]);

  // Unique values for filters
  const uniqueFuncoes = useMemo(() => [...new Set(emendas.map((e) => e.funcao).filter(Boolean))].sort(), [emendas]);
  const uniqueAnos = useMemo(() => [...new Set(emendas.map((e) => String(e.ano)).filter(Boolean))].sort().reverse(), [emendas]);
  const uniqueTipos = useMemo(() => [...new Set(emendas.map((e) => e.tipo_emenda).filter(Boolean))].sort(), [emendas]);
  const uniqueLocalidades = useMemo(() => [...new Set(emendas.map((e) => e.localidade).filter(Boolean))].sort(), [emendas]);

  const activeFilterCount = [funcaoFilter, anoFilter, tipoFilter, localidadeFilter].filter(Boolean).length;

  return (
    <div className="min-h-screen bg-[#0a0e1a]">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-[#0f1629]/80 backdrop-blur-xl border-b border-cyan-500/10">
        <div className="flex items-center justify-between px-4 lg:px-6 py-3 max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 text-slate-400 hover:text-cyan-400 transition-colors text-sm"
            >
              <ArrowLeft className="h-4 w-4" />
              Dashboard
            </Link>
            <div className="h-5 w-px bg-slate-700" />
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-cyan-500/10 flex items-center justify-center">
                <Receipt className="h-4 w-4 text-cyan-400" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-slate-200">Emendas Parlamentares</h1>
                {agg?.totals?.ano_min && agg?.totals?.ano_max && (
                  <span className="text-[10px] text-slate-500">
                    {agg.totals.ano_min}–{agg.totals.ano_max} | Federal
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 lg:px-6 py-6">
        {/* Row 1: Panorama Cards (4 primary metrics) */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <SummaryCard
            icon={FileText}
            label="Total Emendas"
            value={formatNumber(agg?.totals?.total_emendas)}
            color="cyan"
            loading={aggQuery.isLoading}
          />
          <SummaryCard
            icon={DollarSign}
            label="Empenhado"
            value={formatCurrency(agg?.totals?.valor_empenhado)}
            color="emerald"
            loading={aggQuery.isLoading}
          />
          <SummaryCard
            icon={TrendingUp}
            label="Pago"
            value={formatCurrency(agg?.totals?.valor_pago)}
            sub={agg?.totals?.taxa_execucao ? `${agg.totals.taxa_execucao}% executado` : undefined}
            subColor="emerald"
            color="blue"
            loading={aggQuery.isLoading}
          />
          <SummaryCard
            icon={Percent}
            label="Taxa de Execucao"
            value={formatPercent(agg?.totals?.taxa_execucao)}
            sub={agg?.totals?.valor_resto_a_pagar ? `${formatCurrency(agg.totals.valor_resto_a_pagar)} parado` : undefined}
            subColor="amber"
            color="amber"
            loading={aggQuery.isLoading}
          />
        </div>

        {/* Row 2: Secondary context cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <SummaryCard
            icon={Users}
            label="Autores Unicos"
            value={formatNumber(agg?.totals?.autores_unicos)}
            sub={agg?.totals?.ano_min && agg?.totals?.ano_max ? `${agg.totals.ano_max - agg.totals.ano_min + 1} anos de dados` : undefined}
            subColor="slate"
            color="purple"
            loading={aggQuery.isLoading}
          />
          <SummaryCard
            icon={Landmark}
            label="Liquidado"
            value={formatCurrency(agg?.totals?.valor_liquidado)}
            color="blue"
            loading={aggQuery.isLoading}
          />
          <SummaryCard
            icon={Zap}
            label="Emendas PIX"
            value={formatNumber(agg?.totals?.total_emendas_pix)}
            sub={agg?.mecanismos?.emendas_pix ? formatCurrency(agg.mecanismos.emendas_pix.valor_empenhado) : undefined}
            subColor="cyan"
            color="cyan"
            loading={aggQuery.isLoading}
          />
          <SummaryCard
            icon={Handshake}
            label="Convenios"
            value={formatNumber(agg?.mecanismos?.convenios?.count)}
            sub={agg?.mecanismos?.convenios ? formatCurrency(agg.mecanismos.convenios.valor_total) : undefined}
            subColor="emerald"
            color="emerald"
            loading={aggQuery.isLoading}
          />
        </div>

        {/* Row 3: Context Intelligence Cards */}
        {agg && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {/* Beneficiary Focus — "Pra quem vai o dinheiro?" */}
            <BeneficiaryCard items={agg.beneficiaries} loading={aggQuery.isLoading} />

            {/* Top Funções — "Onde mais se investe?" */}
            <ContextFacetCard
              title="Onde Investe"
              icon={Building2}
              items={(agg.top_funcoes || []).slice(0, 5).map((f) => ({
                label: f.funcao,
                primary: formatCurrency(f.valor_empenhado),
                secondary: `${f.taxa_execucao}% exec`,
                count: f.count,
              }))}
              color="cyan"
            />

            {/* Top Destinos — "Pra onde vai?" */}
            <ContextFacetCard
              title="Destino (UF)"
              icon={MapPin}
              items={(agg.top_destinos || []).slice(0, 5).map((d) => ({
                label: d.uf,
                primary: formatCurrency(d.valor_total),
                secondary: `${formatNumber(d.count)} repasses`,
                count: d.count,
              }))}
              color="emerald"
            />

            {/* Top Autores — "Quem mais direciona?" */}
            <ContextFacetCard
              title="Top Autores"
              icon={UserCheck}
              items={(agg.top_autores || []).slice(0, 5).map((a) => ({
                label: a.autor,
                primary: formatCurrency(a.valor_empenhado),
                secondary: `${a.taxa_execucao}% exec`,
                count: a.count,
              }))}
              color="purple"
            />
          </div>
        )}

        {/* Search + Filters */}
        <div className="mb-4">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="text"
                placeholder="Buscar por autor, funcao, localidade..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full h-10 pl-10 pr-4 bg-[#0f1629] border border-slate-700/50 rounded-lg text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500/50"
              />
            </div>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`inline-flex items-center gap-2 h-10 px-4 rounded-lg border text-sm font-medium transition-colors ${
                showFilters || activeFilterCount > 0
                  ? 'bg-cyan-500/15 border-cyan-500/50 text-cyan-400'
                  : 'bg-[#0f1629] border-slate-700/50 text-slate-400 hover:border-cyan-500/30'
              }`}
            >
              <Filter className="h-4 w-4" />
              Filtros
              {activeFilterCount > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-[10px] bg-cyan-500/20 text-cyan-300 rounded-full">
                  {activeFilterCount}
                </span>
              )}
            </button>
          </div>

          {showFilters && (
            <div className="mt-3 p-4 bg-[#0f1629]/80 border border-slate-700/30 rounded-lg">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <FilterSelect label="Funcao" value={funcaoFilter} onChange={setFuncaoFilter} options={uniqueFuncoes as string[]} />
                <FilterSelect label="Ano" value={anoFilter} onChange={setAnoFilter} options={uniqueAnos as string[]} />
                <FilterSelect label="Tipo" value={tipoFilter} onChange={setTipoFilter} options={uniqueTipos as string[]} />
                <FilterSelect label="Localidade" value={localidadeFilter} onChange={setLocalidadeFilter} options={uniqueLocalidades as string[]} />
              </div>
              {activeFilterCount > 0 && (
                <button
                  onClick={() => { setFuncaoFilter(''); setAnoFilter(''); setTipoFilter(''); setLocalidadeFilter(''); }}
                  className="mt-3 inline-flex items-center gap-1 text-xs text-slate-400 hover:text-cyan-400"
                >
                  <X className="h-3 w-3" /> Limpar filtros
                </button>
              )}
            </div>
          )}
        </div>

        {/* Results count */}
        <div className="mb-3 text-xs text-slate-500">
          {filteredData.length} emenda{filteredData.length !== 1 ? 's' : ''} encontrada{filteredData.length !== 1 ? 's' : ''}
        </div>

        {/* Table */}
        <div className="rounded-xl border border-slate-700/30 bg-[#0f1629]/60 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/30">
                  <SortableHeader label="Autor" column="autor" current={sortColumn} direction={sortDirection} onSort={handleSort} />
                  <SortableHeader label="Funcao" column="funcao" current={sortColumn} direction={sortDirection} onSort={handleSort} />
                  <SortableHeader label="Localidade" column="localidade" current={sortColumn} direction={sortDirection} onSort={handleSort} />
                  <SortableHeader label="Tipo" column="tipo_emenda" current={sortColumn} direction={sortDirection} onSort={handleSort} />
                  <SortableHeader label="Empenhado" column="valor_empenhado" current={sortColumn} direction={sortDirection} onSort={handleSort} align="right" />
                  <SortableHeader label="Pago" column="valor_pago" current={sortColumn} direction={sortDirection} onSort={handleSort} align="right" />
                  <SortableHeader label="Ano" column="ano" current={sortColumn} direction={sortDirection} onSort={handleSort} align="center" />
                  <th className="w-10" />
                </tr>
              </thead>
              <tbody>
                {listQuery.isLoading ? (
                  <tr>
                    <td colSpan={8} className="text-center py-12 text-slate-500">
                      <div className="inline-flex items-center gap-2">
                        <div className="h-4 w-4 border-2 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
                        Carregando emendas...
                      </div>
                    </td>
                  </tr>
                ) : filteredData.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-12 text-slate-500">
                      Nenhuma emenda encontrada
                    </td>
                  </tr>
                ) : (
                  filteredData.map((emenda) => (
                    <EmendaRow key={emenda.id} emenda={emenda} />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}

// ============================================
// EMENDA ROW (Expandable)
// ============================================

function EmendaRow({ emenda }: { emenda: Emenda }) {
  const [expanded, setExpanded] = useState(false);

  // Lazy-load context only when expanded
  const contextQuery = useQuery({
    queryKey: ['emenda-context', emenda.id],
    queryFn: () => getEmendaContext(emenda.id),
    enabled: expanded,
    staleTime: 120_000,
  });

  const ctx = contextQuery.data;

  return (
    <>
      <tr
        onClick={() => setExpanded(!expanded)}
        className="border-b border-slate-700/20 hover:bg-cyan-500/5 cursor-pointer transition-colors"
      >
        <td className="px-4 py-3 text-slate-200 font-medium">
          <div className="min-w-0 max-w-[200px] truncate">{emenda.autor || '-'}</div>
        </td>
        <td className="px-4 py-3">
          {emenda.funcao ? (
            <span className="inline-flex px-2 py-0.5 text-xs bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 rounded-full truncate max-w-[150px]">
              {emenda.funcao}
            </span>
          ) : (
            <span className="text-slate-600">-</span>
          )}
        </td>
        <td className="px-4 py-3 text-slate-300">
          <div className="min-w-0 max-w-[150px] truncate">{emenda.localidade || '-'}</div>
        </td>
        <td className="px-4 py-3">
          {emenda.tipo_emenda ? (
            <span className="inline-flex px-2 py-0.5 text-xs bg-purple-500/10 text-purple-300 border border-purple-500/20 rounded-full truncate max-w-[120px]">
              {emenda.tipo_emenda}
            </span>
          ) : (
            <span className="text-slate-600">-</span>
          )}
        </td>
        <td className="px-4 py-3 text-right text-slate-200 font-mono text-xs tabular-nums">
          {formatCurrency(emenda.valor_empenhado)}
        </td>
        <td className="px-4 py-3 text-right text-emerald-400 font-mono text-xs tabular-nums">
          {formatCurrency(emenda.valor_pago)}
        </td>
        <td className="px-4 py-3 text-center text-slate-400 text-xs tabular-nums">
          {emenda.ano || '-'}
        </td>
        <td className="px-4 py-3">
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-slate-500" />
          ) : (
            <ChevronDown className="h-4 w-4 text-slate-500" />
          )}
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={8} className="px-4 py-4 bg-[#0a0e1a]/60">
            <div className="flex flex-col lg:flex-row gap-4">
              {/* Left: Emenda details */}
              <div className="flex-1">
                {/* Taxonomy badge */}
                {ctx?.taxonomia && (
                  <div className="mb-3">
                    <span
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full border"
                      style={{
                        borderColor: `${ctx.taxonomia.cor}33`,
                        backgroundColor: `${ctx.taxonomia.cor}15`,
                        color: ctx.taxonomia.cor,
                      }}
                    >
                      <Tag className="h-3 w-3" />
                      {ctx.taxonomia.nome}
                    </span>
                  </div>
                )}

                <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
                  <InfoPair label="Codigo Emenda" value={emenda.codigo_emenda} />
                  <InfoPair label="Numero" value={emenda.numero_emenda} />
                  <InfoPair label="Ano" value={String(emenda.ano)} />
                  <InfoPair label="Subfuncao" value={emenda.subfuncao} />
                  <InfoPair label="Codigo IBGE" value={emenda.codigo_ibge ? String(emenda.codigo_ibge) : undefined} />
                  <InfoPair label="Partido" value={emenda.partido} />
                </div>
                {/* Financial Cards */}
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
                  <FinancialCard label="Empenhado" value={emenda.valor_empenhado} color="cyan" />
                  <FinancialCard label="Liquidado" value={emenda.valor_liquidado} color="blue" />
                  <FinancialCard label="Pago" value={emenda.valor_pago} color="emerald" />
                  <FinancialCard label="Resto Inscrito" value={emenda.valor_resto_inscrito} color="amber" />
                  <FinancialCard label="Resto Cancelado" value={emenda.valor_resto_cancelado} color="red" />
                  <FinancialCard label="Resto Pago" value={emenda.valor_resto_pago} color="purple" />
                </div>
              </div>

              {/* Right: Context panel — related news */}
              <div className="w-full lg:w-80 flex-shrink-0">
                <div className="rounded-xl border border-slate-700/30 bg-[#0f1629]/40 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Newspaper className="h-4 w-4 text-cyan-400" />
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
                      Noticias Relacionadas
                    </h4>
                  </div>

                  {contextQuery.isLoading ? (
                    <div className="space-y-2">
                      {[1, 2, 3].map((i) => (
                        <div key={i} className="h-12 bg-slate-700/20 rounded animate-pulse" />
                      ))}
                    </div>
                  ) : ctx?.noticias && ctx.noticias.length > 0 ? (
                    <div className="space-y-2.5">
                      {ctx.noticias.map((noticia) => (
                        <div
                          key={noticia.id}
                          className="p-2.5 rounded-lg border border-slate-700/20 hover:border-cyan-500/20 transition-colors"
                        >
                          <div className="text-xs text-slate-200 font-medium line-clamp-2 mb-1">
                            {noticia.titulo}
                          </div>
                          <div className="flex items-center gap-2 text-[10px] text-slate-500">
                            <span className="truncate min-w-0">{noticia.fonte_nome || 'Fonte'}</span>
                            {noticia.data_publicacao && (
                              <>
                                <span>·</span>
                                <span className="flex-shrink-0">
                                  {new Date(noticia.data_publicacao).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })}
                                </span>
                              </>
                            )}
                            {noticia.url && (
                              <a
                                href={noticia.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                className="flex-shrink-0 text-cyan-500 hover:text-cyan-400"
                              >
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-slate-600 py-4 text-center">
                      Nenhuma noticia relacionada encontrada
                    </div>
                  )}

                  {ctx?.associations_count != null && ctx.associations_count > 0 && (
                    <div className="mt-3 pt-2 border-t border-slate-700/20 text-[10px] text-slate-500">
                      {ctx.associations_count} associacao{ctx.associations_count !== 1 ? 'es' : ''} por tema
                    </div>
                  )}
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ============================================
// BENEFICIARY FOCUS CARD
// ============================================

function BeneficiaryCard({ items, loading }: { items: EmendasAggregation['beneficiaries']; loading: boolean }) {
  if (loading) {
    return (
      <div className="rounded-xl border border-amber-500/15 bg-[#0f1629]/60 p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider mb-3 text-amber-400">
          Foco do Beneficiario
        </h3>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-8 bg-slate-700/20 rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-amber-500/15 bg-[#0f1629]/60 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider mb-3 text-amber-400">
        Pra Quem Vai?
      </h3>
      <div className="space-y-2.5">
        {(items || []).map((item) => {
          const meta = BENEFICIARY_LABELS[item.tipo_favorecido] || { label: item.tipo_favorecido, color: 'slate' };
          return (
            <div key={item.tipo_favorecido}>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-slate-300 font-medium min-w-0 truncate">{meta.label}</span>
                <span className="text-slate-400 tabular-nums flex-shrink-0 ml-2">{item.percentual}%</span>
              </div>
              <div className="w-full h-1.5 bg-slate-700/30 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    meta.color === 'cyan' ? 'bg-cyan-500' :
                    meta.color === 'emerald' ? 'bg-emerald-500' :
                    meta.color === 'purple' ? 'bg-purple-500' :
                    'bg-slate-500'
                  }`}
                  style={{ width: `${Math.min(item.percentual, 100)}%` }}
                />
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5 tabular-nums">
                {formatCurrency(item.valor_total)} | {formatNumber(item.count)} registros
              </div>
            </div>
          );
        })}
        {(!items || items.length === 0) && (
          <div className="text-slate-600 text-xs">Sem dados de favorecidos</div>
        )}
      </div>
    </div>
  );
}

// ============================================
// CONTEXT FACET CARD
// ============================================

function ContextFacetCard({
  title,
  icon: Icon,
  items,
  color,
}: {
  title: string;
  icon: typeof Receipt;
  items: Array<{ label: string; primary: string; secondary: string; count: number }>;
  color: 'cyan' | 'emerald' | 'purple';
}) {
  const borderColor = {
    cyan: 'border-cyan-500/15',
    emerald: 'border-emerald-500/15',
    purple: 'border-purple-500/15',
  };
  const titleColor = {
    cyan: 'text-cyan-400',
    emerald: 'text-emerald-400',
    purple: 'text-purple-400',
  };
  const iconBg = {
    cyan: 'bg-cyan-500/10 text-cyan-400',
    emerald: 'bg-emerald-500/10 text-emerald-400',
    purple: 'bg-purple-500/10 text-purple-400',
  };

  return (
    <div className={`rounded-xl border bg-[#0f1629]/60 p-4 ${borderColor[color]}`}>
      <div className="flex items-center gap-2 mb-3">
        <div className={`w-5 h-5 rounded flex items-center justify-center ${iconBg[color]}`}>
          <Icon className="h-3 w-3" />
        </div>
        <h3 className={`text-xs font-semibold uppercase tracking-wider ${titleColor[color]}`}>
          {title}
        </h3>
      </div>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="flex items-center justify-between text-xs gap-2">
            <span className="text-slate-300 truncate min-w-0 flex-1">{item.label || '-'}</span>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="text-slate-400 tabular-nums">{item.primary}</span>
              <span className="text-slate-600 tabular-nums text-[10px]">{item.secondary}</span>
            </div>
          </div>
        ))}
        {items.length === 0 && <div className="text-slate-600 text-xs">Sem dados</div>}
      </div>
    </div>
  );
}

// ============================================
// SUB-COMPONENTS
// ============================================

function SummaryCard({
  icon: Icon,
  label,
  value,
  sub,
  subColor,
  color,
  loading,
}: {
  icon: typeof Receipt;
  label: string;
  value: string;
  sub?: string;
  subColor?: string;
  color: 'cyan' | 'emerald' | 'blue' | 'purple' | 'amber';
  loading: boolean;
}) {
  const colorMap = {
    cyan: 'border-cyan-500/20 text-cyan-400 bg-cyan-500/5',
    emerald: 'border-emerald-500/20 text-emerald-400 bg-emerald-500/5',
    blue: 'border-blue-500/20 text-blue-400 bg-blue-500/5',
    purple: 'border-purple-500/20 text-purple-400 bg-purple-500/5',
    amber: 'border-amber-500/20 text-amber-400 bg-amber-500/5',
  };
  const iconColor = {
    cyan: 'bg-cyan-500/10 text-cyan-400',
    emerald: 'bg-emerald-500/10 text-emerald-400',
    blue: 'bg-blue-500/10 text-blue-400',
    purple: 'bg-purple-500/10 text-purple-400',
    amber: 'bg-amber-500/10 text-amber-400',
  };
  const subColorMap: Record<string, string> = {
    emerald: 'text-emerald-400/70',
    amber: 'text-amber-400/70',
    cyan: 'text-cyan-400/70',
    slate: 'text-slate-500',
  };

  return (
    <div className={`rounded-xl border p-4 ${colorMap[color]}`}>
      <div className="flex items-center gap-2 mb-2">
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${iconColor[color]}`}>
          <Icon className="h-3.5 w-3.5" />
        </div>
        <span className="text-xs text-slate-400 font-medium min-w-0 truncate">{label}</span>
      </div>
      {loading ? (
        <div className="h-6 w-24 bg-slate-700/30 rounded animate-pulse" />
      ) : (
        <>
          <div className="text-lg font-bold text-slate-200 tabular-nums truncate">{value}</div>
          {sub && (
            <div className={`text-[10px] mt-0.5 tabular-nums ${subColorMap[subColor || 'slate']}`}>
              {sub}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <div>
      <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-9 px-3 bg-[#0a0e1a] border border-slate-700/50 rounded-lg text-xs text-slate-300 focus:outline-none focus:border-cyan-500/50"
      >
        <option value="">Todos</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </div>
  );
}

function InfoPair({ label, value }: { label: string; value?: string }) {
  return (
    <div>
      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>
      <div className="text-xs text-slate-300 mt-0.5 truncate">{value || '-'}</div>
    </div>
  );
}

function SortableHeader({
  label,
  column,
  current,
  direction,
  onSort,
  align = 'left',
}: {
  label: string;
  column: string;
  current: string;
  direction: 'asc' | 'desc';
  onSort: (col: string) => void;
  align?: 'left' | 'right' | 'center';
}) {
  const active = current === column;
  const alignClass = align === 'right' ? 'text-right justify-end' : align === 'center' ? 'text-center justify-center' : 'text-left';

  return (
    <th
      onClick={() => onSort(column)}
      className={`px-4 py-3 text-xs font-semibold uppercase tracking-wider cursor-pointer select-none transition-colors hover:text-cyan-400 ${
        active ? 'text-cyan-400' : 'text-slate-400'
      } ${alignClass}`}
    >
      <div className={`inline-flex items-center gap-1 ${align === 'right' ? 'flex-row-reverse' : ''}`}>
        {label}
        {active ? (
          direction === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
        ) : (
          <ArrowUpDown className="h-3 w-3 opacity-30" />
        )}
      </div>
    </th>
  );
}

function FinancialCard({
  label,
  value,
  color,
}: {
  label: string;
  value?: number;
  color: 'cyan' | 'blue' | 'emerald' | 'amber' | 'red' | 'purple';
}) {
  const colorMap = {
    cyan: 'border-cyan-500/20 bg-cyan-500/5',
    blue: 'border-blue-500/20 bg-blue-500/5',
    emerald: 'border-emerald-500/20 bg-emerald-500/5',
    amber: 'border-amber-500/20 bg-amber-500/5',
    red: 'border-red-500/20 bg-red-500/5',
    purple: 'border-purple-500/20 bg-purple-500/5',
  };
  const textColor = {
    cyan: 'text-cyan-400',
    blue: 'text-blue-400',
    emerald: 'text-emerald-400',
    amber: 'text-amber-400',
    red: 'text-red-400',
    purple: 'text-purple-400',
  };

  return (
    <div className={`rounded-lg border p-3 ${colorMap[color]}`}>
      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>
      <div className={`text-sm font-bold mt-1 tabular-nums ${textColor[color]}`}>
        {formatCurrency(value)}
      </div>
    </div>
  );
}
