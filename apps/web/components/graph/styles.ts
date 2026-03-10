const ENTITY_COLORS: Record<string, string> = {
  empresa: '#ef4444',
  pessoa: '#f97316',
  politico: '#3b82f6',
  mandato: '#a855f7',
  emenda: '#06b6d4',
  noticia: '#22c55e',
};

const EDGE_STYLES: Record<string, string> = {
  societaria: 'solid',
  fundador: 'solid',
  diretor: 'solid',
  fornecedor: 'dashed',
  empregado: 'dashed',
  emenda_beneficiario: 'dashed',
  mencionado_em: 'dotted',
  noticia_menciona: 'dotted',
};

const ENTITY_LABELS: Record<string, string> = {
  empresa: 'Empresa',
  pessoa: 'Pessoa',
  politico: 'Politico',
  mandato: 'Mandato',
  emenda: 'Emenda',
  noticia: 'Noticia',
};

export { ENTITY_COLORS, EDGE_STYLES, ENTITY_LABELS };
