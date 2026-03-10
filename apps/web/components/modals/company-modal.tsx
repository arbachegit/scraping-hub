'use client';

import { useState, useRef, useEffect, useCallback, useMemo, type KeyboardEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Image from 'next/image';
import {
  X,
  Search,
  Check,
  Users,
  Loader2,
  ExternalLink,
  UserCheck,
  UserX,
  UserPlus,
  Database,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  ArrowLeft,
  ArrowUp,
  ArrowDown,
  Plus,
  Download,
  AlertTriangle,
  Globe,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import {
  searchCompany,
  getCompanyDetails,
  enrichSocios,
  approveCompany,
  listCompanies,
  checkExistingCnpjs,
  formatCnpj,
  formatRegime,
  type CompanyDetails,
  type Socio,
  type CompanyCandidate,
  type CompanySearchResponse,
} from '@/lib/api';

const PAGE_SIZE = 100;
const DEBOUNCE_MS = 300;

interface CompanyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenCnaeModal: () => void;
  onOpenRegimeModal: () => void;
  onOpenListingModal: () => void;
  userName: string;
  selectedCnae?: string;
  selectedRegime?: string;
}

export function CompanyModal({
  isOpen,
  onClose,
  onOpenCnaeModal,
  onOpenRegimeModal,
  onOpenListingModal,
  userName,
  selectedCnae,
  selectedRegime,
}: CompanyModalProps) {
  const [nome, setNome] = useState('');
  const [cidade, setCidade] = useState('');
  const [segmento, setSegmento] = useState('');
  const [regime, setRegime] = useState('');
  const [debouncedNome, setDebouncedNome] = useState('');
  const [page, setPage] = useState(1);
  const [externalResults, setExternalResults] = useState<CompanyCandidate[]>([]);
  const [externalLoading, setExternalLoading] = useState(false);
  const [externalDone, setExternalDone] = useState(false);
  const [externalMeta, setExternalMeta] = useState<{ requestId?: string; durationMs?: number; searchSource?: string; limits?: CompanySearchResponse['limits'] } | null>(null);
  const [registeredCnpjs, setRegisteredCnpjs] = useState<Set<string>>(new Set());
  const [detailCnpj, setDetailCnpj] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const [insertingCnpj, setInsertingCnpj] = useState<string | null>(null);
  const [massInserting, setMassInserting] = useState(false);
  const [sortField, setSortField] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const inputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (selectedCnae) setSegmento(selectedCnae);
  }, [selectedCnae]);

  useEffect(() => {
    if (selectedRegime) setRegime(selectedRegime);
  }, [selectedRegime]);

  useEffect(() => {
    if (isOpen) inputRef.current?.focus();
  }, [isOpen]);

  // Debounce nome for auto-search
  useEffect(() => {
    if (nome.length < 2) {
      setDebouncedNome('');
      return;
    }
    const timer = setTimeout(() => {
      setDebouncedNome(nome);
      setPage(1);
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [nome]);

  // Reset page on filter changes
  useEffect(() => {
    setPage(1);
  }, [cidade, segmento, regime]);

  // Reset external results when search params change
  useEffect(() => {
    setExternalResults([]);
    setExternalDone(false);
    setExternalMeta(null);
  }, [debouncedNome, cidade, segmento, regime]);

  // Scroll to top on page change
  useEffect(() => {
    scrollRef.current?.scrollTo(0, 0);
  }, [page]);

  // DB auto-search — searches dim_empresas directly via RPC (trigram index, 64M+ rows)
  const dbQuery = useQuery({
    queryKey: ['companies-search', debouncedNome, cidade, regime],
    queryFn: async () => {
      const result = await listCompanies({
        nome: debouncedNome || undefined,
        cidade: cidade || undefined,
        regime: regime || undefined,
        limit: 50,
        offset: 0,
      });
      if (result.requestId) {
        console.info('[DB-SEARCH]', {
          requestId: result.requestId,
          source: result.source,
          durationMs: result.durationMs,
          returnedCount: result.count,
        });
      }
      return result;
    },
    enabled: isOpen && debouncedNome.length >= 2,
  });

  // Manual external search ("Buscar Fora" button only — no auto-trigger)
  function handleSearch() {
    const campos = [
      { nome: 'Nome', valor: nome },
      { nome: 'Cidade', valor: cidade },
      { nome: 'Segmento/CNAE', valor: segmento },
      { nome: 'Regime', valor: regime },
    ];
    const preenchidos = campos.filter((c) => c.valor && c.valor.length >= 2);
    if (preenchidos.length < 1) {
      setMessage({ type: 'error', text: 'Preencha pelo menos 1 campo para buscar' });
      return;
    }
    setMessage(null);

    // Cancel any in-flight auto search
    if (abortRef.current) {
      abortRef.current.abort();
    }

    setExternalLoading(true);
    setExternalDone(false);
    setExternalResults([]);
    setExternalMeta(null);

    const payload: Record<string, string> = {};
    if (nome) payload.nome = nome;
    if (cidade) payload.cidade = cidade;
    if (segmento) payload.segmento = segmento;
    if (regime) payload.regime = regime;

    searchCompany(payload)
      .then((data) => {
        console.info('[EXTERNAL-SEARCH-MANUAL]', {
          requestId: data.requestId,
          source: data.source,
          durationMs: data.durationMs,
          searchSource: data.searchSource,
          found: data.found,
          candidateCount: data.candidates?.length || (data.company ? 1 : 0),
          limits: data.limits,
        });

        if (!data.found) {
          setMessage({ type: 'error', text: 'Nenhuma empresa encontrada nas fontes externas (Serper/BrasilAPI/Perplexity)' });
          setExternalResults([]);
        } else if (data.single_match && data.company) {
          setExternalResults([data.company]);
        } else {
          setExternalResults(data.candidates || []);
        }
        setExternalMeta({ requestId: data.requestId, durationMs: data.durationMs, searchSource: data.searchSource, limits: data.limits });

        // Check which external CNPJs are already registered
        const candidates = data.candidates || (data.company ? [data.company] : []);
        if (candidates.length > 0) {
          const cnpjs = candidates.map(c => c.cnpj).filter(Boolean);
          if (cnpjs.length > 0) {
            checkExistingCnpjs(cnpjs).then(result => {
              if (result.success) {
                setRegisteredCnpjs(prev => new Set([...prev, ...result.existing]));
              }
            }).catch(() => {});
          }
        }
      })
      .catch((error: Error) => {
        setMessage({ type: 'error', text: `Erro na busca externa: ${error.message}` });
      })
      .finally(() => {
        setExternalLoading(false);
        setExternalDone(true);
      });
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearch();
    }
  }

  function handleClose() {
    if (abortRef.current) abortRef.current.abort();
    setNome('');
    setCidade('');
    setSegmento('');
    setRegime('');
    setDebouncedNome('');
    setPage(1);
    setExternalResults([]);
    setExternalLoading(false);
    setExternalDone(false);
    setExternalMeta(null);
    setRegisteredCnpjs(new Set());
    setMessage(null);
    setDetailCnpj(null);
    setInsertingCnpj(null);
    setMassInserting(false);
    onClose();
  }

  function handleCloseDetail() {
    setDetailCnpj(null);
    queryClient.invalidateQueries({ queryKey: ['companies-search'] });
  }

  // Insert individual company
  async function handleInsertOne(cnpj: string) {
    setInsertingCnpj(cnpj);
    try {
      const detailRes = await getCompanyDetails(cnpj);
      if (detailRes.exists) {
        setRegisteredCnpjs(prev => new Set([...prev, cnpj]));
        setMessage({ type: 'info', text: `${detailRes.empresa.razao_social} ja esta cadastrada.` });
        return;
      }
      const approveRes = await approveCompany({
        empresa: detailRes.empresa,
        socios: detailRes.socios || [],
        aprovado_por: userName,
      });
      if (approveRes.success) {
        setRegisteredCnpjs(prev => new Set([...prev, cnpj]));
        setMessage({ type: 'success', text: `${detailRes.empresa.razao_social} inserida com sucesso!` });
        queryClient.invalidateQueries({ queryKey: ['companies-search'] });
      }
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Erro desconhecido';
      if (errorMsg.includes('cadastrada')) {
        setRegisteredCnpjs(prev => new Set([...prev, cnpj]));
      }
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setInsertingCnpj(null);
    }
  }

  // Mass insert all new external companies
  async function handleMassInsert() {
    const novos = mergedResults.filter(c => c.fonte !== 'interno' && !registeredCnpjs.has(c.cnpj));
    if (novos.length === 0) {
      setMessage({ type: 'info', text: 'Todas as empresas ja estao cadastradas.' });
      return;
    }

    setMassInserting(true);
    let inserted = 0;
    let alreadyExisted = 0;
    let failed = 0;

    for (const candidate of novos) {
      try {
        const detailRes = await getCompanyDetails(candidate.cnpj);
        if (detailRes.exists) {
          alreadyExisted++;
          setRegisteredCnpjs(prev => new Set([...prev, candidate.cnpj]));
          continue;
        }
        const approveRes = await approveCompany({
          empresa: detailRes.empresa,
          socios: detailRes.socios || [],
          aprovado_por: userName,
        });
        if (approveRes.success) {
          inserted++;
          setRegisteredCnpjs(prev => new Set([...prev, candidate.cnpj]));
        } else {
          failed++;
        }
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : '';
        if (errorMsg.includes('cadastrada')) {
          alreadyExisted++;
          setRegisteredCnpjs(prev => new Set([...prev, candidate.cnpj]));
        } else {
          failed++;
        }
      }
    }

    setMassInserting(false);
    setMessage({
      type: inserted > 0 ? 'success' : 'info',
      text: `Inseridas: ${inserted} | Ja existiam: ${alreadyExisted} | Falhas: ${failed}`,
    });
    queryClient.invalidateQueries({ queryKey: ['companies-search'] });
  }

  // Merge DB + external results with dedup by CNPJ
  const dbResults = dbQuery.data?.empresas || [];
  const dbTotal = dbQuery.data?.total || 0;
  const totalPages = Math.ceil(dbTotal / PAGE_SIZE);

  const mergedResults = useMemo(() => {
    const dbMapped: CompanyCandidate[] = dbResults.map((e) => ({
      cnpj: e.cnpj,
      cnpj_formatted: formatCnpj(e.cnpj),
      razao_social: e.razao_social,
      nome_fantasia: e.nome_fantasia,
      localizacao: [e.cidade, e.estado].filter(Boolean).join(' - ') || undefined,
      cnae_principal: e.cnae_principal,
      cnae_descricao: e.cnae_descricao,
      descricao_classe: e.descricao_classe,
      regime_tributario: e.regime_tributario,
      fonte: 'interno' as const,
    }));

    const dbCnpjs = new Set(dbMapped.map(e => e.cnpj));

    // Only show external results on page 1
    const externalNew = page === 1
      ? externalResults.filter(c => c.cnpj && !dbCnpjs.has(c.cnpj))
      : [];

    return [...dbMapped, ...externalNew];
  }, [dbResults, externalResults, page]);

  const sortedResults = useMemo(() => {
    if (!sortField) return mergedResults;
    return [...mergedResults].sort((a, b) => {
      const aRec = a as unknown as Record<string, unknown>;
      const bRec = b as unknown as Record<string, unknown>;
      const valA = String(aRec[sortField] ?? '').toLowerCase();
      const valB = String(bRec[sortField] ?? '').toLowerCase();
      return sortDirection === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    });
  }, [mergedResults, sortField, sortDirection]);

  function handleResultSort(column: string) {
    if (sortField === column) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(column);
      setSortDirection('asc');
    }
  }

  const countDb = mergedResults.filter(c => c.fonte === 'interno' || registeredCnpjs.has(c.cnpj)).length;
  const countNew = mergedResults.filter(c => c.fonte !== 'interno' && !registeredCnpjs.has(c.cnpj)).length;

  const isLoading = dbQuery.isFetching && dbResults.length === 0;
  const showBadges = debouncedNome.length >= 2;

  if (!isOpen) return null;

  return (
    <>
      {/* Modal 1: Buscar Empresa */}
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
        <div className="w-[1200px] max-w-[95vw] flex flex-col rounded-2xl border border-cyan-500/15 bg-gradient-to-b from-[#0f1629] to-[#0a0e1a] shadow-2xl" style={{ maxHeight: '90vh' }}>
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 flex-shrink-0">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-1 h-5 bg-gradient-to-b from-cyan-400 to-blue-500 rounded" />
              Buscar Empresa
            </h2>
            <button
              onClick={handleClose}
              className="flex items-center justify-center w-9 h-9 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-400 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Search Form (fixed) */}
          <div className="flex-shrink-0 px-6 pt-4 pb-3 space-y-3 border-b border-white/5">
            <div className="flex gap-3">
              <Input
                ref={inputRef}
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Razao Social (min. 2 letras para buscar)"
                className="flex-[2]"
              />
              <Input
                value={cidade}
                onChange={(e) => setCidade(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Cidade / UF"
                className="flex-1"
              />
            </div>
            <div className="flex gap-3">
              <div className="relative flex-1">
                <Input
                  value={segmento}
                  onChange={(e) => setSegmento(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Segmento / CNAE"
                  className="pr-24"
                />
                <button
                  type="button"
                  onClick={onOpenCnaeModal}
                  className="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1.5 text-xs font-semibold bg-purple-500/15 border border-purple-500 text-purple-400 rounded-md hover:bg-purple-500 hover:text-white transition-colors"
                >
                  Listar CNAE
                </button>
              </div>
              <div className="relative flex-1">
                <Input
                  value={regime}
                  onChange={(e) => setRegime(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Regime Tributario"
                  className="pr-20"
                />
                <button
                  type="button"
                  onClick={onOpenRegimeModal}
                  className="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1.5 text-xs font-semibold bg-green-500/15 border border-green-500/30 text-green-400 rounded-md hover:bg-green-500 hover:text-white transition-colors"
                >
                  Listar
                </button>
              </div>
            </div>
            <div className="flex gap-3 items-center">
              <Button
                onClick={handleSearch}
                disabled={externalLoading}
                variant="outline"
                className="h-12 px-6 border-amber-500/30 text-amber-400 hover:bg-amber-500/15"
              >
                {externalLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Globe className="h-4 w-4 mr-2" />
                )}
                Buscar Fora
              </Button>

              {/* Mass insert button */}
              {countNew > 0 && (
                <Button
                  onClick={handleMassInsert}
                  disabled={massInserting}
                  className="h-12 px-4 bg-green-500/15 border-2 border-green-500 text-green-400 hover:bg-green-500 hover:text-white"
                >
                  {massInserting ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Download className="h-4 w-4 mr-2" />
                  )}
                  {massInserting ? 'Inserindo...' : `Inserir ${countNew} novos`}
                </Button>
              )}

              {/* Badges */}
              {showBadges && (
                <div className="flex gap-2 ml-auto">
                  <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-500/10 border border-slate-500/20 text-slate-300 text-xs font-medium">
                    Total: {mergedResults.length}
                  </span>
                  <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-xs font-medium">
                    <Database className="h-3 w-3" />
                    {countDb}
                  </span>
                  {countNew > 0 && (
                    <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-medium">
                      <Sparkles className="h-3 w-3" />
                      {countNew}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Scrollable Results Area */}
          <div
            ref={scrollRef}
            className="flex-1 min-h-0 max-h-[70vh] overflow-y-auto overscroll-contain"
          >
            <div className="p-6">
              {/* Message */}
              {message && (
                <div
                  className={cn(
                    'p-3 rounded-lg mb-4 text-sm',
                    message.type === 'success'
                      ? 'bg-green-500/10 border border-green-500/30 text-green-400'
                      : message.type === 'info'
                        ? 'bg-blue-500/10 border border-blue-500/30 text-blue-400'
                        : 'bg-red-500/10 border border-red-500/30 text-red-400'
                  )}
                >
                  {message.text}
                </div>
              )}

              {/* External search limits info */}
              {externalMeta?.limits && (
                <div className="flex items-center gap-2 p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/15 text-amber-400/80 text-xs mb-4">
                  <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
                  <span>
                    Max. {externalMeta.limits.serperMaxResults} resultados externos.
                    {' '}{externalMeta.limits.note}
                    {externalMeta.durationMs && ` (${externalMeta.durationMs}ms)`}
                  </span>
                </div>
              )}

              {/* DB Loading */}
              {isLoading && (
                <div className="flex flex-col items-center justify-center py-10 text-slate-400">
                  <Loader2 className="h-10 w-10 animate-spin text-cyan-400 mb-4" />
                  <span>Buscando no banco...</span>
                </div>
              )}

              {/* Unified Results Table */}
              {debouncedNome.length >= 2 && !isLoading && mergedResults.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="bg-cyan-500/5">
                        <ResultSortHeader label="Razao Social" column="razao_social" currentColumn={sortField} direction={sortDirection} onSort={handleResultSort} />
                        <ResultSortHeader label="CNPJ" column="cnpj" currentColumn={sortField} direction={sortDirection} onSort={handleResultSort} />
                        <ResultSortHeader label="CNAE" column="cnae_principal" currentColumn={sortField} direction={sortDirection} onSort={handleResultSort} />
                        <ResultSortHeader label="Descricao" column="cnae_descricao" currentColumn={sortField} direction={sortDirection} onSort={handleResultSort} />
                        <ResultSortHeader label="Classe" column="descricao_classe" currentColumn={sortField} direction={sortDirection} onSort={handleResultSort} />
                        <ResultSortHeader label="Regime" column="regime_tributario" currentColumn={sortField} direction={sortDirection} onSort={handleResultSort} />
                        <th className="text-left p-3 text-cyan-400 font-semibold text-xs uppercase w-20">Acao</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedResults.map((c) => {
                        const isRegistered = c.fonte === 'interno' || registeredCnpjs.has(c.cnpj);
                        return (
                          <tr
                            key={c.cnpj}
                            onClick={() => setDetailCnpj(c.cnpj)}
                            className="border-b border-white/5 hover:bg-cyan-500/5 transition-colors cursor-pointer"
                          >
                            <td className="p-2.5 min-w-0 max-w-[220px]">
                              <div className="truncate text-slate-200 font-medium text-xs">
                                {c.razao_social || 'Sem nome'}
                              </div>
                            </td>
                            <td className="p-2.5 whitespace-nowrap">
                              <span className="text-slate-300 text-xs font-mono">{c.cnpj_formatted}</span>
                            </td>
                            <td className="p-2.5 whitespace-nowrap">
                              {c.cnae_principal ? (
                                <span className="text-slate-400 text-xs font-mono">{c.cnae_principal}</span>
                              ) : (
                                <span className="text-slate-600">{'\u2014'}</span>
                              )}
                            </td>
                            <td className="p-2.5 min-w-0 max-w-[180px]">
                              {c.cnae_descricao ? (
                                <div className="truncate text-slate-300 text-xs">{c.cnae_descricao}</div>
                              ) : (
                                <span className="text-slate-600">{'\u2014'}</span>
                              )}
                            </td>
                            <td className="p-2.5 min-w-0 max-w-[160px]">
                              {c.descricao_classe ? (
                                <div className="truncate text-slate-300 text-xs">{c.descricao_classe}</div>
                              ) : (
                                <span className="text-slate-600">{'\u2014'}</span>
                              )}
                            </td>
                            <td className="p-2.5">
                              {c.regime_tributario ? (
                                <span className="inline-flex items-center px-2 py-0.5 text-[10px] font-medium rounded bg-slate-500/15 text-slate-300 whitespace-nowrap">
                                  {formatRegime(c.regime_tributario)}
                                </span>
                              ) : (
                                <span className="text-slate-600">{'\u2014'}</span>
                              )}
                            </td>
                            <td className="p-2.5">
                              {!isRegistered ? (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleInsertOne(c.cnpj);
                                  }}
                                  disabled={insertingCnpj === c.cnpj}
                                  className="flex items-center gap-1 px-2.5 py-1 text-xs font-semibold bg-green-500/15 border border-green-500/30 text-green-400 rounded-lg hover:bg-green-500 hover:text-white transition-colors disabled:opacity-50 whitespace-nowrap"
                                >
                                  {insertingCnpj === c.cnpj ? (
                                    <Loader2 className="h-3 w-3 animate-spin" />
                                  ) : (
                                    <Plus className="h-3 w-3" />
                                  )}
                                  Inserir
                                </button>
                              ) : (
                                <span className="flex items-center gap-1 text-xs text-slate-500 whitespace-nowrap">
                                  <Check className="h-3 w-3" />
                                  OK
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* External search loading indicator (below DB results) */}
              {externalLoading && debouncedNome.length >= 2 && (
                <div className="flex items-center gap-2 mt-4 p-3 rounded-lg bg-cyan-500/5 border border-cyan-500/15 text-cyan-400/80 text-xs">
                  <Loader2 className="h-3.5 w-3.5 animate-spin flex-shrink-0" />
                  <span>Buscando fontes externas (Serper + BrasilAPI)...</span>
                </div>
              )}

              {/* DB search metadata */}
              {debouncedNome.length >= 2 && !isLoading && mergedResults.length > 0 && dbQuery.data?.requestId && (
                <div className="text-[11px] text-slate-600 mt-3 text-right">
                  Fonte: Supabase (dim_empresas) | {dbQuery.data.durationMs}ms | Mostrando {dbResults.length} de ~{dbTotal}
                  {externalMeta?.durationMs && ` | Externo: ${externalMeta.durationMs}ms`}
                </div>
              )}

              {/* Empty state */}
              {!isLoading &&
                debouncedNome.length >= 2 &&
                mergedResults.length === 0 &&
                !dbQuery.isLoading &&
                !externalLoading && (
                  <div className="text-center py-10 text-slate-500">
                    <p>Nenhuma empresa encontrada para &quot;{debouncedNome}&quot;.</p>
                    {!externalDone && (
                      <p className="mt-2 text-sm">Use o botao <strong>&quot;Buscar Fora&quot;</strong> para pesquisar via Serper/BrasilAPI/Perplexity.</p>
                    )}
                  </div>
                )}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-3 mt-6 pt-4 border-t border-white/5">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="h-9"
                  >
                    <ChevronLeft className="h-4 w-4 mr-1" />
                    Anterior
                  </Button>
                  <span className="text-sm text-slate-400">
                    Pagina {page} de {totalPages} (~{dbTotal} total)
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="h-9"
                  >
                    Proxima
                    <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Modal 2: Detalhe da Empresa (empilhado) */}
      {detailCnpj && (
        <CompanyDetailModal cnpj={detailCnpj} onClose={handleCloseDetail} userName={userName} />
      )}
    </>
  );
}

// ============================================
// Result Sort Header
// ============================================

function ResultSortHeader({
  label,
  column,
  currentColumn,
  direction,
  onSort,
}: {
  label: string;
  column: string;
  currentColumn: string | null;
  direction: 'asc' | 'desc';
  onSort: (column: string) => void;
}) {
  const isActive = currentColumn === column;
  return (
    <th
      onClick={() => onSort(column)}
      className="text-left p-3 text-cyan-400 font-semibold text-xs uppercase cursor-pointer select-none hover:bg-white/5 transition-colors"
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
          <span className="opacity-40">{'\u2195'}</span>
        )}
      </div>
    </th>
  );
}

// ============================================
// Company Detail Modal (stacked - Modal 2)
// ============================================

function CompanyDetailModal({
  cnpj,
  onClose,
  userName,
}: {
  cnpj: string;
  onClose: () => void;
  userName: string;
}) {
  const [showSocios, setShowSocios] = useState(false);
  const [enrichedSocios, setEnrichedSocios] = useState<Socio[] | null>(null);
  const [isApproved, setIsApproved] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const detailsQuery = useQuery({
    queryKey: ['company-detail', cnpj],
    queryFn: () => getCompanyDetails(cnpj),
    enabled: !!cnpj,
  });

  const enrichMutation = useMutation({
    mutationFn: enrichSocios,
    onSuccess: (data) => {
      if (data.success && data.socios) {
        setEnrichedSocios(data.socios);
        setShowSocios(true);
      }
    },
    onError: (error: Error) => {
      setMessage({ type: 'error', text: error.message });
    },
  });

  const approveMutation = useMutation({
    mutationFn: approveCompany,
    onSuccess: (data) => {
      if (data.success) {
        setMessage({
          type: 'success',
          text: `Empresa cadastrada com sucesso! ${data.socios?.length || 0} socio(s) adicionado(s)`,
        });
        setIsApproved(true);
      }
    },
    onError: (error: Error) => {
      setMessage({ type: 'error', text: error.message });
    },
  });

  const data = detailsQuery.data;
  const empresa = data?.empresa;
  const isExisting = data?.exists || isApproved;
  const socios = data?.socios || [];
  const sociosAtivos = data?.socios_ativos || [];
  const sociosInativos = data?.socios_inativos || [];
  const sociosNovos = data?.socios_novos || [];
  const displaySocios = enrichedSocios || socios;

  function handleLoadSocios() {
    if (!empresa || socios.length === 0) return;
    enrichMutation.mutate({
      socios: socios,
      empresa_nome: empresa.nome_fantasia || empresa.razao_social,
    });
  }

  function handleApprove() {
    if (!empresa) return;
    approveMutation.mutate({
      empresa: empresa,
      socios: displaySocios,
      aprovado_por: userName,
    });
  }

  return (
    <div className="fixed inset-0 z-[55] flex items-center justify-center bg-black/60">
      <div className="w-[1000px] max-w-[95vw] flex flex-col rounded-2xl border border-cyan-500/15 bg-gradient-to-b from-[#0f1629] to-[#0a0e1a] shadow-2xl" style={{ maxHeight: '90vh' }}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 flex-shrink-0">
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <span className="w-1 h-5 bg-gradient-to-b from-cyan-400 to-blue-500 rounded" />
            Detalhes da Empresa
          </h2>
          <button
            onClick={onClose}
            className="flex items-center justify-center w-9 h-9 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-400 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 min-h-0 max-h-[70vh] overflow-y-auto overscroll-contain p-6">
          {detailsQuery.isLoading ? (
            <div className="flex flex-col items-center justify-center py-10 text-slate-400">
              <Loader2 className="h-10 w-10 animate-spin text-cyan-400 mb-4" />
              <span>Carregando detalhes via BrasilAPI + Apollo...</span>
            </div>
          ) : detailsQuery.isError ? (
            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">
              Erro ao carregar detalhes: {(detailsQuery.error as Error).message}
            </div>
          ) : empresa ? (
            <div className="space-y-4">
              {/* Messages */}
              {message && (
                <div
                  className={cn(
                    'p-4 rounded-lg',
                    message.type === 'success'
                      ? 'bg-green-500/10 border border-green-500/30 text-green-400'
                      : 'bg-red-500/10 border border-red-500/30 text-red-400'
                  )}
                >
                  {message.text}
                </div>
              )}

              {isExisting && !isApproved && (
                <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-sm">
                  Empresa ja cadastrada no sistema. Socios cruzados com QSA atual da Receita Federal.
                </div>
              )}

              {/* Company Data */}
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                <DetailRow label="CNPJ" value={formatCnpj(empresa.cnpj)} />
                <DetailRow label="Razao Social" value={empresa.razao_social} />
                <DetailRow label="Nome Fantasia" value={empresa.nome_fantasia} />
                <DetailRow
                  label="CNAE"
                  value={`${empresa.cnae_principal || '-'} - ${empresa.cnae_descricao || ''}`}
                />
                <DetailRow label="Porte" value={empresa.porte} />
                <DetailRow label="Situacao" value={empresa.situacao_cadastral} />
                <DetailRow
                  label="Capital Social"
                  value={
                    empresa.capital_social
                      ? `R$ ${Number(empresa.capital_social).toLocaleString('pt-BR')}`
                      : '-'
                  }
                />
                <DetailRow
                  label="Endereco"
                  value={[
                    empresa.logradouro,
                    empresa.numero,
                    empresa.bairro,
                    empresa.cidade,
                    empresa.estado,
                  ]
                    .filter(Boolean)
                    .join(', ')}
                />
                <DetailRow label="Telefone" value={empresa.telefone_1} />
                <DetailRow label="Email" value={empresa.email} />
                <DetailRow
                  label="Website"
                  value={
                    empresa.website && empresa.website !== 'NAO_POSSUI' ? (
                      <a
                        href={empresa.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-cyan-400 hover:underline inline-flex items-center gap-1"
                      >
                        {empresa.website} <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : (
                      '-'
                    )
                  }
                />
                <DetailRow
                  label="LinkedIn"
                  value={
                    empresa.linkedin && empresa.linkedin !== 'NAO_POSSUI' ? (
                      <a
                        href={empresa.linkedin}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-cyan-400 hover:underline inline-flex items-center gap-1"
                      >
                        Ver perfil <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : empresa.linkedin === 'NAO_POSSUI' ? (
                      <span className="text-red-400">Nao possui</span>
                    ) : (
                      <span className="text-slate-500">Nao informado</span>
                    )
                  }
                />

                {/* Socios - Existing company (categorized) */}
                {isExisting &&
                  !isApproved &&
                  (sociosAtivos.length > 0 ||
                    sociosInativos.length > 0 ||
                    sociosNovos.length > 0) && (
                    <div className="mt-6 pt-5 border-t border-white/5 space-y-5">
                      {sociosAtivos.length > 0 && (
                        <div>
                          <div className="text-slate-400 text-sm font-semibold mb-3 flex items-center gap-2">
                            <UserCheck className="h-4 w-4 text-green-400" />
                            Socios Ativos
                            <span className="bg-green-500/15 text-green-400 px-2 py-0.5 rounded text-xs">
                              {sociosAtivos.length}
                            </span>
                          </div>
                          <div className="space-y-3">
                            {sociosAtivos.map((s, i) => (
                              <SocioCard key={`ativo-${i}`} socio={s} variant="ativo" />
                            ))}
                          </div>
                        </div>
                      )}
                      {sociosInativos.length > 0 && (
                        <div>
                          <div className="text-slate-400 text-sm font-semibold mb-3 flex items-center gap-2">
                            <UserX className="h-4 w-4 text-red-400" />
                            Ex-Socios
                            <span className="bg-red-500/15 text-red-400 px-2 py-0.5 rounded text-xs">
                              {sociosInativos.length}
                            </span>
                          </div>
                          <div className="space-y-3">
                            {sociosInativos.map((s, i) => (
                              <SocioCard key={`inativo-${i}`} socio={s} variant="inativo" />
                            ))}
                          </div>
                        </div>
                      )}
                      {sociosNovos.length > 0 && (
                        <div>
                          <div className="text-slate-400 text-sm font-semibold mb-3 flex items-center gap-2">
                            <UserPlus className="h-4 w-4 text-blue-400" />
                            Novos Socios (QSA)
                            <span className="bg-blue-500/15 text-blue-400 px-2 py-0.5 rounded text-xs">
                              {sociosNovos.length}
                            </span>
                          </div>
                          <div className="space-y-3">
                            {sociosNovos.map((s, i) => (
                              <SocioCard key={`novo-${i}`} socio={s} variant="novo" />
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                {/* Socios - New company */}
                {!isExisting && showSocios && displaySocios.length > 0 && (
                  <div className="mt-6 pt-5 border-t border-white/5">
                    <div className="text-slate-400 text-sm font-semibold mb-3 flex items-center gap-2">
                      Socios{' '}
                      <span className="bg-purple-500/15 text-purple-400 px-2 py-0.5 rounded text-xs">
                        {displaySocios.length}
                      </span>
                    </div>
                    <div className="space-y-3">
                      {displaySocios.map((s, i) => (
                        <SocioCard key={`socio-${i}`} socio={s} variant="default" />
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col gap-3">
                {!isExisting && socios.length > 0 && !showSocios && (
                  <Button
                    onClick={handleLoadSocios}
                    disabled={enrichMutation.isPending}
                    className="h-12 w-full bg-purple-500/15 border-2 border-purple-500 text-purple-400 hover:bg-purple-500 hover:text-white"
                  >
                    {enrichMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <Users className="h-4 w-4 mr-2" />
                    )}
                    {enrichMutation.isPending
                      ? 'Buscando LinkedIn...'
                      : `Ver Socios (${socios.length})`}
                  </Button>
                )}

                {isExisting ? (
                  <Button
                    disabled
                    className="h-12 w-full bg-slate-500/15 border-2 border-slate-500/30 text-slate-400 cursor-not-allowed"
                  >
                    <Check className="h-4 w-4 mr-2" />
                    Ja Cadastrada
                  </Button>
                ) : (
                  <Button
                    onClick={handleApprove}
                    disabled={approveMutation.isPending || isApproved}
                    className="h-12 w-full bg-green-500/15 border-2 border-green-500 text-green-400 hover:bg-green-500 hover:text-white"
                  >
                    {approveMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <Check className="h-4 w-4 mr-2" />
                    )}
                    {approveMutation.isPending ? 'Salvando...' : 'Aprovar e Cadastrar'}
                  </Button>
                )}

                <Button onClick={onClose} variant="outline" className="h-12 w-full">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Voltar
                </Button>
              </div>

              {/* Error message */}
              {message?.type === 'error' && (
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">
                  {message.text}
                </div>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

// ============================================
// Shared Components
// ============================================

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex py-2.5 border-b border-white/[0.04] last:border-b-0">
      <span className="text-slate-500 text-sm font-medium w-32 flex-shrink-0">{label}</span>
      <span className="text-slate-300 text-sm flex-1">{value || '-'}</span>
    </div>
  );
}

const SOCIO_VARIANT_STYLES = {
  ativo: { bg: 'bg-green-500/15', text: 'text-green-400', border: 'border-green-500/20' },
  inativo: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20' },
  novo: { bg: 'bg-blue-500/15', text: 'text-blue-400', border: 'border-blue-500/20' },
  default: { bg: 'bg-purple-500/15', text: 'text-purple-400', border: 'border-white/5' },
} as const;

function SocioCard({
  socio: s,
  variant,
}: {
  socio: Socio;
  variant: keyof typeof SOCIO_VARIANT_STYLES;
}) {
  const style = SOCIO_VARIANT_STYLES[variant];

  return (
    <div className={cn('flex gap-3 p-4 bg-white/[0.02] border rounded-xl', style.border)}>
      <div
        className={cn(
          'w-11 h-11 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden',
          style.bg
        )}
      >
        {s.foto_url ? (
          <Image
            src={s.foto_url}
            alt={s.nome}
            width={44}
            height={44}
            className="w-full h-full object-cover"
            unoptimized
          />
        ) : (
          <span className={cn('font-semibold', style.text)}>
            {s.nome?.charAt(0).toUpperCase() || '?'}
          </span>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-slate-200 font-semibold text-sm truncate">{s.nome}</span>
          {variant === 'ativo' && (
            <span className="flex-shrink-0 px-1.5 py-0.5 text-[10px] font-bold rounded bg-green-500/15 text-green-400 border border-green-500/30">
              Ativo
            </span>
          )}
          {variant === 'inativo' && (
            <span className="flex-shrink-0 px-1.5 py-0.5 text-[10px] font-bold rounded bg-red-500/10 text-red-400 border border-red-500/30">
              Saiu
            </span>
          )}
          {variant === 'novo' && (
            <span className="flex-shrink-0 px-1.5 py-0.5 text-[10px] font-bold rounded bg-blue-500/15 text-blue-400 border border-blue-500/30">
              Novo no QSA
            </span>
          )}
        </div>
        <div className="text-slate-500 text-sm">{s.qualificacao || s.cargo || 'Socio'}</div>
        <div className="flex flex-wrap gap-2 text-sm mt-1">
          {s.cpf && (
            <span className="text-slate-500">
              CPF: ***{s.cpf.slice(-6, -2)}**-{s.cpf.slice(-2)}
            </span>
          )}
          {s.data_entrada && <span className="text-slate-500">Entrada: {s.data_entrada}</span>}
          {s.email && <span className="text-slate-500">{s.email}</span>}
          {s.linkedin && s.linkedin !== 'NAO_POSSUI' ? (
            <a
              href={s.linkedin}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-400 hover:underline"
            >
              LinkedIn
            </a>
          ) : s.linkedin === 'NAO_POSSUI' ? (
            <span className="text-red-400">Nao possui LinkedIn</span>
          ) : variant !== 'novo' ? (
            <span className="text-red-400">Sem LinkedIn</span>
          ) : null}
        </div>
        {s.headline && <div className="text-slate-400 text-xs mt-1">{s.headline}</div>}
      </div>
    </div>
  );
}
