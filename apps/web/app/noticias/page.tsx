'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  Newspaper,
  Search,
  ChevronDown,
  ChevronUp,
  ArrowLeft,
  Filter,
  X,
  Clock,
  Globe,
  Tag,
  ExternalLink,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Shield,
  ShieldCheck,
  ShieldAlert,
  Layers,
} from 'lucide-react';
import {
  listNews,
  getNewsAggregation,
  type NewsItem,
  type NewsAggregation,
} from '@/lib/api';
import { isAuthenticated } from '@/lib/auth';

// ============================================
// HELPERS
// ============================================

function formatDate(dateStr: string | undefined | null): string {
  if (!dateStr) return '-';
  try {
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(new Date(dateStr));
  } catch {
    return dateStr;
  }
}

function formatNumber(value: number | undefined | null): string {
  if (!value) return '0';
  return new Intl.NumberFormat('pt-BR').format(value);
}

function truncateText(text: string | undefined, maxLen: number): string {
  if (!text) return '';
  return text.length > maxLen ? text.substring(0, maxLen) + '...' : text;
}

// ============================================
// MAIN PAGE
// ============================================

export default function NoticiasPage() {
  const router = useRouter();
  const [authReady, setAuthReady] = useState(false);
  const [search, setSearch] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [fonteFilter, setFonteFilter] = useState('');
  const [tipoFilter, setTipoFilter] = useState('');
  const [temaFilter, setTemaFilter] = useState('');
  const [classificacaoFilter, setClassificacaoFilter] = useState('');
  const [sortColumn, setSortColumn] = useState<string>('');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/');
      return;
    }
    setAuthReady(true);
  }, [router]);

  // Data queries
  const aggQuery = useQuery({
    queryKey: ['news-aggregation'],
    queryFn: getNewsAggregation,
    enabled: authReady,
    staleTime: 60_000,
  });

  const listQuery = useQuery({
    queryKey: ['news-list'],
    queryFn: () => listNews({ limit: 100 }),
    enabled: authReady,
    staleTime: 30_000,
  });

  const news = listQuery.data?.news || [];
  const agg = aggQuery.data;

  function handleSort(col: string) {
    if (sortColumn === col) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(col);
      setSortDirection(col === 'data_publicacao' ? 'desc' : 'asc');
    }
  }

  // Filtered + sorted data
  const filteredData = useMemo(() => {
    let data = news;
    if (search) {
      const q = search.toLowerCase();
      data = data.filter(
        (n) =>
          n.titulo?.toLowerCase().includes(q) ||
          n.resumo?.toLowerCase().includes(q) ||
          n.fonte_nome?.toLowerCase().includes(q)
      );
    }
    if (fonteFilter) data = data.filter((n) => (n.fonte_nome || n.fonte) === fonteFilter);
    if (tipoFilter) data = data.filter((n) => n.tipo === tipoFilter);
    if (temaFilter) data = data.filter((n) => n.tema_principal === temaFilter);
    if (classificacaoFilter) data = data.filter((n) => n.tipo_classificacao === classificacaoFilter);

    if (sortColumn) {
      const dir = sortDirection === 'asc' ? 1 : -1;
      data = [...data].sort((a, b) => {
        let av: string | undefined;
        let bv: string | undefined;
        if (sortColumn === 'fonte') {
          av = a.fonte_nome || a.fonte;
          bv = b.fonte_nome || b.fonte;
        } else if (sortColumn === 'data_publicacao') {
          av = a.data_publicacao || a.data;
          bv = b.data_publicacao || b.data;
        } else {
          av = a[sortColumn as keyof NewsItem] as string | undefined;
          bv = b[sortColumn as keyof NewsItem] as string | undefined;
        }
        if (av == null && bv == null) return 0;
        if (av == null) return 1;
        if (bv == null) return -1;
        return String(av).localeCompare(String(bv), 'pt-BR') * dir;
      });
    }

    return data;
  }, [news, search, fonteFilter, tipoFilter, temaFilter, classificacaoFilter, sortColumn, sortDirection]);

  // Unique values for filters
  const uniqueFontes = useMemo(
    () => [...new Set(news.map((n) => n.fonte_nome || n.fonte).filter(Boolean))].sort(),
    [news]
  );
  const uniqueTipos = useMemo(
    () => [...new Set(news.map((n) => n.tipo).filter(Boolean))].sort(),
    [news]
  );
  const uniqueTemas = useMemo(
    () => [...new Set(news.map((n) => n.tema_principal).filter(Boolean))].sort(),
    [news]
  );
  const uniqueClassificacoes = useMemo(
    () => [...new Set(news.map((n) => n.tipo_classificacao).filter(Boolean))].sort(),
    [news]
  );

  const activeFilterCount = [fonteFilter, tipoFilter, temaFilter, classificacaoFilter].filter(Boolean).length;

  return (
    <div className="min-h-screen bg-[#0a0e1a]">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-[#0f1629]/80 backdrop-blur-xl border-b border-green-500/10">
        <div className="flex items-center justify-between px-4 lg:px-6 py-3 max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 text-slate-400 hover:text-green-400 transition-colors text-sm"
            >
              <ArrowLeft className="h-4 w-4" />
              Dashboard
            </Link>
            <div className="h-5 w-px bg-slate-700" />
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-green-500/10 flex items-center justify-center">
                <Newspaper className="h-4 w-4 text-green-400" />
              </div>
              <h1 className="text-lg font-bold text-slate-200">Notícias</h1>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 lg:px-6 py-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <SummaryCard
            icon={Newspaper}
            label="Total Notícias"
            value={formatNumber(agg?.totals?.total_noticias)}
            color="green"
            loading={aggQuery.isLoading}
          />
          <SummaryCard
            icon={Clock}
            label="Últimos 7 dias"
            value={formatNumber(agg?.totals?.ultimos_7_dias)}
            color="emerald"
            loading={aggQuery.isLoading}
          />
          <SummaryCard
            icon={Globe}
            label="Fontes"
            value={formatNumber(agg?.by_fonte?.length)}
            color="blue"
            loading={aggQuery.isLoading}
          />
          <SummaryCard
            icon={Tag}
            label="Temas"
            value={formatNumber(agg?.by_tema?.length)}
            color="purple"
            loading={aggQuery.isLoading}
          />
        </div>

        {/* Credibility Meter */}
        {agg?.credibilidade && (
          <div className="mb-6 rounded-xl border border-slate-700/30 bg-[#0f1629]/60 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
              <Shield className="h-3.5 w-3.5" /> Credibilidade das Fontes
            </h3>
            <div className="flex items-center gap-4">
              <CredibilityBar label="Alta" icon={ShieldCheck} value={agg.credibilidade.alta} total={agg.totals.total_noticias} color="emerald" />
              <CredibilityBar label="Média" icon={Shield} value={agg.credibilidade.media} total={agg.totals.total_noticias} color="amber" />
              <CredibilityBar label="Baixa" icon={ShieldAlert} value={agg.credibilidade.baixa} total={agg.totals.total_noticias} color="red" />
            </div>
          </div>
        )}

        {/* Top Facets Row */}
        {agg && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <FacetCard
              title="Por Segmento"
              items={agg.by_segmento.slice(0, 5).map((s) => ({ label: s.segmento, count: s.count }))}
              color="green"
            />
            <FacetCard
              title="Por Fonte"
              items={agg.by_fonte.slice(0, 5).map((f) => ({ label: f.fonte, count: f.count }))}
              color="blue"
            />
            <FacetCard
              title="Por Tema"
              items={(agg.by_tema || []).slice(0, 5).map((t) => ({ label: t.tema, count: t.count }))}
              color="purple"
            />
            <FacetCard
              title="Por Classificação"
              items={(agg.by_classificacao || []).slice(0, 5).map((c) => ({ label: c.tipo, count: c.count }))}
              color="amber"
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
                placeholder="Buscar por título, resumo, fonte..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full h-10 pl-10 pr-4 bg-[#0f1629] border border-slate-700/50 rounded-lg text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-green-500/50"
              />
            </div>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`inline-flex items-center gap-2 h-10 px-4 rounded-lg border text-sm font-medium transition-colors ${
                showFilters || activeFilterCount > 0
                  ? 'bg-green-500/15 border-green-500/50 text-green-400'
                  : 'bg-[#0f1629] border-slate-700/50 text-slate-400 hover:border-green-500/30'
              }`}
            >
              <Filter className="h-4 w-4" />
              Filtros
              {activeFilterCount > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-[10px] bg-green-500/20 text-green-300 rounded-full">
                  {activeFilterCount}
                </span>
              )}
            </button>
          </div>

          {showFilters && (
            <div className="mt-3 p-4 bg-[#0f1629]/80 border border-slate-700/30 rounded-lg">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <FilterSelect label="Fonte" value={fonteFilter} onChange={setFonteFilter} options={uniqueFontes as string[]} />
                <FilterSelect label="Tipo" value={tipoFilter} onChange={setTipoFilter} options={uniqueTipos as string[]} />
                <FilterSelect label="Tema" value={temaFilter} onChange={setTemaFilter} options={uniqueTemas as string[]} />
                <FilterSelect label="Classificação" value={classificacaoFilter} onChange={setClassificacaoFilter} options={uniqueClassificacoes as string[]} />
              </div>
              {activeFilterCount > 0 && (
                <button
                  onClick={() => { setFonteFilter(''); setTipoFilter(''); setTemaFilter(''); setClassificacaoFilter(''); }}
                  className="mt-3 inline-flex items-center gap-1 text-xs text-slate-400 hover:text-green-400"
                >
                  <X className="h-3 w-3" /> Limpar filtros
                </button>
              )}
            </div>
          )}
        </div>

        {/* Results count */}
        <div className="mb-3 text-xs text-slate-500">
          {filteredData.length} notícia{filteredData.length !== 1 ? 's' : ''} encontrada{filteredData.length !== 1 ? 's' : ''}
        </div>

        {/* Table */}
        <div className="rounded-xl border border-slate-700/30 bg-[#0f1629]/60 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/30">
                  <SortableHeader label="Título" column="titulo" current={sortColumn} direction={sortDirection} onSort={handleSort} color="green" />
                  <SortableHeader label="Fonte" column="fonte" current={sortColumn} direction={sortDirection} onSort={handleSort} color="green" />
                  <SortableHeader label="Tema" column="tema_principal" current={sortColumn} direction={sortDirection} onSort={handleSort} color="green" />
                  <SortableHeader label="Cred." column="credibilidade_score" current={sortColumn} direction={sortDirection} onSort={handleSort} align="center" color="green" />
                  <SortableHeader label="Data" column="data_publicacao" current={sortColumn} direction={sortDirection} onSort={handleSort} color="green" />
                  <th className="w-10" />
                </tr>
              </thead>
              <tbody>
                {listQuery.isLoading ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-slate-500">
                      <div className="inline-flex items-center gap-2">
                        <div className="h-4 w-4 border-2 border-green-500/30 border-t-green-500 rounded-full animate-spin" />
                        Carregando notícias...
                      </div>
                    </td>
                  </tr>
                ) : filteredData.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-slate-500">
                      Nenhuma notícia encontrada
                    </td>
                  </tr>
                ) : (
                  filteredData.map((item) => (
                    <NewsRow key={item.id} item={item} />
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
// NEWS ROW (Expandable)
// ============================================

function NewsRow({ item }: { item: NewsItem }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        onClick={() => setExpanded(!expanded)}
        className="border-b border-slate-700/20 hover:bg-green-500/5 cursor-pointer transition-colors"
      >
        <td className="px-4 py-3 text-slate-200 font-medium">
          <div className="min-w-0 max-w-[350px] truncate">{item.titulo || '-'}</div>
        </td>
        <td className="px-4 py-3">
          {(item.fonte_nome || item.fonte) ? (
            <span className="inline-flex px-2 py-0.5 text-xs bg-green-500/10 text-green-300 border border-green-500/20 rounded-full truncate max-w-[150px]">
              {item.fonte_nome || item.fonte}
            </span>
          ) : (
            <span className="text-slate-600">-</span>
          )}
        </td>
        <td className="px-4 py-3">
          {item.tema_principal ? (
            <span className="inline-flex px-2 py-0.5 text-xs bg-purple-500/10 text-purple-300 border border-purple-500/20 rounded-full truncate max-w-[120px]">
              {item.tema_principal}
            </span>
          ) : (
            <span className="text-slate-600">-</span>
          )}
        </td>
        <td className="px-4 py-3 text-center">
          <CredibilityBadge score={item.credibilidade_score} />
        </td>
        <td className="px-4 py-3 text-slate-400 text-xs whitespace-nowrap">
          {formatDate(item.data_publicacao || item.data)}
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
          <td colSpan={6} className="px-4 py-4 bg-[#0a0e1a]/60">
            <div className="space-y-3">
              {/* Resumo */}
              {item.resumo && (
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Resumo</span>
                  <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                    {truncateText(item.resumo, 500)}
                  </p>
                </div>
              )}

              {/* Meta info */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <InfoPair label="Fonte" value={item.fonte_nome || item.fonte} />
                <InfoPair label="Segmento" value={item.segmento} />
                <InfoPair label="Classificação" value={item.tipo_classificacao} />
                <InfoPair label="Relevância" value={item.relevancia_geral ? `${item.relevancia_geral}/100` : item.relevancia} />
                <InfoPair label="Tema" value={item.tema_principal} />
                <InfoPair label="Credibilidade" value={item.credibilidade_score ? `${item.credibilidade_score}` : undefined} />
                <InfoPair label="Tipo" value={item.tipo} />
                <InfoPair label="Data" value={formatDate(item.data_publicacao || item.data)} />
              </div>

              {/* Link */}
              {item.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-green-400 hover:text-green-300 transition-colors"
                >
                  <ExternalLink className="h-3 w-3" />
                  Abrir notícia original
                </a>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ============================================
// SUB-COMPONENTS
// ============================================

function SortableHeader({
  label,
  column,
  current,
  direction,
  onSort,
  align = 'left',
  color = 'green',
}: {
  label: string;
  column: string;
  current: string;
  direction: 'asc' | 'desc';
  onSort: (col: string) => void;
  align?: 'left' | 'right' | 'center';
  color?: 'green' | 'cyan';
}) {
  const active = current === column;
  const activeColor = color === 'green' ? 'text-green-400' : 'text-cyan-400';
  const hoverColor = color === 'green' ? 'hover:text-green-400' : 'hover:text-cyan-400';
  const alignClass = align === 'right' ? 'text-right justify-end' : align === 'center' ? 'text-center justify-center' : 'text-left';

  return (
    <th
      onClick={() => onSort(column)}
      className={`px-4 py-3 text-xs font-semibold uppercase tracking-wider cursor-pointer select-none transition-colors ${hoverColor} ${
        active ? activeColor : 'text-slate-400'
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

function SummaryCard({
  icon: Icon,
  label,
  value,
  color,
  loading,
}: {
  icon: typeof Newspaper;
  label: string;
  value: string;
  color: 'green' | 'emerald' | 'blue' | 'purple';
  loading: boolean;
}) {
  const colorMap = {
    green: 'border-green-500/20 text-green-400 bg-green-500/5',
    emerald: 'border-emerald-500/20 text-emerald-400 bg-emerald-500/5',
    blue: 'border-blue-500/20 text-blue-400 bg-blue-500/5',
    purple: 'border-purple-500/20 text-purple-400 bg-purple-500/5',
  };
  const iconColor = {
    green: 'bg-green-500/10 text-green-400',
    emerald: 'bg-emerald-500/10 text-emerald-400',
    blue: 'bg-blue-500/10 text-blue-400',
    purple: 'bg-purple-500/10 text-purple-400',
  };

  return (
    <div className={`rounded-xl border p-4 ${colorMap[color]}`}>
      <div className="flex items-center gap-2 mb-2">
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${iconColor[color]}`}>
          <Icon className="h-3.5 w-3.5" />
        </div>
        <span className="text-xs text-slate-400 font-medium">{label}</span>
      </div>
      {loading ? (
        <div className="h-6 w-24 bg-slate-700/30 rounded animate-pulse" />
      ) : (
        <div className="text-lg font-bold text-slate-200 tabular-nums truncate">{value}</div>
      )}
    </div>
  );
}

function CredibilityBadge({ score }: { score?: number }) {
  if (score == null) return <span className="text-slate-600 text-xs">-</span>;
  const s = Number(score);
  if (s >= 0.8) {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 rounded-full" title={`Score: ${s}`}>
        <ShieldCheck className="h-3 w-3" /> {s}
      </span>
    );
  }
  if (s >= 0.5) {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-semibold bg-amber-500/15 text-amber-400 rounded-full" title={`Score: ${s}`}>
        <Shield className="h-3 w-3" /> {s}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-semibold bg-red-500/15 text-red-400 rounded-full" title={`Score: ${s}`}>
      <ShieldAlert className="h-3 w-3" /> {s}
    </span>
  );
}

function CredibilityBar({
  label,
  icon: Icon,
  value,
  total,
  color,
}: {
  label: string;
  icon: typeof Shield;
  value: number;
  total: number;
  color: 'emerald' | 'amber' | 'red';
}) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  const barColor = {
    emerald: 'bg-emerald-500',
    amber: 'bg-amber-500',
    red: 'bg-red-500',
  };
  const textColor = {
    emerald: 'text-emerald-400',
    amber: 'text-amber-400',
    red: 'text-red-400',
  };

  return (
    <div className="flex-1">
      <div className="flex items-center justify-between mb-1">
        <span className={`inline-flex items-center gap-1 text-xs font-medium ${textColor[color]}`}>
          <Icon className="h-3 w-3" /> {label}
        </span>
        <span className="text-xs text-slate-400 tabular-nums">{formatNumber(value)} ({pct}%)</span>
      </div>
      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${barColor[color]}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function FacetCard({
  title,
  items,
  color,
}: {
  title: string;
  items: Array<{ label: string; count: number }>;
  color: 'green' | 'blue' | 'purple' | 'amber';
}) {
  const borderColor: Record<string, string> = { green: 'border-green-500/15', blue: 'border-blue-500/15', purple: 'border-purple-500/15', amber: 'border-amber-500/15' };
  const titleColor: Record<string, string> = { green: 'text-green-400', blue: 'text-blue-400', purple: 'text-purple-400', amber: 'text-amber-400' };

  return (
    <div className={`rounded-xl border bg-[#0f1629]/60 p-4 ${borderColor[color]}`}>
      <h3 className={`text-xs font-semibold uppercase tracking-wider mb-3 ${titleColor[color]}`}>
        {title}
      </h3>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="flex items-center justify-between text-xs">
            <span className="text-slate-300 truncate min-w-0 mr-2">{item.label || '-'}</span>
            <span className="text-slate-400 tabular-nums font-medium flex-shrink-0">
              {formatNumber(item.count)}
            </span>
          </div>
        ))}
        {items.length === 0 && <div className="text-slate-600 text-xs">Sem dados</div>}
      </div>
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
        className="w-full h-9 px-3 bg-[#0a0e1a] border border-slate-700/50 rounded-lg text-xs text-slate-300 focus:outline-none focus:border-green-500/50"
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
