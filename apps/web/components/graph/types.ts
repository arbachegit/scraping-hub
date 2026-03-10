export type EntityType =
  | 'empresa'
  | 'pessoa'
  | 'politico'
  | 'mandato'
  | 'emenda'
  | 'noticia';

export type RelationshipType =
  | 'societaria'
  | 'fundador'
  | 'diretor'
  | 'fornecedor'
  | 'empregado'
  | 'emenda_beneficiario'
  | 'mencionado_em'
  | 'noticia_menciona';

export interface GraphNode {
  id: string;
  type: EntityType;
  label: string;
  data?: Record<string, unknown>;
  // D3 simulation mutable fields
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
  index?: number;
}

export interface GraphEdge {
  id: string;
  source: string | GraphNode;
  target: string | GraphNode;
  tipo_relacao: RelationshipType;
  strength: number;
  confidence?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

