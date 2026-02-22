'use client';

import { useState, useEffect, useCallback } from 'react';
import { X, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { listCnaes, type Cnae } from '@/lib/api';

interface CnaeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (codigo: string, descricao: string) => void;
}

export function CnaeModal({ isOpen, onClose, onSelect }: CnaeModalProps) {
  const [cnaes, setCnaes] = useState<Cnae[]>([]);
  const [filteredCnaes, setFilteredCnaes] = useState<Cnae[]>([]);
  const [search, setSearch] = useState('');
  const [secao, setSecao] = useState('');
  const [divisao, setDivisao] = useState('');
  const [grupo, setGrupo] = useState('');
  const [classe, setClasse] = useState('');
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const loadCnaes = useCallback(async () => {
    if (loaded) return;
    setLoading(true);
    try {
      const data = await listCnaes(2000);
      setCnaes(data.data || []);
      setFilteredCnaes(data.data || []);
      setLoaded(true);
    } catch {
      // Error handled silently
    } finally {
      setLoading(false);
    }
  }, [loaded]);

  useEffect(() => {
    if (isOpen && !loaded) {
      loadCnaes();
    }
  }, [isOpen, loaded, loadCnaes]);

  useEffect(() => {
    let filtered = cnaes;

    if (secao) {
      filtered = filtered.filter((c) => c.descricao_secao === secao);
    }
    if (divisao) {
      filtered = filtered.filter((c) => c.descricao_divisao === divisao);
    }
    if (grupo) {
      filtered = filtered.filter((c) => c.descricao_grupo === grupo);
    }
    if (classe) {
      filtered = filtered.filter((c) => c.descricao_classe === classe);
    }

    if (search) {
      const searchLower = search.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          (c.codigo || '').toLowerCase().includes(searchLower) ||
          (c.subclasse || '').toLowerCase().includes(searchLower) ||
          (c.descricao || '').toLowerCase().includes(searchLower)
      );
    }

    setFilteredCnaes(filtered);
  }, [cnaes, search, secao, divisao, grupo, classe]);

  const secoes = [...new Set(cnaes.map((c) => c.descricao_secao).filter(Boolean))].sort();
  const divisoes = secao
    ? [
        ...new Set(
          cnaes
            .filter((c) => c.descricao_secao === secao)
            .map((c) => c.descricao_divisao)
            .filter(Boolean)
        ),
      ].sort()
    : [];
  const grupos = divisao
    ? [
        ...new Set(
          cnaes
            .filter((c) => c.descricao_divisao === divisao)
            .map((c) => c.descricao_grupo)
            .filter(Boolean)
        ),
      ].sort()
    : [];
  const classes = grupo
    ? [
        ...new Set(
          cnaes
            .filter((c) => c.descricao_grupo === grupo)
            .map((c) => c.descricao_classe)
            .filter(Boolean)
        ),
      ].sort()
    : [];

  function handleSelect(cnae: Cnae) {
    onSelect(cnae.codigo || cnae.subclasse || '', cnae.descricao || '');
    onClose();
  }

  function handleSecaoChange(value: string) {
    setSecao(value);
    setDivisao('');
    setGrupo('');
    setClasse('');
  }

  function handleDivisaoChange(value: string) {
    setDivisao(value);
    setGrupo('');
    setClasse('');
  }

  function handleGrupoChange(value: string) {
    setGrupo(value);
    setClasse('');
  }

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/85"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="w-[95%] max-w-5xl max-h-[85vh] overflow-hidden rounded-2xl border border-purple-500/20 bg-gradient-to-b from-[#0f1629] to-[#0a0e1a] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-purple-500/15">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <span className="w-1 h-5 bg-gradient-to-b from-purple-400 to-purple-600 rounded" />
            Lista de CNAEs
          </h3>
          <button
            onClick={onClose}
            className="flex items-center justify-center w-9 h-9 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-400 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Search */}
        <div className="px-6 py-4 border-b border-white/5">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por codigo ou descricao..."
            className="w-full"
          />
        </div>

        {/* Filters */}
        <div className="flex gap-2 px-6 py-3 flex-wrap">
          <select
            value={secao}
            onChange={(e) => handleSecaoChange(e.target.value)}
            className="flex-1 min-w-[150px] bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500/50"
          >
            <option value="">Todas as Secoes</option>
            {secoes.map((s) => (
              <option key={s} value={s}>
                {(s || '').substring(0, 50)}
                {(s || '').length > 50 ? '...' : ''}
              </option>
            ))}
          </select>
          <select
            value={divisao}
            onChange={(e) => handleDivisaoChange(e.target.value)}
            className="flex-1 min-w-[150px] bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500/50"
            disabled={!secao}
          >
            <option value="">Todas as Divisoes</option>
            {divisoes.map((d) => (
              <option key={d} value={d}>
                {(d || '').substring(0, 40)}
                {(d || '').length > 40 ? '...' : ''}
              </option>
            ))}
          </select>
          <select
            value={grupo}
            onChange={(e) => handleGrupoChange(e.target.value)}
            className="flex-1 min-w-[150px] bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500/50"
            disabled={!divisao}
          >
            <option value="">Todos os Grupos</option>
            {grupos.map((g) => (
              <option key={g} value={g}>
                {(g || '').substring(0, 40)}
                {(g || '').length > 40 ? '...' : ''}
              </option>
            ))}
          </select>
          <select
            value={classe}
            onChange={(e) => setClasse(e.target.value)}
            className="flex-1 min-w-[150px] bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500/50"
            disabled={!grupo}
          >
            <option value="">Todas as Classes</option>
            {classes.map((cl) => (
              <option key={cl} value={cl}>
                {(cl || '').substring(0, 40)}
                {(cl || '').length > 40 ? '...' : ''}
              </option>
            ))}
          </select>
        </div>

        {/* Table */}
        <ScrollArea className="flex-1 px-6 pb-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <Loader2 className="h-10 w-10 animate-spin text-purple-400 mb-4" />
              <span>Carregando CNAEs...</span>
            </div>
          ) : filteredCnaes.length === 0 ? (
            <div className="text-center py-12 text-slate-500">Nenhum CNAE encontrado</div>
          ) : (
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-purple-500/10">
                  <th className="text-left p-3 text-purple-400 font-semibold text-xs uppercase sticky top-0 bg-[#0f1629] z-10">
                    Codigo
                  </th>
                  <th className="text-left p-3 text-purple-400 font-semibold text-xs uppercase sticky top-0 bg-[#0f1629] z-10">
                    Descricao
                  </th>
                  <th className="text-left p-3 text-purple-400 font-semibold text-xs uppercase sticky top-0 bg-[#0f1629] z-10">
                    Secao
                  </th>
                  <th className="text-left p-3 text-purple-400 font-semibold text-xs uppercase sticky top-0 bg-[#0f1629] z-10">
                    Divisao
                  </th>
                  <th className="text-left p-3 text-purple-400 font-semibold text-xs uppercase sticky top-0 bg-[#0f1629] z-10">
                    Grupo
                  </th>
                  <th className="text-left p-3 text-purple-400 font-semibold text-xs uppercase sticky top-0 bg-[#0f1629] z-10">
                    Classe
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredCnaes.map((cnae) => (
                  <tr
                    key={cnae.codigo || cnae.subclasse}
                    onClick={() => handleSelect(cnae)}
                    className="cursor-pointer hover:bg-purple-500/5 border-b border-white/5"
                  >
                    <td className="p-2.5 text-purple-400 font-mono font-semibold whitespace-nowrap">
                      {cnae.codigo || cnae.subclasse || '-'}
                    </td>
                    <td className="p-2.5 text-white font-medium">{cnae.descricao || '-'}</td>
                    <td className="p-2.5 text-cyan-400 text-xs">{cnae.descricao_secao || '-'}</td>
                    <td className="p-2.5 text-slate-400 text-xs">
                      {cnae.descricao_divisao || '-'}
                    </td>
                    <td className="p-2.5 text-slate-400 text-xs">{cnae.descricao_grupo || '-'}</td>
                    <td className="p-2.5 text-slate-400 text-xs">{cnae.descricao_classe || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ScrollArea>
      </div>
    </div>
  );
}
