'use client';

import { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { isAuthenticated } from '@/lib/auth';
import { expandGraphNode, searchGraphEntities, type GraphExploreResponse, type GraphSearchResult } from '@/lib/api';
import { GraphCanvas } from '@/components/graph/graph-canvas';
import {
  LayoutDashboard,
  Network,
  Database,
  Loader2,
  AlertCircle,
  Search,
  X,
} from 'lucide-react';

const ENTITY_COLORS: Record<string, string> = {
  empresa: '#ef4444',
  pessoa: '#f97316',
  politico: '#3b82f6',
  mandato: '#a855f7',
  emenda: '#06b6d4',
  noticia: '#22c55e',
};

const ENTITY_LABELS: Record<string, string> = {
  empresa: 'Empresa',
  pessoa: 'Pessoa',
  politico: 'Politico',
  mandato: 'Mandato',
  emenda: 'Emenda',
  noticia: 'Noticia',
};

export default function GraphPage() {
  const router = useRouter();

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [graphData, setGraphData] = useState<GraphExploreResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Autocomplete state
  const [suggestions, setSuggestions] = useState<GraphSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Stabilize canvas data to avoid infinite re-renders
  const canvasData = useMemo(() => {
    if (!graphData || graphData.nodes.length === 0) return null;
    return { nodes: graphData.nodes as any, edges: graphData.edges as any };
  }, [graphData]);

  // Auth check
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/');
    }
  }, [router]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Live search after 2 characters
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (value.trim().length < 2) {
      setSuggestions([]);
      setShowDropdown(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setIsSearching(true);
      try {
        const data = await searchGraphEntities(value.trim(), 200);
        setSuggestions(data.results || []);
        setShowDropdown(true);
      } catch {
        setSuggestions([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);
  }, []);

  // Select a suggestion from the dropdown — uses expand endpoint directly
  const handleSelectSuggestion = useCallback(async (result: GraphSearchResult) => {
    setSearchQuery(result.label);
    setShowDropdown(false);
    setSuggestions([]);
    setIsLoading(true);
    setError(null);
    setGraphData(null);

    try {
      const data = await expandGraphNode(result.type, result.id);
      // Normalize nodes: ensure hop is always inside data (backend may put it at top level or inside data)
      const nodes = (data.nodes || []).map((n: any) => ({
        ...n,
        data: {
          ...n.data,
          hop: n.data?.hop ?? n.hop ?? 1,
        },
      }));
      const edges = data.edges || [];
      const statsMap: Record<string, number> = {};
      for (const n of nodes) {
        const t = (n as any).type || 'unknown';
        statsMap[t] = (statsMap[t] || 0) + 1;
      }
      const adapted: GraphExploreResponse = {
        success: true,
        nodes,
        edges,
        center: (data as any).center || { id: result.id, type: result.type, label: result.label },
        stats: {
          total_nodes: nodes.length,
          total_edges: edges.length,
          empresas: statsMap['empresa'] || 0,
          socios: statsMap['pessoa'] || 0,
          noticias: statsMap['noticia'] || 0,
          politicos: statsMap['politico'] || 0,
          emendas: statsMap['emenda'] || 0,
          mandatos: statsMap['mandato'] || 0,
        },
      };
      setGraphData(adapted);
      if (nodes.length === 0) {
        setError(`Nenhuma conexao encontrada para "${result.label}"`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao explorar grafo');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleClear = useCallback(() => {
    setSearchQuery('');
    setSuggestions([]);
    setShowDropdown(false);
  }, []);

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  return (
    <div className="h-screen flex flex-col bg-[#0a0e1a] overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 bg-[#0f1629]/80 backdrop-blur-xl border-b border-cyan-500/10 z-50 relative">
        <div className="flex items-center justify-between px-4 lg:px-6 py-2.5">
          <div className="flex items-center gap-3">
            <picture>
              <source srcSet="/iconsai-logo.webp" type="image/webp" />
              <img
                src="/iconsai-logo.png"
                alt="Iconsai"
                className="h-8 w-auto"
              />
            </picture>
            <h1 className="text-lg font-bold bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent hidden sm:block">
              Graph Explorer
            </h1>
          </div>

          {/* Search Bar with Autocomplete */}
          <div ref={dropdownRef} className="relative flex-1 max-w-lg mx-4">
            <div className="flex items-center flex-1 bg-slate-800/60 border border-cyan-500/20 rounded-lg px-3 py-1.5 focus-within:border-cyan-500/50 transition-colors">
              <Search className="h-4 w-4 text-slate-400 flex-shrink-0" />
              <input
                type="text"
                value={searchQuery}
                onChange={handleInputChange}
                onFocus={() => suggestions.length > 0 && setShowDropdown(true)}
                placeholder="Buscar empresas, pessoas, politicos, noticias..."
                className="flex-1 bg-transparent text-sm text-slate-200 placeholder-slate-500 outline-none px-2"
              />
              {isSearching && (
                <Loader2 className="h-3.5 w-3.5 text-cyan-400 animate-spin flex-shrink-0" />
              )}
              {searchQuery && !isSearching && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="flex-shrink-0 text-slate-500 hover:text-slate-300"
                >
                  <X size={14} />
                </button>
              )}
            </div>

            {/* Autocomplete Dropdown — grouped by type with section headers */}
            {showDropdown && suggestions.length > 0 && (() => {
              // Group suggestions by type, preserving order
              const grouped: Record<string, typeof suggestions> = {};
              const typeOrder: string[] = [];
              for (const r of suggestions) {
                if (!grouped[r.type]) {
                  grouped[r.type] = [];
                  typeOrder.push(r.type);
                }
                grouped[r.type].push(r);
              }
              return (
                <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-96 overflow-y-auto rounded-lg border border-cyan-500/20 bg-[#0f1629] shadow-2xl">
                  {typeOrder.map((type) => (
                    <div key={type}>
                      <div className="sticky top-0 z-10 flex items-center gap-2 bg-[#0d1220] px-3 py-1.5 border-b border-slate-800/50">
                        <div
                          className="h-2 w-2 flex-shrink-0 rounded-full"
                          style={{ backgroundColor: ENTITY_COLORS[type] || '#6b7280' }}
                        />
                        <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: ENTITY_COLORS[type] || '#6b7280' }}>
                          {ENTITY_LABELS[type] || type} ({grouped[type].length})
                        </span>
                      </div>
                      <ul>
                        {grouped[type].map((result) => (
                          <li key={`${result.type}-${result.id}`}>
                            <button
                              type="button"
                              onMouseDown={(e) => e.preventDefault()}
                              onClick={() => handleSelectSuggestion(result)}
                              className="flex w-full items-center gap-3 px-3 py-2 text-left cursor-pointer transition-colors hover:bg-cyan-500/10 border-b border-slate-800/30 last:border-b-0"
                            >
                              <div className="min-w-0 flex-1">
                                <div className="text-sm text-slate-200 truncate">{result.label}</div>
                                {result.subtitle && (
                                  <div className="text-xs text-slate-500 truncate">{result.subtitle}</div>
                                )}
                              </div>
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              );
            })()}

            {/* No results message */}
            {showDropdown && suggestions.length === 0 && !isSearching && searchQuery.trim().length >= 2 && (
              <div className="absolute left-0 right-0 top-full z-50 mt-1 rounded-lg border border-cyan-500/20 bg-[#0f1629] px-3 py-3 text-xs text-slate-500 text-center">
                Nenhum resultado para &quot;{searchQuery.trim()}&quot;
              </div>
            )}
          </div>

          <nav className="flex items-center gap-2">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 h-9 px-3 bg-slate-400/10 border border-slate-400/20 text-slate-300 rounded-lg text-xs font-medium hover:bg-slate-400/20 transition-colors"
            >
              <LayoutDashboard className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Dashboard</span>
            </Link>
            <Link
              href="/db"
              className="inline-flex items-center gap-1.5 h-9 px-3 bg-slate-400/10 border border-slate-400/20 text-slate-300 rounded-lg text-xs font-medium hover:bg-slate-400/20 transition-colors"
            >
              <Database className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">DB</span>
            </Link>
            <span className="inline-flex items-center gap-1.5 h-9 px-3 bg-cyan-500/15 border border-cyan-500/50 text-cyan-400 rounded-lg text-xs font-semibold">
              <Network className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Graph</span>
            </span>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 relative">
          {/* Empty State */}
          {!graphData && !isLoading && !error && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="flex flex-col items-center gap-4 text-center max-w-sm">
                <Network className="h-16 w-16 text-cyan-500/30" />
                <h2 className="text-lg font-semibold text-slate-300">Graph Explorer</h2>
                <p className="text-sm text-slate-500">
                  Digite o nome de uma empresa, pessoa, politico ou noticia para visualizar conexoes.
                </p>
              </div>
            </div>
          )}

          {/* Loading */}
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-[#0a0e1a]/80 z-10">
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="h-8 w-8 text-cyan-400 animate-spin" />
                <span className="text-sm text-slate-400">
                  Explorando conexoes...
                </span>
              </div>
            </div>
          )}

          {/* Error */}
          {error && !isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-[#0a0e1a]/80 z-10">
              <div className="flex flex-col items-center gap-4 max-w-sm text-center">
                <AlertCircle className="h-10 w-10 text-red-400" />
                <p className="text-sm text-slate-300">{error}</p>
              </div>
            </div>
          )}

          {/* Graph Canvas */}
          {canvasData && !isLoading && !error && (
            <GraphCanvas
              initialData={canvasData}
              className="h-full"
            />
          )}

          {/* Stats Badge */}
          {graphData && graphData.stats && !isLoading && !error && (
            <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
              <div className="bg-[#0f1629]/90 border border-cyan-500/20 rounded-lg px-3 py-1.5 flex items-center gap-2 flex-wrap text-xs">
                <span className="text-slate-400">Centro: <span className="text-cyan-400 font-medium">{graphData.center?.label}</span></span>
                <span className="text-slate-600">|</span>
                {graphData.stats.empresas > 0 && <span className="text-red-400">{graphData.stats.empresas} empresa</span>}
                {graphData.stats.socios > 0 && <span className="text-orange-400">{graphData.stats.socios} socios</span>}
                {graphData.stats.politicos > 0 && <span className="text-blue-400">{graphData.stats.politicos} politicos</span>}
                {graphData.stats.mandatos > 0 && <span className="text-purple-400">{graphData.stats.mandatos} mandatos</span>}
                {graphData.stats.emendas > 0 && <span className="text-cyan-400">{graphData.stats.emendas} emendas</span>}
                {graphData.stats.noticias > 0 && <span className="text-green-400">{graphData.stats.noticias} noticias</span>}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
