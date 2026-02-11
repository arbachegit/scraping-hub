/**
 * Constants for scraping-hub
 * Avoid magic strings - use these constants
 */

// LinkedIn status
export const LINKEDIN_STATUS = {
  NAO_POSSUI: 'NAO_POSSUI',
  PENDENTE: 'PENDENTE'
};

// Tax regimes (Brazilian)
export const REGIME_TRIBUTARIO = {
  MEI: 'MEI',
  SIMPLES_NACIONAL: 'SIMPLES_NACIONAL',
  LUCRO_PRESUMIDO: 'LUCRO_PRESUMIDO',
  LUCRO_REAL: 'LUCRO_REAL',
  DESCONHECIDO: 'DESCONHECIDO'
};

// Revenue limits by regime (2024)
export const LIMITES_REGIME = {
  MEI: 81000,
  SIMPLES_ME: 360000,
  SIMPLES_EPP: 4800000,
  LUCRO_PRESUMIDO: 78000000
};

// Data sources for compliance registration
export const DATA_SOURCES = {
  SERPER: {
    nome: 'Serper - Google Search API',
    categoria: 'busca',
    fonte_primaria: 'Google',
    url: 'https://google.serper.dev',
    documentacao_url: 'https://serper.dev/docs',
    formato: 'JSON',
    api_key_necessaria: true,
    confiabilidade: 'alta',
    observacoes: 'Busca Google para encontrar CNPJs'
  },
  PERPLEXITY: {
    nome: 'Perplexity AI',
    categoria: 'ia',
    fonte_primaria: 'Perplexity',
    url: 'https://api.perplexity.ai',
    documentacao_url: 'https://docs.perplexity.ai',
    formato: 'JSON',
    api_key_necessaria: true,
    confiabilidade: 'media',
    observacoes: 'Fallback quando Serper não encontra empresa'
  },
  BRASILAPI: {
    nome: 'BrasilAPI - Receita Federal',
    categoria: 'governamental',
    fonte_primaria: 'Receita Federal do Brasil',
    url: 'https://brasilapi.com.br/api/cnpj/v1',
    documentacao_url: 'https://brasilapi.com.br/docs',
    formato: 'JSON',
    api_key_necessaria: false,
    confiabilidade: 'alta',
    cobertura_temporal: '1990-presente',
    observacoes: 'Dados oficiais de CNPJ da Receita Federal'
  },
  APOLLO: {
    nome: 'Apollo.io',
    categoria: 'enrichment',
    fonte_primaria: 'Apollo',
    url: 'https://api.apollo.io',
    documentacao_url: 'https://apolloio.github.io/apollo-api-docs',
    formato: 'JSON',
    api_key_necessaria: true,
    confiabilidade: 'alta',
    observacoes: 'Enriquecimento de dados de empresas e pessoas (LinkedIn)'
  },
  CNPJA: {
    nome: 'CNPJá - Regime Tributário',
    categoria: 'fiscal',
    fonte_primaria: 'CNPJá',
    url: 'https://api.cnpja.com',
    documentacao_url: 'https://cnpja.com/docs',
    formato: 'JSON',
    api_key_necessaria: true,
    confiabilidade: 'alta',
    cobertura_temporal: '2015-presente',
    observacoes: 'Histórico de Simples Nacional e MEI'
  }
};

// Search sources order (fallback chain)
export const SEARCH_FALLBACK_ORDER = ['serper', 'perplexity', 'serper_exact'];
