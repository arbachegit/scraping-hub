'use client';

import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { X, Search, ArrowLeft, Loader2, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  listPeople,
  searchPeople,
  getPersonDetails,
  type Person,
  type PersonDetailsResponse,
} from '@/lib/api';

interface PeopleModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenListingModal: () => void;
}

type ViewState = 'search' | 'details';

export function PeopleModal({ isOpen, onClose, onOpenListingModal }: PeopleModalProps) {
  const [view, setView] = useState<ViewState>('search');
  const [nome, setNome] = useState('');
  const [selectedPersonId, setSelectedPersonId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  const listQuery = useQuery({
    queryKey: ['people', 'list'],
    queryFn: () => listPeople({ limit: 50 }),
    enabled: isOpen,
  });

  const searchMutation = useMutation({
    mutationFn: searchPeople,
  });

  const detailsQuery = useQuery({
    queryKey: ['person', selectedPersonId],
    queryFn: () => getPersonDetails(selectedPersonId!),
    enabled: !!selectedPersonId && view === 'details',
  });

  const people = searchMutation.data?.people || listQuery.data?.people || [];
  const count = searchMutation.data?.count || listQuery.data?.count || 0;
  const isLoading = searchMutation.isPending || listQuery.isLoading;

  function handleSearch() {
    if (!nome.trim()) {
      searchMutation.reset();
      return;
    }
    searchMutation.mutate(nome);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearch();
    }
  }

  function handleSelectPerson(personId: string) {
    setSelectedPersonId(personId);
    setView('details');
  }

  function handleBack() {
    setView('search');
    setSelectedPersonId(null);
  }

  function handleClose() {
    setView('search');
    setNome('');
    setSelectedPersonId(null);
    searchMutation.reset();
    onClose();
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
      <div className="w-full max-w-2xl max-h-[85vh] overflow-hidden rounded-2xl border border-cyan-500/15 bg-gradient-to-b from-[#0f1629] to-[#0a0e1a] shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/5">
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <span className="w-1 h-5 bg-gradient-to-b from-orange-400 to-orange-600 rounded" />
            Buscar Pessoas
          </h2>
          <button
            onClick={handleClose}
            className="flex items-center justify-center w-9 h-9 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-400 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <ScrollArea className="p-6 max-h-[calc(85vh-80px)]">
          {view === 'search' ? (
            <>
              {/* Search Form */}
              <div className="flex gap-3 mb-4">
                <Input
                  ref={inputRef}
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Nome da pessoa *"
                  className="flex-[2]"
                />
                <Button
                  onClick={handleSearch}
                  disabled={isLoading}
                  className="h-10 px-6 bg-cyan-500/15 border-2 border-cyan-500 text-cyan-400 hover:bg-cyan-500 hover:text-white"
                >
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Search className="h-4 w-4 mr-2" />
                  )}
                  Buscar
                </Button>
                <Button onClick={onOpenListingModal} variant="outline" className="h-10 px-6">
                  Listar
                </Button>
              </div>

              {/* Loading */}
              {isLoading && (
                <div className="flex flex-col items-center justify-center py-10 text-slate-400">
                  <Loader2 className="h-10 w-10 animate-spin text-cyan-400 mb-4" />
                  <span>Carregando pessoas...</span>
                </div>
              )}

              {/* Results */}
              {!isLoading && people.length > 0 && (
                <>
                  <div className="text-slate-400 text-sm mb-4 pb-2 border-b border-white/5">
                    <strong>{count}</strong> pessoa(s) encontrada(s)
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {people.map((p) => (
                      <PersonCard key={p.id} person={p} onClick={() => handleSelectPerson(p.id)} />
                    ))}
                  </div>
                </>
              )}

              {!isLoading && people.length === 0 && (
                <div className="text-center py-10 text-slate-500">
                  {nome ? `Nenhuma pessoa encontrada com "${nome}".` : 'Nenhuma pessoa encontrada na base.'}
                </div>
              )}
            </>
          ) : (
            <>
              {/* Person Details View */}
              <Button onClick={handleBack} variant="outline" className="mb-4">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Voltar
              </Button>

              {detailsQuery.isLoading && (
                <div className="flex flex-col items-center justify-center py-10 text-slate-400">
                  <Loader2 className="h-10 w-10 animate-spin text-cyan-400 mb-4" />
                  <span>Carregando detalhes...</span>
                </div>
              )}

              {detailsQuery.isError && (
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">
                  Erro ao carregar detalhes
                </div>
              )}

              {detailsQuery.data?.success && (
                <PersonDetailsView data={detailsQuery.data} />
              )}
            </>
          )}
        </ScrollArea>
      </div>
    </div>
  );
}

function PersonCard({ person, onClick }: { person: Person; onClick: () => void }) {
  const nome = person.nome_completo || person.nome || 'Nome nao disponivel';
  const linkedin =
    person.linkedin_url && person.linkedin_url !== 'inexistente' ? person.linkedin_url : null;

  return (
    <div
      onClick={onClick}
      className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] cursor-pointer hover:border-cyan-500/40 hover:bg-cyan-500/5 transition-colors"
    >
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-full bg-orange-500/15 flex items-center justify-center flex-shrink-0">
          <span className="text-orange-400 font-semibold">{nome.charAt(0).toUpperCase()}</span>
        </div>
        <div className="flex-1 min-w-0">
          <strong className="text-slate-200 text-sm block truncate">{nome}</strong>
          {person.faixa_etaria && (
            <span className="text-slate-500 text-xs">{person.faixa_etaria}</span>
          )}
        </div>
      </div>
      {person.pais && (
        <div className="text-slate-500 text-xs">
          <span className="text-slate-600">Pais:</span> {person.pais}
        </div>
      )}
      {linkedin && (
        <a
          href={linkedin}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-cyan-400 text-xs hover:underline inline-flex items-center gap-1 mt-1"
        >
          Ver LinkedIn <ExternalLink className="h-3 w-3" />
        </a>
      )}
    </div>
  );
}

function PersonDetailsView({ data }: { data: PersonDetailsResponse }) {
  const p = data.pessoa;
  const nome = p.nome_completo || p.nome || 'Nome nao disponivel';
  const linkedin = p.linkedin_url && p.linkedin_url !== 'inexistente' ? p.linkedin_url : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="w-16 h-16 rounded-full bg-orange-500/15 flex items-center justify-center flex-shrink-0">
          <span className="text-orange-400 font-semibold text-2xl">
            {nome.charAt(0).toUpperCase()}
          </span>
        </div>
        <div>
          <h3 className="text-xl font-semibold text-white">{nome}</h3>
          {p.faixa_etaria && <span className="text-slate-400 text-sm">{p.faixa_etaria}</span>}
        </div>
      </div>

      {/* Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {p.email && (
          <div className="text-sm">
            <span className="text-slate-500">Email:</span>{' '}
            <span className="text-slate-300">{p.email}</span>
          </div>
        )}
        {p.pais && (
          <div className="text-sm">
            <span className="text-slate-500">Pais:</span>{' '}
            <span className="text-slate-300">{p.pais}</span>
          </div>
        )}
        {linkedin && (
          <div className="text-sm">
            <a
              href={linkedin}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-400 hover:underline inline-flex items-center gap-1"
            >
              Ver LinkedIn <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        )}
      </div>

      {/* Experiences */}
      {data.experiencias && data.experiencias.length > 0 && (
        <div>
          <h4 className="text-slate-400 text-sm font-semibold mb-3">Experiencias</h4>
          <div className="space-y-3">
            {data.experiencias.map((exp, i) => (
              <div key={i} className="p-3 bg-white/[0.02] border border-white/5 rounded-lg">
                <strong className="text-slate-200 text-sm">
                  {exp.titulo || 'Cargo nao informado'}
                </strong>
                {exp.instituicao && <span className="text-slate-400 text-sm"> - {exp.instituicao}</span>}
                {exp.data_inicio && (
                  <div className="text-slate-500 text-xs mt-1">
                    {exp.data_inicio}
                    {exp.data_fim ? ` - ${exp.data_fim}` : ' - Atual'}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Related Companies */}
      {data.empresas && data.empresas.length > 0 && (
        <div>
          <h4 className="text-slate-400 text-sm font-semibold mb-3">Empresas Relacionadas</h4>
          <div className="space-y-3">
            {data.empresas.map((emp, i) => {
              const empresa = emp.dim_empresas;
              if (!empresa) return null;
              return (
                <div key={i} className="p-3 bg-white/[0.02] border border-white/5 rounded-lg">
                  <strong className="text-slate-200 text-sm">
                    {empresa.razao_social || empresa.nome_fantasia || 'Empresa'}
                  </strong>
                  {emp.cargo && <span className="text-slate-400 text-sm"> - {emp.cargo}</span>}
                  {empresa.cidade && (
                    <div className="text-slate-500 text-xs mt-1">
                      {empresa.cidade}/{empresa.estado}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
