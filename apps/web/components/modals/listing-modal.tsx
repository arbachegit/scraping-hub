'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { X, Loader2, ExternalLink, ArrowUp, ArrowDown, ChevronRight, ChevronDown, SlidersHorizontal } from 'lucide-react';
import { Input } from '@/components/ui/input';
import {
  listCompanies,
  listPeopleEnriched,
  listNews,
  listPoliticians,
  searchPoliticians,
  getPoliticianDetails,
  listEmendas,
  searchEmendas,
  formatRegime,
  type Company,
  type PeopleEnrichedRow,
  type NewsItem,
  type Politician,
  type PoliticianMandate,
  type Emenda,
} from '@/lib/api';
import { normalizePoliticianName, ibgeToUF } from '@/lib/politicians-utils';

type SortDirection = 'asc' | 'desc';

// ============================================
// EMPRESAS LISTING MODAL
// ============================================

interface EmpresasListingModalProps {
  isOpen: boolean;
  onClose: () => void;
  filters?: {
    nome?: string;
    cidade?: string;
    segmento?: string;
    regime?: string;
  };
}

export function EmpresasListingModal({ isOpen, onClose, filters }: EmpresasListingModalProps) {
  const [search, setSearch] = useState('');
  const [cidadeFilter, setCidadeFilter] = useState('');
  const [ufFilter, setUfFilter] = useState('');
  const [segmentoFilter, setSegmentoFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const activeFilterCount = [cidadeFilter, ufFilter, segmentoFilter].filter(Boolean).length;

  const query = useQuery({
    queryKey: ['empresas', 'listing', filters],
    queryFn: () =>
      listCompanies({
        nome: filters?.nome,
        cidade: filters?.cidade,
        segmento: filters?.segmento,
        regime: filters?.regime,
        limit: 500,
      }),
    enabled: isOpen,
    retry: 1,
    staleTime: 30_000,
  });

  const filteredData = useMemo(() => {
    let data = query.data?.empresas || [];

    if (search) {
      const searchLower = search.toLowerCase();
      data = data.filter(
        (e) =>
          (e.razao_social || '').toLowerCase().includes(searchLower) ||
          (e.nome_fantasia || '').toLowerCase().includes(searchLower) ||
          (e.cidade || '').toLowerCase().includes(searchLower) ||
          (e.cnae_descricao || '').toLowerCase().includes(searchLower) ||
          (e.regime_tributario || '').toLowerCase().includes(searchLower)
      );
    }

    if (cidadeFilter) {
      const cl = cidadeFilter.toLowerCase();
      data = data.filter((e) => (e.cidade || '').toLowerCase().includes(cl));
    }

    if (ufFilter) {
      const ul = ufFilter.toLowerCase();
      data = data.filter((e) => (e.estado || '').toLowerCase().includes(ul));
    }

    if (segmentoFilter) {
      const sl = segmentoFilter.toLowerCase();
      data = data.filter((e) => (e.cnae_descricao || '').toLowerCase().includes(sl));
    }

    if (sortColumn) {
      data = [...data].sort((a, b) => {
        const valA = String(
          (a as unknown as Record<string, unknown>)[sortColumn] ?? ''
        ).toLowerCase();
        const valB = String(
          (b as unknown as Record<string, unknown>)[sortColumn] ?? ''
        ).toLowerCase();
        return sortDirection === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
      });
    }

    return data;
  }, [query.data?.empresas, search, cidadeFilter, ufFilter, segmentoFilter, sortColumn, sortDirection]);

  const columnStats = useMemo(() => {
    const total = filteredData.length;
    if (total === 0) return null;
    const count = (fn: (e: Company) => string | undefined | null) =>
      filteredData.filter((e) => { const v = fn(e); return v && v !== '-'; }).length;
    return {
      razao_social: count((e) => e.razao_social),
      nome_fantasia: count((e) => e.nome_fantasia),
      cidade: count((e) => e.cidade),
      cnae: count((e) => e.cnae_descricao),
      regime: count((e) => e.regime_tributario),
      linkedin: count((e) => e.linkedin && e.linkedin !== 'NAO_POSSUI' && e.linkedin !== 'inexistente' ? e.linkedin : null),
      total,
    };
  }, [filteredData]);

  function handleSort(column: string) {
    if (sortColumn === column) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[55] flex items-center justify-center bg-black/85">
      <div className="w-[95%] max-w-6xl max-h-[90vh] overflow-hidden rounded-2xl border border-cyan-500/15 bg-gradient-to-b from-[#0f1629] to-[#0a0e1a] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <h2 className="text-lg font-semibold text-white flex items-center gap-3">
            <span className="w-1 h-5 bg-gradient-to-b from-cyan-400 to-blue-500 rounded" />
            Empresas
            <span className="bg-cyan-500/15 text-cyan-400 px-2.5 py-1 rounded text-sm">
              {filteredData.length}
            </span>
          </h2>
          {/* Column fill stats */}
          {columnStats && (
            <div className="flex items-center gap-3 text-xs">
              {([
                ['Fantasia', columnStats.nome_fantasia],
                ['Cidade', columnStats.cidade],
                ['CNAE', columnStats.cnae],
                ['Regime', columnStats.regime],
                ['LinkedIn', columnStats.linkedin],
              ] as const).map(([label, filled]) => {
                const pct = Math.round((filled / columnStats.total) * 100);
                const color = pct >= 70 ? 'text-green-400' : pct >= 30 ? 'text-amber-400' : 'text-red-400';
                return (
                  <span key={label} className="flex items-center gap-1 text-slate-500">
                    {label}: <span className={color}>{filled}/{columnStats.total}</span>
                  </span>
                );
              })}
            </div>
          )}
          <button
            onClick={onClose}
            className="flex items-center justify-center w-9 h-9 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-400 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Search + Filter Toggle */}
        <div className="flex items-center gap-3 px-6 py-3 border-b border-white/5">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filtrar resultados..."
            className="max-w-xs"
          />
          <button
            onClick={() => setShowFilters((v) => !v)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-colors ${
              showFilters || activeFilterCount > 0
                ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-400'
                : 'border-white/10 bg-white/5 text-slate-400 hover:border-cyan-500/20 hover:text-cyan-300'
            }`}
          >
            <SlidersHorizontal className="h-4 w-4" />
            Filtros
            {activeFilterCount > 0 && (
              <span className="bg-cyan-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>

        {/* Collapsible Filters */}
        {showFilters && (
          <div className="flex items-center gap-3 px-6 py-3 border-b border-white/5 bg-white/[0.02]">
            <Input
              value={cidadeFilter}
              onChange={(e) => setCidadeFilter(e.target.value)}
              placeholder="Cidade"
              className="max-w-[160px]"
            />
            <Input
              value={ufFilter}
              onChange={(e) => setUfFilter(e.target.value)}
              placeholder="UF"
              className="max-w-[80px]"
            />
            <Input
              value={segmentoFilter}
              onChange={(e) => setSegmentoFilter(e.target.value)}
              placeholder="Segmento / CNAE"
              className="max-w-[200px]"
            />
            {activeFilterCount > 0 && (
              <button
                onClick={() => { setCidadeFilter(''); setUfFilter(''); setSegmentoFilter(''); }}
                className="text-xs text-slate-500 hover:text-red-400 transition-colors"
              >
                Limpar
              </button>
            )}
          </div>
        )}

        {/* Table */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {query.isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <Loader2 className="h-10 w-10 animate-spin text-cyan-400 mb-4" />
              <span>Carregando empresas...</span>
            </div>
          ) : query.isError ? (
            <div className="text-center py-12 text-red-400">
              Erro ao carregar empresas. Tente novamente mais tarde.
            </div>
          ) : filteredData.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              Nenhuma empresa encontrada com os filtros aplicados.
            </div>
          ) : (
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-cyan-500/5">
                  <SortableHeader
                    label="Razão Social"
                    column="razao_social"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                  />
                  <SortableHeader
                    label="Nome Fantasia"
                    column="nome_fantasia"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                  />
                  <SortableHeader
                    label="Cidade"
                    column="cidade"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                  />
                  <SortableHeader
                    label="UF"
                    column="estado"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                  />
                  <SortableHeader
                    label="Segmento"
                    column="cnae_descricao"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                  />
                  <SortableHeader
                    label="Regime"
                    column="regime_tributario"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                  />
                  <th className="text-left p-3 text-cyan-400 font-semibold text-xs uppercase">
                    LinkedIn
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredData.map((e) => (
                  <EmpresaRow key={e.id} empresa={e} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function EmpresaRow({ empresa }: { empresa: Company }) {
  const [expanded, setExpanded] = useState(false);
  const hasLinkedin =
    empresa.linkedin && empresa.linkedin !== 'NAO_POSSUI' && empresa.linkedin !== 'inexistente';

  return (
    <>
      <tr
        className="border-b border-white/5 hover:bg-cyan-500/5 transition-colors cursor-pointer"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="p-3 text-slate-300 flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-cyan-400 flex-shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 text-slate-500 flex-shrink-0" />
          )}
          {empresa.razao_social || '-'}
        </td>
        <td className="p-3 text-slate-300">{empresa.nome_fantasia || '-'}</td>
        <td className="p-3 text-slate-300">{empresa.cidade || '-'}</td>
        <td className="p-3 text-slate-300">{empresa.estado || '-'}</td>
        <td className="p-3 text-slate-300">{empresa.cnae_descricao || '-'}</td>
        <td className="p-3">
          <RegimeBadge regime={empresa.regime_tributario} />
        </td>
        <td className="p-3">
          {hasLinkedin ? (
            <a
              href={empresa.linkedin}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-400 hover:underline inline-flex items-center gap-1"
              onClick={(e) => e.stopPropagation()}
            >
              Ver <ExternalLink className="h-3 w-3" />
            </a>
          ) : (
            <span className="text-slate-500">-</span>
          )}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-cyan-500/5 border-b border-white/5">
          <td colSpan={7} className="p-4">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-slate-500 text-xs uppercase">CNPJ</span>
                <p className="text-slate-200 font-mono">{empresa.cnpj || '-'}</p>
              </div>
              <div>
                <span className="text-slate-500 text-xs uppercase">Razão Social</span>
                <p className="text-slate-200">{empresa.razao_social || '-'}</p>
              </div>
              <div>
                <span className="text-slate-500 text-xs uppercase">Nome Fantasia</span>
                <p className="text-slate-200">{empresa.nome_fantasia || '-'}</p>
              </div>
              <div>
                <span className="text-slate-500 text-xs uppercase">Cidade / UF</span>
                <p className="text-slate-200">{[empresa.cidade, empresa.estado].filter(Boolean).join(' - ') || '-'}</p>
              </div>
              <div>
                <span className="text-slate-500 text-xs uppercase">Segmento (CNAE)</span>
                <p className="text-slate-200">{empresa.cnae_descricao || empresa.cnae_principal || '-'}</p>
              </div>
              <div>
                <span className="text-slate-500 text-xs uppercase">Regime Tributário</span>
                <p className="text-slate-200">{empresa.regime_tributario || '-'}</p>
              </div>
              <div>
                <span className="text-slate-500 text-xs uppercase">Situação Cadastral</span>
                <p className="text-slate-200">{empresa.situacao_cadastral || '-'}</p>
              </div>
              <div>
                <span className="text-slate-500 text-xs uppercase">Fonte</span>
                <p className="text-slate-200">{empresa.fonte || '-'}</p>
              </div>
              {hasLinkedin && (
                <div>
                  <span className="text-slate-500 text-xs uppercase">LinkedIn</span>
                  <p>
                    <a href={empresa.linkedin} target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline inline-flex items-center gap-1">
                      {empresa.linkedin} <ExternalLink className="h-3 w-3" />
                    </a>
                  </p>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ============================================
// PESSOAS LISTING MODAL
// ============================================

interface PessoasListingModalProps {
  isOpen: boolean;
  onClose: () => void;
  filters?: {
    nome?: string;
    cidade?: string;
  };
}

export function PessoasListingModal({ isOpen, onClose, filters }: PessoasListingModalProps) {
  const [search, setSearch] = useState('');
  const [cidadeFilter, setCidadeFilter] = useState('');
  const [ufFilter, setUfFilter] = useState('');
  const [areaFilter, setAreaFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const searchInputRef = useRef<HTMLInputElement>(null);
  const activeFilterCount = [cidadeFilter, ufFilter, areaFilter].filter(Boolean).length;
  const searchTerm = search.trim();
  const initialSearch = filters?.nome?.trim() || '';
  const apiSearch = searchTerm.length >= 2 ? searchTerm : initialSearch;
  const shouldFetch = apiSearch.length >= 2;

  useEffect(() => {
    if (!isOpen) return;
    const t = window.setTimeout(() => searchInputRef.current?.focus(), 50);
    return () => window.clearTimeout(t);
  }, [isOpen]);

  const query = useQuery({
    queryKey: ['pessoas', 'listing', filters, apiSearch],
    queryFn: () => listPeopleEnriched(apiSearch, 500, 0),
    enabled: isOpen && shouldFetch,
    retry: 1,
    staleTime: 30_000,
  });

  const filteredData = useMemo(() => {
    let data = query.data?.people || [];

    if (searchTerm.length >= 2) {
      const searchLower = searchTerm.toLowerCase();
      data = data.filter(
        (p) =>
          (p.nome || '').toLowerCase().includes(searchLower) ||
          (p.empresa || '').toLowerCase().includes(searchLower) ||
          (p.cidade || '').toLowerCase().includes(searchLower) ||
          (p.estado || '').toLowerCase().includes(searchLower) ||
          (p.cnae || '').toLowerCase().includes(searchLower) ||
          (p.descricao || p.cnae_descricao || '').toLowerCase().includes(searchLower) ||
          (p.email || '').toLowerCase().includes(searchLower) ||
          (p.phone || p.telefone || '').toLowerCase().includes(searchLower)
      );
    }

    if (filters?.cidade || cidadeFilter) {
      const cityLower = (cidadeFilter || filters?.cidade || '').toLowerCase();
      if (cityLower) data = data.filter((p) => (p.cidade || '').toLowerCase().includes(cityLower));
    }

    if (ufFilter) {
      const ufLower = ufFilter.toLowerCase();
      data = data.filter((p) => (p.estado || '').toLowerCase().includes(ufLower));
    }

    if (areaFilter) {
      const areaLower = areaFilter.toLowerCase();
      data = data.filter((p) =>
        (p.cnae || '').toLowerCase().includes(areaLower) ||
        (p.descricao || p.cnae_descricao || '').toLowerCase().includes(areaLower)
      );
    }

    if (sortColumn) {
      data = [...data].sort((a, b) => {
        const valA = ((a as unknown as Record<string, unknown>)[sortColumn] || '')
          .toString()
          .toLowerCase();
        const valB = ((b as unknown as Record<string, unknown>)[sortColumn] || '')
          .toString()
          .toLowerCase();
        return sortDirection === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
      });
    }

    return data;
  }, [filters?.cidade, cidadeFilter, ufFilter, areaFilter, query.data?.people, searchTerm, sortColumn, sortDirection]);

  const columnStats = useMemo(() => {
    const total = filteredData.length;
    if (total === 0) return null;
    const count = (fn: (p: PeopleEnrichedRow) => string | undefined | null) =>
      filteredData.filter((p) => { const v = fn(p); return v && v !== '-'; }).length;
    return {
      nome: count((p) => p.nome),
      empresa: count((p) => p.empresa),
      cidade: count((p) => p.cidade),
      estado: count((p) => p.estado),
      cnae: count((p) => p.cnae),
      descricao: count((p) => p.descricao || p.cnae_descricao),
      email: count((p) => p.email),
      phone: count((p) => p.phone || p.telefone),
      total,
    };
  }, [filteredData]);

  function handleSort(column: string) {
    if (sortColumn === column) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[55] flex items-center justify-center bg-black/85">
      <div className="w-[95%] max-w-5xl max-h-[90vh] overflow-hidden rounded-2xl border border-orange-500/15 bg-gradient-to-b from-[#0f1629] to-[#0a0e1a] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <h2 className="text-lg font-semibold text-white flex items-center gap-3">
            <span className="w-1 h-5 bg-gradient-to-b from-orange-400 to-orange-600 rounded" />
            Pessoas
            <span className="bg-orange-500/15 text-orange-400 px-2.5 py-1 rounded text-sm">
              {filteredData.length}
            </span>
          </h2>
          {/* Column fill stats */}
          {columnStats && (
            <div className="flex items-center gap-3 text-xs">
              {([
                ['Empresa', columnStats.empresa],
                ['Cidade', columnStats.cidade],
                ['Email', columnStats.email],
                ['Tel', columnStats.phone],
              ] as const).map(([label, filled]) => {
                const pct = Math.round((filled / columnStats.total) * 100);
                const color = pct >= 70 ? 'text-green-400' : pct >= 30 ? 'text-amber-400' : 'text-red-400';
                return (
                  <span key={label} className="flex items-center gap-1 text-slate-500">
                    {label}: <span className={color}>{filled}/{columnStats.total}</span>
                  </span>
                );
              })}
            </div>
          )}
          <button
            onClick={onClose}
            className="flex items-center justify-center w-9 h-9 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-400 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Search + Filter Toggle */}
        <div className="flex items-center gap-3 px-6 py-3 border-b border-white/5">
          <Input
            ref={searchInputRef}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Digite pelo menos 2 letras do nome..."
            className="max-w-xs"
          />
          <button
            onClick={() => setShowFilters((v) => !v)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-colors ${
              showFilters || activeFilterCount > 0
                ? 'border-orange-500/30 bg-orange-500/10 text-orange-400'
                : 'border-white/10 bg-white/5 text-slate-400 hover:border-orange-500/20 hover:text-orange-300'
            }`}
          >
            <SlidersHorizontal className="h-4 w-4" />
            Filtros
            {activeFilterCount > 0 && (
              <span className="bg-orange-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>

        {/* Collapsible Filters */}
        {showFilters && (
          <div className="flex items-center gap-3 px-6 py-3 border-b border-white/5 bg-white/[0.02]">
            <Input
              value={cidadeFilter}
              onChange={(e) => setCidadeFilter(e.target.value)}
              placeholder="Cidade"
              className="max-w-[160px]"
            />
            <Input
              value={ufFilter}
              onChange={(e) => setUfFilter(e.target.value)}
              placeholder="UF"
              className="max-w-[80px]"
            />
            <Input
              value={areaFilter}
              onChange={(e) => setAreaFilter(e.target.value)}
              placeholder="Área / CNAE"
              className="max-w-[200px]"
            />
            {activeFilterCount > 0 && (
              <button
                onClick={() => { setCidadeFilter(''); setUfFilter(''); setAreaFilter(''); }}
                className="text-xs text-slate-500 hover:text-red-400 transition-colors"
              >
                Limpar
              </button>
            )}
          </div>
        )}

        {/* Table */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {!shouldFetch ? (
            <div className="text-center py-12 text-slate-500">
              Digite pelo menos 2 letras para buscar pessoas no banco.
            </div>
          ) : query.isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <Loader2 className="h-10 w-10 animate-spin text-orange-400 mb-4" />
              <span>Carregando pessoas...</span>
            </div>
          ) : query.isError ? (
            <div className="text-center py-12 text-red-400">
              Erro ao carregar pessoas. Tente novamente mais tarde.
            </div>
          ) : filteredData.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              Nenhuma pessoa encontrada com os filtros aplicados.
            </div>
          ) : (
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-orange-500/5">
                  <SortableHeader
                    label="Nome"
                    column="nome"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="orange"
                  />
                  <SortableHeader
                    label="Empresa"
                    column="empresa"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="orange"
                  />
                  <SortableHeader
                    label="Cidade"
                    column="cidade"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="orange"
                  />
                  <SortableHeader
                    label="UF"
                    column="estado"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="orange"
                  />
                  <SortableHeader
                    label="CNAE"
                    column="cnae"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="orange"
                  />
                  <SortableHeader
                    label="Descricao"
                    column="descricao"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="orange"
                  />
                  <SortableHeader
                    label="Email"
                    column="email"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="orange"
                  />
                  <SortableHeader
                    label="Phone"
                    column="phone"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="orange"
                  />
                </tr>
              </thead>
              <tbody>
                {filteredData.map((p) => (
                  <PessoaRow key={p.id} pessoa={p} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function PessoaRow({ pessoa }: { pessoa: PeopleEnrichedRow }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        className="border-b border-white/5 hover:bg-orange-500/5 transition-colors cursor-pointer"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="p-3 text-slate-300 flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-orange-400 flex-shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 text-slate-500 flex-shrink-0" />
          )}
          {pessoa.nome || '-'}
        </td>
        <td className="p-3 text-slate-300">{pessoa.empresa || '-'}</td>
        <td className="p-3 text-slate-300">{pessoa.cidade || '-'}</td>
        <td className="p-3 text-slate-300">{pessoa.estado || '-'}</td>
        <td className="p-3 text-slate-300">{pessoa.cnae || '-'}</td>
        <td className="p-3 text-slate-300">{pessoa.descricao || pessoa.cnae_descricao || '-'}</td>
        <td className="p-3 text-slate-300">{pessoa.email || '-'}</td>
        <td className="p-3 text-slate-300">{pessoa.phone || pessoa.telefone || '-'}</td>
      </tr>
      {expanded && (
        <tr className="bg-orange-500/5 border-b border-white/5">
          <td colSpan={8} className="p-4">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-slate-500 text-xs uppercase">Nome Completo</span>
                <p className="text-slate-200">{pessoa.nome || '-'}</p>
              </div>
              <div>
                <span className="text-slate-500 text-xs uppercase">Empresa</span>
                <p className="text-slate-200">{pessoa.empresa || '-'}</p>
              </div>
              <div>
                <span className="text-slate-500 text-xs uppercase">Cidade / UF</span>
                <p className="text-slate-200">{[pessoa.cidade, pessoa.estado].filter(Boolean).join(' - ') || '-'}</p>
              </div>
              <div>
                <span className="text-slate-500 text-xs uppercase">CNAE</span>
                <p className="text-slate-200">{pessoa.cnae || '-'}</p>
              </div>
              <div>
                <span className="text-slate-500 text-xs uppercase">Descrição</span>
                <p className="text-slate-200">{pessoa.descricao || pessoa.cnae_descricao || '-'}</p>
              </div>
              <div>
                <span className="text-slate-500 text-xs uppercase">Email</span>
                <p className="text-slate-200">{pessoa.email || '-'}</p>
              </div>
              <div>
                <span className="text-slate-500 text-xs uppercase">Telefone</span>
                <p className="text-slate-200">{pessoa.phone || pessoa.telefone || '-'}</p>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ============================================
// NOTICIAS LISTING MODAL
// ============================================

interface NoticiasListingModalProps {
  isOpen: boolean;
  onClose: () => void;
  filters?: {
    q?: string;
    data_inicio?: string;
    data_fim?: string;
    idioma?: string;
    pais?: string;
    fonte?: string;
    tipo?: string;
  };
}

export function NoticiasListingModal({ isOpen, onClose, filters }: NoticiasListingModalProps) {
  const [search, setSearch] = useState('');
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  const query = useQuery({
    queryKey: ['noticias', 'listing', filters],
    queryFn: () =>
      listNews({
        q: filters?.q,
        data_inicio: filters?.data_inicio,
        data_fim: filters?.data_fim,
        idioma: filters?.idioma,
        pais: filters?.pais,
        fonte: filters?.fonte,
        tipo: filters?.tipo,
        limit: 500,
      }),
    enabled: isOpen,
    retry: 1,
    staleTime: 30_000,
  });

  const filteredData = useMemo(() => {
    let data = query.data?.news || [];

    if (search) {
      const searchLower = search.toLowerCase();
      data = data.filter(
        (n) =>
          (n.titulo || '').toLowerCase().includes(searchLower) ||
          (n.fonte_nome || '').toLowerCase().includes(searchLower) ||
          (n.tipo || '').toLowerCase().includes(searchLower)
      );
    }

    if (sortColumn) {
      data = [...data].sort((a, b) => {
        const valA = ((a as unknown as Record<string, unknown>)[sortColumn] || '')
          .toString()
          .toLowerCase();
        const valB = ((b as unknown as Record<string, unknown>)[sortColumn] || '')
          .toString()
          .toLowerCase();
        return sortDirection === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
      });
    }

    return data;
  }, [query.data?.news, search, sortColumn, sortDirection]);

  function handleSort(column: string) {
    if (sortColumn === column) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[55] flex items-center justify-center bg-black/85">
      <div className="w-[95%] max-w-6xl max-h-[90vh] overflow-hidden rounded-2xl border border-green-500/15 bg-gradient-to-b from-[#0f1629] to-[#0a0e1a] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <h2 className="text-lg font-semibold text-white flex items-center gap-3">
            <span className="w-1 h-5 bg-gradient-to-b from-green-400 to-green-600 rounded" />
            Notícias
            <span className="bg-green-500/15 text-green-400 px-2.5 py-1 rounded text-sm">
              {filteredData.length}
            </span>
          </h2>
          <button
            onClick={onClose}
            className="flex items-center justify-center w-9 h-9 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-400 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4 px-6 py-3 border-b border-white/5">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filtrar resultados..."
            className="max-w-xs"
          />
        </div>

        {/* Table */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {query.isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <Loader2 className="h-10 w-10 animate-spin text-green-400 mb-4" />
              <span>Carregando notícias...</span>
            </div>
          ) : query.isError ? (
            <div className="text-center py-12 text-red-400">
              Erro ao carregar notícias. Tente novamente mais tarde.
            </div>
          ) : filteredData.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              Nenhuma notícia encontrada com os filtros aplicados.
            </div>
          ) : (
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-green-500/5">
                  <SortableHeader
                    label="Título"
                    column="titulo"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="green"
                  />
                  <SortableHeader
                    label="Fonte"
                    column="fonte_nome"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="green"
                  />
                  <SortableHeader
                    label="Data"
                    column="data_publicacao"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="green"
                  />
                  <SortableHeader
                    label="Tipo"
                    column="tipo"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="green"
                  />
                  <th className="text-left p-3 text-green-400 font-semibold text-xs uppercase">
                    Link
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredData.map((n) => (
                  <NoticiaRow key={n.id} noticia={n} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function NoticiaRow({ noticia }: { noticia: NewsItem }) {
  const data = noticia.data_publicacao
    ? new Date(noticia.data_publicacao).toLocaleDateString('pt-BR')
    : '-';

  return (
    <tr className="border-b border-white/5 hover:bg-green-500/5 transition-colors">
      <td className="p-3 text-slate-300 max-w-xs truncate">{noticia.titulo || '-'}</td>
      <td className="p-3 text-slate-300">{noticia.fonte_nome || '-'}</td>
      <td className="p-3 text-slate-300">{data}</td>
      <td className="p-3 text-slate-300">{noticia.tipo || '-'}</td>
      <td className="p-3">
        {noticia.url ? (
          <a
            href={noticia.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-cyan-400 hover:underline inline-flex items-center gap-1"
          >
            Abrir <ExternalLink className="h-3 w-3" />
          </a>
        ) : (
          <span className="text-slate-500">-</span>
        )}
      </td>
    </tr>
  );
}

// ============================================
// POLITICOS LISTING MODAL
// ============================================

interface PoliticosListingModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PoliticosListingModal({ isOpen, onClose }: PoliticosListingModalProps) {
  const [nome, setNome] = useState('');
  const [partido, setPartido] = useState('');
  const [municipioFilter, setMunicipioFilter] = useState('');
  const [ufFilter, setUfFilter] = useState('');
  const [cargoFilter, setCargoFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [searchKey, setSearchKey] = useState('|');
  const [sortColumn, setSortColumn] = useState<string>('nome_completo');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const activeFilterCount = [municipioFilter, ufFilter, cargoFilter].filter(Boolean).length;

  const query = useQuery({
    queryKey: ['politicos', 'search', searchKey],
    queryFn: async () => {
      const [searchNome, searchPartido] = searchKey.split('|');

      if (searchNome && searchNome.length >= 2) {
        const result = await searchPoliticians(searchNome);
        if (searchPartido) {
          return {
            ...result,
            politicians: result.politicians.filter(
              (p) => (p.partido_sigla || '').toUpperCase() === searchPartido
            ),
          };
        }
        return result;
      }

      if (searchPartido) {
        return listPoliticians({ partido: searchPartido, limit: 100 });
      }

      return listPoliticians({ limit: 50 });
    },
    enabled: isOpen,
  });

  function handleSearch() {
    setSearchKey(`${nome.trim()}|${partido.trim().toUpperCase()}`);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') {
      handleSearch();
    }
  }

  const filteredData = useMemo(() => {
    let data = [...(query.data?.politicians || [])];

    if (municipioFilter) {
      const mLower = municipioFilter.toLowerCase();
      data = data.filter((p) => (p.municipio || '').toLowerCase().includes(mLower));
    }

    if (ufFilter) {
      const uLower = ufFilter.toLowerCase();
      data = data.filter((p) => ibgeToUF(p.codigo_ibge).toLowerCase().includes(uLower));
    }

    if (cargoFilter) {
      const cLower = cargoFilter.toLowerCase();
      data = data.filter((p) =>
        (p.cargo_atual || '').toLowerCase().includes(cLower) ||
        (p.ocupacao || '').toLowerCase().includes(cLower)
      );
    }

    data.sort((a, b) => {
      const col = sortColumn || 'nome_completo';

      if (col === 'estado') {
        const valA = ibgeToUF(a.codigo_ibge).toLowerCase();
        const valB = ibgeToUF(b.codigo_ibge).toLowerCase();
        return sortDirection === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
      }

      const valA = String(
        (a as unknown as Record<string, unknown>)[col] ?? ''
      ).toLowerCase();
      const valB = String(
        (b as unknown as Record<string, unknown>)[col] ?? ''
      ).toLowerCase();
      return sortDirection === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    });

    return data;
  }, [query.data?.politicians, municipioFilter, ufFilter, cargoFilter, sortColumn, sortDirection]);

  const columnStats = useMemo(() => {
    const total = filteredData.length;
    if (total === 0) return null;
    const count = (fn: (p: Politician) => string | undefined | null) =>
      filteredData.filter((p) => { const v = fn(p); return v && v !== '-'; }).length;
    return {
      nome_urna: count((p) => p.nome_urna),
      municipio: count((p) => p.municipio),
      partido: count((p) => p.partido_sigla),
      cargo: count((p) => p.cargo_atual || p.ocupacao),
      sexo: count((p) => p.sexo),
      total,
    };
  }, [filteredData]);

  function handleSort(column: string) {
    if (sortColumn === column) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[55] flex items-center justify-center bg-black/85">
      <div className="w-[95%] max-w-6xl max-h-[90vh] overflow-hidden rounded-2xl border border-blue-500/15 bg-gradient-to-b from-[#0f1629] to-[#0a0e1a] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <h2 className="text-lg font-semibold text-white flex items-center gap-3">
            <span className="w-1 h-5 bg-gradient-to-b from-blue-400 to-blue-600 rounded" />
            Políticos
            {!query.isLoading && (
              <span className="bg-blue-500/15 text-blue-400 px-2.5 py-1 rounded text-sm">
                {filteredData.length}
              </span>
            )}
          </h2>
          {/* Column fill stats */}
          {columnStats && (
            <div className="flex items-center gap-3 text-xs">
              {([
                ['Urna', columnStats.nome_urna],
                ['Município', columnStats.municipio],
                ['Partido', columnStats.partido],
                ['Cargo', columnStats.cargo],
                ['Sexo', columnStats.sexo],
              ] as const).map(([label, filled]) => {
                const pct = Math.round((filled / columnStats.total) * 100);
                const color = pct >= 70 ? 'text-green-400' : pct >= 30 ? 'text-amber-400' : 'text-red-400';
                return (
                  <span key={label} className="flex items-center gap-1 text-slate-500">
                    {label}: <span className={color}>{filled}/{columnStats.total}</span>
                  </span>
                );
              })}
            </div>
          )}
          <button
            onClick={onClose}
            className="flex items-center justify-center w-9 h-9 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-400 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Search + Filter Toggle */}
        <div className="flex items-center gap-3 px-6 py-3 border-b border-white/5">
          <Input
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Nome do político..."
            className="max-w-xs"
          />
          <Input
            value={partido}
            onChange={(e) => setPartido(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Partido (ex: PT, PL, MDB)"
            className="max-w-[180px]"
          />
          <button
            onClick={handleSearch}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors whitespace-nowrap"
          >
            Buscar
          </button>
          <button
            onClick={() => setShowFilters((v) => !v)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-colors ${
              showFilters || activeFilterCount > 0
                ? 'border-blue-500/30 bg-blue-500/10 text-blue-400'
                : 'border-white/10 bg-white/5 text-slate-400 hover:border-blue-500/20 hover:text-blue-300'
            }`}
          >
            <SlidersHorizontal className="h-4 w-4" />
            Filtros
            {activeFilterCount > 0 && (
              <span className="bg-blue-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>

        {/* Collapsible Filters */}
        {showFilters && (
          <div className="flex items-center gap-3 px-6 py-3 border-b border-white/5 bg-white/[0.02]">
            <Input
              value={municipioFilter}
              onChange={(e) => setMunicipioFilter(e.target.value)}
              placeholder="Município"
              className="max-w-[160px]"
            />
            <Input
              value={ufFilter}
              onChange={(e) => setUfFilter(e.target.value)}
              placeholder="UF"
              className="max-w-[80px]"
            />
            <Input
              value={cargoFilter}
              onChange={(e) => setCargoFilter(e.target.value)}
              placeholder="Cargo / Ocupação"
              className="max-w-[200px]"
            />
            {activeFilterCount > 0 && (
              <button
                onClick={() => { setMunicipioFilter(''); setUfFilter(''); setCargoFilter(''); }}
                className="text-xs text-slate-500 hover:text-red-400 transition-colors"
              >
                Limpar
              </button>
            )}
          </div>
        )}

        {/* Table */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {query.isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <Loader2 className="h-10 w-10 animate-spin text-blue-400 mb-4" />
              <span>Buscando políticos...</span>
            </div>
          ) : query.isError ? (
            <div className="text-center py-12 text-red-400">
              Erro ao buscar políticos. Verifique se o Brasil Data Hub está configurado.
            </div>
          ) : filteredData.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              Nenhum político encontrado. Tente outro nome ou partido.
            </div>
          ) : (
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-blue-500/5">
                  <th className="w-8 p-3" />
                  <SortableHeader
                    label="Nome"
                    column="nome_completo"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="blue"
                  />
                  <SortableHeader
                    label="Nome Urna"
                    column="nome_urna"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="blue"
                  />
                  <SortableHeader
                    label="UF"
                    column="estado"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="blue"
                  />
                  <SortableHeader
                    label="Município"
                    column="municipio"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="blue"
                  />
                </tr>
              </thead>
              <tbody>
                {filteredData.map((p) => (
                  <PoliticoRow key={p.id} politico={p} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function PoliticoRow({ politico }: { politico: Politician }) {
  const [expanded, setExpanded] = useState(false);

  const mandatesQuery = useQuery({
    queryKey: ['politico', 'details', politico.id],
    queryFn: () => getPoliticianDetails(politico.id),
    enabled: expanded,
    staleTime: 5 * 60 * 1000,
  });

  const uf = ibgeToUF(politico.codigo_ibge);

  return (
    <>
      <tr
        onClick={() => setExpanded((v) => !v)}
        className="border-b border-white/5 hover:bg-blue-500/5 transition-colors cursor-pointer"
      >
        <td className="p-3 w-8 text-slate-500">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-blue-400" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </td>
        <td className="p-3 text-slate-300">{normalizePoliticianName(politico.nome_completo) || '-'}</td>
        <td className="p-3 text-slate-300">{normalizePoliticianName(politico.nome_urna) || '-'}</td>
        <td className="p-3 text-slate-300">{uf || '-'}</td>
        <td className="p-3 text-slate-300">{normalizePoliticianName(politico.municipio) || '-'}</td>
      </tr>

      {expanded && (
        <tr className="border-b border-white/5">
          <td colSpan={5} className="p-0">
            <div className="bg-blue-500/5 px-8 py-3">
              {/* Personal info */}
              <div className="flex flex-wrap gap-x-6 gap-y-1 mb-3 text-xs">
                {politico.sexo && (
                  <span className="text-slate-500">Sexo: <span className="text-slate-300">{politico.sexo}</span></span>
                )}
                {politico.ocupacao && (
                  <span className="text-slate-500">Ocupação: <span className="text-slate-300">{normalizePoliticianName(politico.ocupacao)}</span></span>
                )}
                {politico.grau_instrucao && (
                  <span className="text-slate-500">Instrução: <span className="text-slate-300">{normalizePoliticianName(politico.grau_instrucao)}</span></span>
                )}
                {politico.cargo_atual && (
                  <span className="text-slate-500">Cargo: <span className="text-blue-400">{normalizePoliticianName(politico.cargo_atual)}</span></span>
                )}
              </div>

              {/* Mandatos */}
              {mandatesQuery.isLoading ? (
                <div className="flex items-center gap-2 py-2 text-slate-400 text-xs">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Carregando mandatos...
                </div>
              ) : mandatesQuery.isError ? (
                <div className="py-2 text-red-400 text-xs">
                  Erro ao carregar mandatos.
                </div>
              ) : (mandatesQuery.data?.mandatos || []).length === 0 ? (
                <div className="py-2 text-slate-500 text-xs">
                  Nenhum mandato encontrado.
                </div>
              ) : (
                <table className="w-full border-collapse text-xs">
                  <thead>
                    <tr className="text-slate-500">
                      <th className="text-left py-1.5 px-2 font-medium uppercase">Cargo</th>
                      <th className="text-left py-1.5 px-2 font-medium uppercase">Ano</th>
                      <th className="text-left py-1.5 px-2 font-medium uppercase">Partido</th>
                      <th className="text-left py-1.5 px-2 font-medium uppercase">Eleito</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(mandatesQuery.data?.mandatos || []).map((m: PoliticianMandate) => (
                      <tr key={m.id} className="border-t border-white/5">
                        <td className="py-1.5 px-2 text-slate-300">
                          {normalizePoliticianName(m.cargo) || '-'}
                        </td>
                        <td className="py-1.5 px-2 text-slate-300 font-variant-numeric tabular-nums">
                          {m.ano_eleicao || '-'}
                        </td>
                        <td className="py-1.5 px-2">
                          {m.partido_sigla ? (
                            <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-500/15 text-blue-400">
                              {m.partido_sigla}
                            </span>
                          ) : (
                            <span className="text-slate-500">-</span>
                          )}
                        </td>
                        <td className="py-1.5 px-2">
                          {m.eleito === true ? (
                            <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-500/15 text-green-400">
                              Eleito
                            </span>
                          ) : m.eleito === false ? (
                            <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-500/15 text-red-400">
                              Não eleito
                            </span>
                          ) : (
                            <span className="text-slate-500">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ============================================
// MANDATOS LISTING MODAL
// ============================================

interface MandatosListingModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function MandatosListingModal({ isOpen, onClose }: MandatosListingModalProps) {
  const [nome, setNome] = useState('');
  const [partido, setPartido] = useState('');
  const [cargoFilter, setCargoFilter] = useState('');
  const [ufFilter, setUfFilter] = useState('');
  const [anoFilter, setAnoFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [searchKey, setSearchKey] = useState('|');
  const [sortColumn, setSortColumn] = useState<string>('nome_completo');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const activeFilterCount = [cargoFilter, ufFilter, anoFilter].filter(Boolean).length;

  const query = useQuery({
    queryKey: ['mandatos', 'search', searchKey],
    queryFn: async () => {
      const [searchNome, searchPartido] = searchKey.split('|');

      if (searchNome && searchNome.length >= 2) {
        const result = await searchPoliticians(searchNome);
        if (searchPartido) {
          return {
            ...result,
            politicians: result.politicians.filter(
              (p) => (p.partido_sigla || '').toUpperCase() === searchPartido
            ),
          };
        }
        return result;
      }

      if (searchPartido) {
        return listPoliticians({ partido: searchPartido, limit: 100 });
      }

      return listPoliticians({ limit: 50 });
    },
    enabled: isOpen,
  });

  function handleSearch() {
    setSearchKey(`${nome.trim()}|${partido.trim().toUpperCase()}`);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') {
      handleSearch();
    }
  }

  const filteredData = useMemo(() => {
    let data = [...(query.data?.politicians || [])];

    if (ufFilter) {
      const uLower = ufFilter.toLowerCase();
      data = data.filter((p) => ibgeToUF(p.codigo_ibge).toLowerCase().includes(uLower));
    }

    if (cargoFilter) {
      const cLower = cargoFilter.toLowerCase();
      data = data.filter((p) =>
        (p.cargo_atual || '').toLowerCase().includes(cLower) ||
        (p.ocupacao || '').toLowerCase().includes(cLower)
      );
    }

    data.sort((a, b) => {
      const col = sortColumn || 'nome_completo';
      if (col === 'estado') {
        const valA = ibgeToUF(a.codigo_ibge).toLowerCase();
        const valB = ibgeToUF(b.codigo_ibge).toLowerCase();
        return sortDirection === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
      }
      const valA = String((a as unknown as Record<string, unknown>)[col] ?? '').toLowerCase();
      const valB = String((b as unknown as Record<string, unknown>)[col] ?? '').toLowerCase();
      return sortDirection === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    });

    return data;
  }, [query.data?.politicians, ufFilter, cargoFilter, sortColumn, sortDirection]);

  const columnStats = useMemo(() => {
    const total = filteredData.length;
    if (total === 0) return null;
    const count = (fn: (p: Politician) => string | undefined | null) =>
      filteredData.filter((p) => { const v = fn(p); return v && v !== '-'; }).length;
    return {
      partido: count((p) => p.partido_sigla),
      cargo: count((p) => p.cargo_atual),
      municipio: count((p) => p.municipio),
      total,
    };
  }, [filteredData]);

  function handleSort(column: string) {
    if (sortColumn === column) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[55] flex items-center justify-center bg-black/85">
      <div className="w-[95%] max-w-6xl max-h-[90vh] overflow-hidden rounded-2xl border border-purple-500/15 bg-gradient-to-b from-[#0f1629] to-[#0a0e1a] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <h2 className="text-lg font-semibold text-white flex items-center gap-3">
            <span className="w-1 h-5 bg-gradient-to-b from-purple-400 to-purple-600 rounded" />
            Mandatos
            {!query.isLoading && (
              <span className="bg-purple-500/15 text-purple-400 px-2.5 py-1 rounded text-sm">
                {filteredData.length}
              </span>
            )}
          </h2>
          {/* Column fill stats */}
          {columnStats && (
            <div className="flex items-center gap-3 text-xs">
              {([
                ['Partido', columnStats.partido],
                ['Cargo', columnStats.cargo],
                ['Município', columnStats.municipio],
              ] as const).map(([label, filled]) => {
                const pct = Math.round((filled / columnStats.total) * 100);
                const color = pct >= 70 ? 'text-green-400' : pct >= 30 ? 'text-amber-400' : 'text-red-400';
                return (
                  <span key={label} className="flex items-center gap-1 text-slate-500">
                    {label}: <span className={color}>{filled}/{columnStats.total}</span>
                  </span>
                );
              })}
            </div>
          )}
          <button
            onClick={onClose}
            className="flex items-center justify-center w-9 h-9 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-400 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Search + Filter Toggle */}
        <div className="flex items-center gap-3 px-6 py-3 border-b border-white/5">
          <Input
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Nome do político..."
            className="max-w-xs"
          />
          <Input
            value={partido}
            onChange={(e) => setPartido(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Partido (ex: PT, PL, MDB)"
            className="max-w-[180px]"
          />
          <button
            onClick={handleSearch}
            className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium transition-colors whitespace-nowrap"
          >
            Buscar
          </button>
          <button
            onClick={() => setShowFilters((v) => !v)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-colors ${
              showFilters || activeFilterCount > 0
                ? 'border-purple-500/30 bg-purple-500/10 text-purple-400'
                : 'border-white/10 bg-white/5 text-slate-400 hover:border-purple-500/20 hover:text-purple-300'
            }`}
          >
            <SlidersHorizontal className="h-4 w-4" />
            Filtros
            {activeFilterCount > 0 && (
              <span className="bg-purple-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>

        {/* Collapsible Filters */}
        {showFilters && (
          <div className="flex items-center gap-3 px-6 py-3 border-b border-white/5 bg-white/[0.02]">
            <Input
              value={cargoFilter}
              onChange={(e) => setCargoFilter(e.target.value)}
              placeholder="Cargo (Prefeito, Vereador...)"
              className="max-w-[200px]"
            />
            <Input
              value={ufFilter}
              onChange={(e) => setUfFilter(e.target.value)}
              placeholder="UF"
              className="max-w-[80px]"
            />
            <Input
              value={anoFilter}
              onChange={(e) => setAnoFilter(e.target.value)}
              placeholder="Ano eleição"
              className="max-w-[120px]"
            />
            {activeFilterCount > 0 && (
              <button
                onClick={() => { setCargoFilter(''); setUfFilter(''); setAnoFilter(''); }}
                className="text-xs text-slate-500 hover:text-red-400 transition-colors"
              >
                Limpar
              </button>
            )}
          </div>
        )}

        {/* Table */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {query.isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <Loader2 className="h-10 w-10 animate-spin text-purple-400 mb-4" />
              <span>Buscando mandatos...</span>
            </div>
          ) : query.isError ? (
            <div className="text-center py-12 text-red-400">
              Erro ao buscar mandatos. Verifique se o Brasil Data Hub está configurado.
            </div>
          ) : filteredData.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              Nenhum político encontrado. Tente outro nome ou partido.
            </div>
          ) : (
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-purple-500/5">
                  <th className="w-8 p-3" />
                  <SortableHeader
                    label="Nome"
                    column="nome_completo"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="blue"
                  />
                  <SortableHeader
                    label="Partido"
                    column="partido_sigla"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="blue"
                  />
                  <SortableHeader
                    label="UF"
                    column="estado"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="blue"
                  />
                  <SortableHeader
                    label="Município"
                    column="municipio"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                    color="blue"
                  />
                </tr>
              </thead>
              <tbody>
                {filteredData.map((p) => (
                  <MandatoRow key={p.id} politico={p} anoFilter={anoFilter} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function MandatoRow({ politico, anoFilter }: { politico: Politician; anoFilter: string }) {
  const [expanded, setExpanded] = useState(false);

  const mandatesQuery = useQuery({
    queryKey: ['politico', 'details', politico.id],
    queryFn: () => getPoliticianDetails(politico.id),
    enabled: expanded,
    staleTime: 5 * 60 * 1000,
  });

  const uf = ibgeToUF(politico.codigo_ibge);

  const mandatos = useMemo(() => {
    let list = mandatesQuery.data?.mandatos || [];
    if (anoFilter) {
      list = list.filter((m) => String(m.ano_eleicao).includes(anoFilter));
    }
    return list;
  }, [mandatesQuery.data?.mandatos, anoFilter]);

  return (
    <>
      <tr
        onClick={() => setExpanded((v) => !v)}
        className="border-b border-white/5 hover:bg-purple-500/5 transition-colors cursor-pointer"
      >
        <td className="p-3 w-8 text-slate-500">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-purple-400" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </td>
        <td className="p-3 text-slate-300">{normalizePoliticianName(politico.nome_completo) || '-'}</td>
        <td className="p-3">
          {politico.partido_sigla ? (
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-500/15 text-purple-400">
              {politico.partido_sigla}
            </span>
          ) : (
            <span className="text-slate-500">-</span>
          )}
        </td>
        <td className="p-3 text-slate-300">{uf || '-'}</td>
        <td className="p-3 text-slate-300">{normalizePoliticianName(politico.municipio) || '-'}</td>
      </tr>

      {expanded && (
        <tr className="border-b border-white/5">
          <td colSpan={5} className="p-0">
            <div className="bg-purple-500/5 px-8 py-3">
              {mandatesQuery.isLoading ? (
                <div className="flex items-center gap-2 py-2 text-slate-400 text-xs">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Carregando mandatos...
                </div>
              ) : mandatesQuery.isError ? (
                <div className="py-2 text-red-400 text-xs">
                  Erro ao carregar mandatos.
                </div>
              ) : mandatos.length === 0 ? (
                <div className="py-2 text-slate-500 text-xs">
                  Nenhum mandato encontrado.
                </div>
              ) : (
                <>
                  <div className="text-xs text-slate-500 mb-2">
                    {mandatos.length} mandato{mandatos.length > 1 ? 's' : ''} registrado{mandatos.length > 1 ? 's' : ''}
                  </div>
                  <table className="w-full border-collapse text-xs">
                    <thead>
                      <tr className="text-slate-500">
                        <th className="text-left py-1.5 px-2 font-medium uppercase">Cargo</th>
                        <th className="text-left py-1.5 px-2 font-medium uppercase">Ano</th>
                        <th className="text-left py-1.5 px-2 font-medium uppercase">Partido</th>
                        <th className="text-left py-1.5 px-2 font-medium uppercase">Município</th>
                        <th className="text-left py-1.5 px-2 font-medium uppercase">Votos</th>
                        <th className="text-left py-1.5 px-2 font-medium uppercase">Eleito</th>
                      </tr>
                    </thead>
                    <tbody>
                      {mandatos.map((m: PoliticianMandate) => (
                        <tr key={m.id} className="border-t border-white/5">
                          <td className="py-1.5 px-2 text-slate-300">
                            {normalizePoliticianName(m.cargo) || '-'}
                          </td>
                          <td className="py-1.5 px-2 text-slate-300 tabular-nums">
                            {m.ano_eleicao || '-'}
                          </td>
                          <td className="py-1.5 px-2">
                            {m.partido_sigla ? (
                              <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-500/15 text-purple-400">
                                {m.partido_sigla}
                              </span>
                            ) : (
                              <span className="text-slate-500">-</span>
                            )}
                          </td>
                          <td className="py-1.5 px-2 text-slate-300">
                            {normalizePoliticianName(m.municipio) || '-'}
                          </td>
                          <td className="py-1.5 px-2 text-slate-300 tabular-nums">
                            {(m as unknown as Record<string, unknown>).votos_nominais
                              ? Number((m as unknown as Record<string, unknown>).votos_nominais).toLocaleString('pt-BR')
                              : '-'}
                          </td>
                          <td className="py-1.5 px-2">
                            {m.eleito === true ? (
                              <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-500/15 text-green-400">
                                Eleito
                              </span>
                            ) : m.eleito === false ? (
                              <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-500/15 text-red-400">
                                Não eleito
                              </span>
                            ) : (
                              <span className="text-slate-500">-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ============================================
// EMENDAS LISTING MODAL
// ============================================

interface EmendasListingModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function EmendasListingModal({ isOpen, onClose }: EmendasListingModalProps) {
  const [search, setSearch] = useState('');
  const [searchKey, setSearchKey] = useState('');
  const [funcaoFilter, setFuncaoFilter] = useState('');
  const [localidadeFilter, setLocalidadeFilter] = useState('');
  const [tipoFilter, setTipoFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [sortColumn, setSortColumn] = useState<string>('ano');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const activeFilterCount = [funcaoFilter, localidadeFilter, tipoFilter].filter(Boolean).length;

  const query = useQuery({
    queryKey: ['emendas', 'listing', searchKey],
    queryFn: async () => {
      if (searchKey && searchKey.length >= 2) {
        return searchEmendas(searchKey, 200);
      }
      return listEmendas({ limit: 200 });
    },
    enabled: isOpen,
    retry: 1,
    staleTime: 30_000,
  });

  function handleSearch() {
    setSearchKey(search.trim());
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') {
      handleSearch();
    }
  }

  const filteredData = useMemo(() => {
    let data = [...(query.data?.emendas || [])];

    if (funcaoFilter) {
      const fLower = funcaoFilter.toLowerCase();
      data = data.filter((e) =>
        (e.funcao || e.area_governo || '').toLowerCase().includes(fLower) ||
        (e.subfuncao || '').toLowerCase().includes(fLower)
      );
    }

    if (localidadeFilter) {
      const lLower = localidadeFilter.toLowerCase();
      data = data.filter((e) => (e.localidade || e.uf || '').toLowerCase().includes(lLower));
    }

    if (tipoFilter) {
      const tLower = tipoFilter.toLowerCase();
      data = data.filter((e) => (e.tipo_emenda || e.tipo || '').toLowerCase().includes(tLower));
    }

    const col = sortColumn || 'ano';
    data.sort((a, b) => {
      if (col === 'valor_empenhado' || col === 'valor' || col === 'ano') {
        const valA = Number((a as unknown as Record<string, unknown>)[col]) || 0;
        const valB = Number((b as unknown as Record<string, unknown>)[col]) || 0;
        return sortDirection === 'asc' ? valA - valB : valB - valA;
      }
      const valA = String((a as unknown as Record<string, unknown>)[col] ?? '').toLowerCase();
      const valB = String((b as unknown as Record<string, unknown>)[col] ?? '').toLowerCase();
      return sortDirection === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    });

    return data;
  }, [query.data?.emendas, funcaoFilter, localidadeFilter, tipoFilter, sortColumn, sortDirection]);

  const columnStats = useMemo(() => {
    const total = filteredData.length;
    if (total === 0) return null;
    const count = (fn: (e: Emenda) => string | number | undefined | null) =>
      filteredData.filter((e) => { const v = fn(e); return v && v !== '-' && v !== 0; }).length;
    return {
      funcao: count((e) => e.funcao || e.area_governo),
      localidade: count((e) => e.localidade),
      valor: count((e) => e.valor_empenhado || e.valor),
      tipo: count((e) => e.tipo_emenda || e.tipo),
      subfuncao: count((e) => e.subfuncao),
      total,
    };
  }, [filteredData]);

  function handleSort(column: string) {
    if (sortColumn === column) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(column);
      setSortDirection(column === 'valor_empenhado' || column === 'valor' || column === 'ano' ? 'desc' : 'asc');
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[55] flex items-center justify-center bg-black/85">
      <div className="w-[95%] max-w-7xl max-h-[90vh] overflow-hidden rounded-2xl border border-cyan-500/15 bg-gradient-to-b from-[#0f1629] to-[#0a0e1a] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <h2 className="text-lg font-semibold text-white flex items-center gap-3">
            <span className="w-1 h-5 bg-gradient-to-b from-cyan-400 to-cyan-600 rounded" />
            Emendas Parlamentares
            {!query.isLoading && (
              <span className="bg-cyan-500/15 text-cyan-400 px-2.5 py-1 rounded text-sm">
                {filteredData.length}
              </span>
            )}
          </h2>
          {/* Column fill stats */}
          {columnStats && (
            <div className="flex items-center gap-3 text-xs">
              {([
                ['Função', columnStats.funcao],
                ['Local', columnStats.localidade],
                ['Valor', columnStats.valor],
                ['Tipo', columnStats.tipo],
                ['Sub', columnStats.subfuncao],
              ] as const).map(([label, filled]) => {
                const pct = Math.round((filled / columnStats.total) * 100);
                const color = pct >= 70 ? 'text-green-400' : pct >= 30 ? 'text-amber-400' : 'text-red-400';
                return (
                  <span key={label} className="flex items-center gap-1 text-slate-500">
                    {label}: <span className={color}>{filled}/{columnStats.total}</span>
                  </span>
                );
              })}
            </div>
          )}
          <button
            onClick={onClose}
            className="flex items-center justify-center w-9 h-9 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-400 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Search + Filter Toggle */}
        <div className="flex items-center gap-3 px-6 py-3 border-b border-white/5">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Buscar por autor, função ou localidade..."
            className="max-w-md"
          />
          <button
            onClick={handleSearch}
            className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium transition-colors whitespace-nowrap"
          >
            Buscar
          </button>
          <button
            onClick={() => setShowFilters((v) => !v)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-colors ${
              showFilters || activeFilterCount > 0
                ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-400'
                : 'border-white/10 bg-white/5 text-slate-400 hover:border-cyan-500/20 hover:text-cyan-300'
            }`}
          >
            <SlidersHorizontal className="h-4 w-4" />
            Filtros
            {activeFilterCount > 0 && (
              <span className="bg-cyan-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>

        {/* Collapsible Filters */}
        {showFilters && (
          <div className="flex items-center gap-3 px-6 py-3 border-b border-white/5 bg-white/[0.02]">
            <Input
              value={funcaoFilter}
              onChange={(e) => setFuncaoFilter(e.target.value)}
              placeholder="Função (Saúde, Educação...)"
              className="max-w-[200px]"
            />
            <Input
              value={localidadeFilter}
              onChange={(e) => setLocalidadeFilter(e.target.value)}
              placeholder="Localidade / UF"
              className="max-w-[180px]"
            />
            <Input
              value={tipoFilter}
              onChange={(e) => setTipoFilter(e.target.value)}
              placeholder="Tipo (Individual, Bancada...)"
              className="max-w-[200px]"
            />
            {activeFilterCount > 0 && (
              <button
                onClick={() => { setFuncaoFilter(''); setLocalidadeFilter(''); setTipoFilter(''); }}
                className="text-xs text-slate-500 hover:text-red-400 transition-colors"
              >
                Limpar
              </button>
            )}
          </div>
        )}

        {/* Table */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {query.isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <Loader2 className="h-10 w-10 animate-spin text-cyan-400 mb-4" />
              <span>Buscando emendas...</span>
            </div>
          ) : query.isError ? (
            <div className="text-center py-12 text-red-400">
              Erro ao carregar emendas. Verifique se o Brasil Data Hub está configurado.
            </div>
          ) : filteredData.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              Nenhuma emenda encontrada. Tente outro termo de busca.
            </div>
          ) : (
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-cyan-500/5">
                  <th className="w-8 p-3" />
                  <SortableHeader
                    label="Autor"
                    column="autor"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                  />
                  <SortableHeader
                    label="Função"
                    column="funcao"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                  />
                  <SortableHeader
                    label="Localidade"
                    column="localidade"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                  />
                  <SortableHeader
                    label="Valor Empenhado"
                    column="valor_empenhado"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                  />
                  <SortableHeader
                    label="Ano"
                    column="ano"
                    currentColumn={sortColumn}
                    direction={sortDirection}
                    onSort={handleSort}
                  />
                </tr>
              </thead>
              <tbody>
                {filteredData.map((e) => (
                  <EmendaRow key={e.id} emenda={e} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function EmendaRow({ emenda }: { emenda: Emenda }) {
  const [expanded, setExpanded] = useState(false);

  const fmtBRL = (v?: number | null) =>
    v ? v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : '-';

  const valorEmpenhado = emenda.valor_empenhado || emenda.valor;
  const tipoEmenda = emenda.tipo_emenda || emenda.tipo;
  const funcao = emenda.funcao || emenda.area_governo;

  // Short tipo label
  const tipoShort = tipoEmenda
    ? tipoEmenda.replace('Emenda ', '').replace('Individual - ', '').replace('Transferências com Finalidade Definida', 'TFD').replace('Transferências Especiais', 'TE')
    : null;

  return (
    <>
      <tr
        onClick={() => setExpanded((v) => !v)}
        className="border-b border-white/5 hover:bg-cyan-500/5 transition-colors cursor-pointer"
      >
        <td className="p-3 w-8 text-slate-500">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-cyan-400" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </td>
        <td className="p-3 text-slate-300 max-w-[180px] min-w-0 truncate">{emenda.autor || '-'}</td>
        <td className="p-3 text-slate-300 max-w-[150px] min-w-0 truncate">{funcao || '-'}</td>
        <td className="p-3 text-slate-300 max-w-[150px] min-w-0 truncate">{emenda.localidade || '-'}</td>
        <td className="p-3 text-emerald-400 font-variant-numeric tabular-nums whitespace-nowrap">
          {fmtBRL(valorEmpenhado)}
        </td>
        <td className="p-3 text-slate-300 font-variant-numeric tabular-nums">{emenda.ano || '-'}</td>
      </tr>

      {expanded && (
        <tr className="border-b border-white/5">
          <td colSpan={7} className="p-0">
            <div className="bg-cyan-500/5 px-8 py-3">
              {/* Tipo + Código */}
              <div className="flex flex-wrap gap-x-6 gap-y-1 mb-3 text-xs">
                {tipoEmenda && (
                  <span className="text-slate-500">Tipo: <span className="px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-400 font-medium">{tipoShort}</span></span>
                )}
                {emenda.codigo_emenda && (
                  <span className="text-slate-500">Código: <span className="text-slate-300 font-mono">{emenda.codigo_emenda}</span></span>
                )}
                {emenda.numero_emenda && (
                  <span className="text-slate-500">Número: <span className="text-slate-300 font-mono">{emenda.numero_emenda}</span></span>
                )}
                {emenda.subfuncao && (
                  <span className="text-slate-500">Subfunção: <span className="text-slate-300">{emenda.subfuncao}</span></span>
                )}
              </div>

              {/* Financial details */}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-xs">
                <div className="bg-white/5 rounded-lg p-2">
                  <div className="text-slate-500 mb-0.5">Empenhado</div>
                  <div className="text-emerald-400 font-medium tabular-nums">{fmtBRL(emenda.valor_empenhado || emenda.valor)}</div>
                </div>
                <div className="bg-white/5 rounded-lg p-2">
                  <div className="text-slate-500 mb-0.5">Liquidado</div>
                  <div className="text-amber-400 font-medium tabular-nums">{fmtBRL(emenda.valor_liquidado)}</div>
                </div>
                <div className="bg-white/5 rounded-lg p-2">
                  <div className="text-slate-500 mb-0.5">Pago</div>
                  <div className="text-green-400 font-medium tabular-nums">{fmtBRL(emenda.valor_pago)}</div>
                </div>
                <div className="bg-white/5 rounded-lg p-2">
                  <div className="text-slate-500 mb-0.5">Resto Inscrito</div>
                  <div className="text-slate-300 font-medium tabular-nums">{fmtBRL(emenda.valor_resto_inscrito)}</div>
                </div>
                <div className="bg-white/5 rounded-lg p-2">
                  <div className="text-slate-500 mb-0.5">Resto Cancelado</div>
                  <div className="text-red-400 font-medium tabular-nums">{fmtBRL(emenda.valor_resto_cancelado)}</div>
                </div>
                <div className="bg-white/5 rounded-lg p-2">
                  <div className="text-slate-500 mb-0.5">Resto Pago</div>
                  <div className="text-blue-400 font-medium tabular-nums">{fmtBRL(emenda.valor_resto_pago)}</div>
                </div>
              </div>

              {/* Execution rate */}
              {(emenda.valor_empenhado || emenda.valor) && (emenda.valor_pago != null) && (
                <div className="mt-2 text-xs text-slate-500">
                  Taxa de execução:{' '}
                  <span className={
                    ((emenda.valor_pago / (emenda.valor_empenhado || emenda.valor || 1)) * 100) >= 70
                      ? 'text-green-400 font-medium'
                      : ((emenda.valor_pago / (emenda.valor_empenhado || emenda.valor || 1)) * 100) >= 30
                        ? 'text-amber-400 font-medium'
                        : 'text-red-400 font-medium'
                  }>
                    {(((emenda.valor_pago) / (emenda.valor_empenhado || emenda.valor || 1)) * 100).toFixed(1)}%
                  </span>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ============================================
// SHARED COMPONENTS
// ============================================

function SortableHeader({
  label,
  column,
  currentColumn,
  direction,
  onSort,
  color = 'cyan',
}: {
  label: string;
  column: string;
  currentColumn: string | null;
  direction: SortDirection;
  onSort: (column: string) => void;
  color?: 'cyan' | 'orange' | 'green' | 'blue';
}) {
  const isActive = currentColumn === column;
  const colorMap: Record<string, string> = {
    cyan: 'text-cyan-400',
    orange: 'text-orange-400',
    green: 'text-green-400',
    blue: 'text-blue-400',
  };
  const colorClass = colorMap[color] || 'text-cyan-400';

  return (
    <th
      onClick={() => onSort(column)}
      className={`text-left p-3 font-semibold text-xs uppercase cursor-pointer select-none hover:bg-white/5 transition-colors ${colorClass}`}
    >
      <div className="flex items-center gap-1">
        {label}
        {isActive ? (
          direction === 'asc' ? (
            <ArrowUp className="h-3 w-3" />
          ) : (
            <ArrowDown className="h-3 w-3" />
          )
        ) : (
          <span className="opacity-40">↕</span>
        )}
      </div>
    </th>
  );
}

function RegimeBadge({ regime }: { regime: string | null | undefined }) {
  if (!regime) return <span className="text-slate-500">-</span>;

  const colorMap: Record<string, string> = {
    MEI: 'bg-green-500/15 text-green-400',
    SIMPLES_NACIONAL: 'bg-blue-500/15 text-blue-400',
    LUCRO_PRESUMIDO: 'bg-yellow-500/15 text-yellow-400',
    LUCRO_REAL: 'bg-red-500/15 text-red-400',
    DESCONHECIDO: 'bg-slate-500/15 text-slate-400',
  };

  const colorClass = colorMap[regime] || 'bg-slate-500/15 text-slate-400';

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {formatRegime(regime)}
    </span>
  );
}
