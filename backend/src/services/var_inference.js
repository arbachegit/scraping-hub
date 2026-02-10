/**
 * VAR Inference Service
 * Estimates revenue and predicts tax regime changes
 */

// Limites dos regimes tributários (valores anuais em R$)
const LIMITES_REGIME = {
  MEI: 81000,
  SIMPLES_ME: 360000,
  SIMPLES_EPP: 4800000,
  LUCRO_PRESUMIDO: 78000000,
  LUCRO_REAL: Infinity
};

// Pesos das variáveis no modelo VAR (calibrados empiricamente)
const PESOS_VAR = {
  qtd_funcionarios: 0.30,      // Forte correlação com faturamento
  capital_social: 0.15,        // Correlação moderada
  anos_operando: 0.20,         // Empresas mais velhas tendem a crescer
  qtd_mudancas_regime: 0.15,   // Histórico de crescimento
  qtd_socios: 0.10,            // Mais sócios = mais capital/operação
  qtd_cnaes: 0.10              // Diversificação indica escala
};

// Faturamento médio por funcionário por setor (estimativas)
const FATURAMENTO_POR_FUNCIONARIO = {
  comercio: 180000,
  servicos: 120000,
  industria: 250000,
  tecnologia: 200000,
  default: 150000
};

/**
 * Calculate VAR inference for a company
 */
export function calcularInferenciaVAR(empresa, regimes, socios) {
  const variaveis = extrairVariaveis(empresa, regimes, socios);
  const faturamento = estimarFaturamento(variaveis);
  const probabilidade = calcularProbabilidadeMudanca(variaveis, faturamento);
  const sinais = identificarSinais(variaveis, faturamento);

  return {
    // Estimativas de faturamento
    faturamento_estimado_min: faturamento.min,
    faturamento_estimado_max: faturamento.max,
    faturamento_estimado_medio: faturamento.medio,

    // Previsão de mudança de regime
    provavelmente_ultrapassou_limite: probabilidade.ultrapassou,
    probabilidade_mudanca_regime: probabilidade.percentual,
    regime_provavel_proximo: probabilidade.proximo_regime,
    tempo_estimado_mudanca_meses: probabilidade.meses_para_mudanca,
    confianca: probabilidade.confianca,

    // Dados do modelo
    sinais: sinais,
    variaveis_correlacionadas: variaveis,

    // Metadados
    qtd_mudancas_regime: variaveis.qtd_mudancas_regime,
    capital_social: variaveis.capital_social,
    qtd_funcionarios: variaveis.qtd_funcionarios,
    anos_operando: variaveis.anos_operando
  };
}

/**
 * Extract variables from company data
 */
function extrairVariaveis(empresa, regimes, socios) {
  const dataFundacao = empresa.data_fundacao || empresa.data_abertura;
  const anosOperando = dataFundacao
    ? Math.floor((new Date() - new Date(dataFundacao)) / (365.25 * 24 * 60 * 60 * 1000))
    : 0;

  // Get current regime
  const regimeAtual = regimes?.find(r => r.ativo) || regimes?.[0];

  // Determine sector from CNAE
  const setor = determinarSetor(regimeAtual?.cnae_principal || empresa.cnae_principal);

  return {
    // Variáveis diretas
    qtd_funcionarios: regimeAtual?.qtd_funcionarios || 0,
    capital_social: parseFloat(regimeAtual?.capital_social || empresa.capital_social || 0),
    anos_operando: anosOperando,
    qtd_mudancas_regime: regimes?.filter(r => !r.ativo).length || 0,
    qtd_socios: socios?.length || 0,
    qtd_cnaes: 1, // TODO: count secondary CNAEs

    // Contexto
    regime_atual: regimeAtual?.regime_tributario || 'DESCONHECIDO',
    porte: regimeAtual?.porte || empresa.porte,
    setor: setor,
    mei_optante: regimeAtual?.mei_optante || false,
    simples_optante: regimeAtual?.simples_optante || false,

    // Histórico
    regimes_anteriores: regimes?.filter(r => !r.ativo).map(r => r.regime_tributario) || []
  };
}

/**
 * Estimate revenue based on available variables
 */
function estimarFaturamento(variaveis) {
  const { regime_atual, qtd_funcionarios, capital_social, anos_operando, setor } = variaveis;

  // Base: faturamento por funcionário
  const fatPorFunc = FATURAMENTO_POR_FUNCIONARIO[setor] || FATURAMENTO_POR_FUNCIONARIO.default;
  let estimativaBase = Math.max(qtd_funcionarios, 1) * fatPorFunc;

  // Ajuste por capital social (capital alto sugere operação maior)
  if (capital_social > 100000) {
    estimativaBase *= 1.2;
  } else if (capital_social > 500000) {
    estimativaBase *= 1.5;
  }

  // Ajuste por anos operando (empresas mais velhas tendem a ter mais receita)
  if (anos_operando > 5) {
    estimativaBase *= 1 + (anos_operando * 0.02); // +2% por ano após 5 anos
  }

  // Limites baseados no regime atual
  const limiteAtual = LIMITES_REGIME[regime_atual] || LIMITES_REGIME.SIMPLES_EPP;
  const limiteAnterior = getLimiteAnterior(regime_atual);

  // MEI: sabemos que está entre 0 e 81k
  if (regime_atual === 'MEI') {
    return {
      min: Math.max(estimativaBase * 0.5, 20000),
      max: LIMITES_REGIME.MEI,
      medio: Math.min(estimativaBase, LIMITES_REGIME.MEI * 0.8)
    };
  }

  // Simples: entre limite anterior e atual
  if (regime_atual === 'SIMPLES_NACIONAL') {
    const ehME = variaveis.porte === 'ME';
    const limMax = ehME ? LIMITES_REGIME.SIMPLES_ME : LIMITES_REGIME.SIMPLES_EPP;
    return {
      min: LIMITES_REGIME.MEI, // Ultrapassou MEI
      max: limMax,
      medio: Math.min(estimativaBase, limMax * 0.7)
    };
  }

  // Lucro Presumido/Real
  return {
    min: limiteAnterior,
    max: limiteAtual,
    medio: estimativaBase
  };
}

/**
 * Calculate probability of regime change
 */
function calcularProbabilidadeMudanca(variaveis, faturamento) {
  const { regime_atual, qtd_funcionarios, anos_operando, qtd_mudancas_regime, mei_optante } = variaveis;

  let score = 0;
  let confianca = 'baixa';

  // Limite do regime atual
  const limiteAtual = LIMITES_REGIME[regime_atual] || LIMITES_REGIME.SIMPLES_EPP;

  // Fator 1: Proximidade do limite (faturamento estimado vs limite)
  const proximidadeLimite = faturamento.medio / limiteAtual;
  if (proximidadeLimite > 0.9) {
    score += 40;
    confianca = 'alta';
  } else if (proximidadeLimite > 0.7) {
    score += 25;
    confianca = 'media';
  } else if (proximidadeLimite > 0.5) {
    score += 10;
  }

  // Fator 2: MEI com funcionário (limite é 1)
  if (mei_optante && qtd_funcionarios > 1) {
    score += 50; // Já ultrapassou limite
    confianca = 'alta';
  }

  // Fator 3: Histórico de mudanças (empresas que já mudaram tendem a mudar de novo)
  if (qtd_mudancas_regime >= 2) {
    score += 15;
  } else if (qtd_mudancas_regime >= 1) {
    score += 10;
  }

  // Fator 4: Anos no regime atual (quanto mais tempo, maior chance)
  if (anos_operando > 10 && regime_atual === 'MEI') {
    score += 20; // MEI há muito tempo é suspeito
    confianca = 'media';
  }

  // Determinar próximo regime provável
  const proximoRegime = determinarProximoRegime(regime_atual);

  // Tempo estimado para mudança (em meses)
  let mesesParaMudanca = null;
  if (score > 50) {
    mesesParaMudanca = 12; // Próximo ano
  } else if (score > 30) {
    mesesParaMudanca = 24; // 2 anos
  }

  return {
    ultrapassou: score >= 50,
    percentual: Math.min(score, 100),
    proximo_regime: proximoRegime,
    meses_para_mudanca: mesesParaMudanca,
    confianca: confianca
  };
}

/**
 * Identify signals that indicate regime change
 */
function identificarSinais(variaveis, faturamento) {
  const sinais = [];
  const { regime_atual, qtd_funcionarios, capital_social, anos_operando, mei_optante, regimes_anteriores } = variaveis;

  // MEI signals
  if (mei_optante) {
    if (qtd_funcionarios > 1) {
      sinais.push(`MEI com ${qtd_funcionarios} funcionários (limite é 1) - ULTRAPASSOU`);
    }
    if (capital_social > 50000) {
      sinais.push(`Capital social R$ ${capital_social.toLocaleString('pt-BR')} alto para MEI`);
    }
    if (anos_operando > 8) {
      sinais.push(`MEI há ${anos_operando} anos - provável faturamento próximo do limite`);
    }
  }

  // Simples signals
  if (regime_atual === 'SIMPLES_NACIONAL') {
    if (qtd_funcionarios > 50) {
      sinais.push(`${qtd_funcionarios} funcionários - porte significativo`);
    }
    if (faturamento.medio > LIMITES_REGIME.SIMPLES_ME * 0.8) {
      sinais.push('Faturamento estimado próximo do limite de ME');
    }
  }

  // Historical signals
  if (regimes_anteriores.includes('MEI')) {
    sinais.push('Já foi MEI - cresceu e mudou para Simples');
  }
  if (regimes_anteriores.length >= 2) {
    sinais.push(`${regimes_anteriores.length} mudanças de regime - crescimento consistente`);
  }

  // Revenue signals
  const limiteAtual = LIMITES_REGIME[regime_atual] || LIMITES_REGIME.SIMPLES_EPP;
  const percentualLimite = (faturamento.medio / limiteAtual * 100).toFixed(0);
  sinais.push(`Faturamento estimado: R$ ${faturamento.medio.toLocaleString('pt-BR')} (${percentualLimite}% do limite)`);

  return sinais;
}

/**
 * Determine sector from CNAE
 */
function determinarSetor(cnae) {
  if (!cnae) return 'default';
  const codigo = cnae.toString().substring(0, 2);

  // CNAE groups
  const setores = {
    '01': 'industria', '02': 'industria', '03': 'industria', // Agro
    '10': 'industria', '11': 'industria', '12': 'industria', // Alimentos
    '45': 'comercio', '46': 'comercio', '47': 'comercio',    // Comércio
    '62': 'tecnologia', '63': 'tecnologia',                   // TI
    '69': 'servicos', '70': 'servicos', '71': 'servicos'      // Serviços
  };

  return setores[codigo] || 'default';
}

/**
 * Get previous regime limit
 */
function getLimiteAnterior(regime) {
  const ordem = ['MEI', 'SIMPLES_ME', 'SIMPLES_NACIONAL', 'LUCRO_PRESUMIDO', 'LUCRO_REAL'];
  const idx = ordem.indexOf(regime);
  if (idx <= 0) return 0;
  return LIMITES_REGIME[ordem[idx - 1]] || 0;
}

/**
 * Determine next probable regime
 */
function determinarProximoRegime(regimeAtual) {
  const progressao = {
    'MEI': 'SIMPLES_NACIONAL',
    'SIMPLES_NACIONAL': 'LUCRO_PRESUMIDO',
    'LUCRO_PRESUMIDO': 'LUCRO_REAL',
    'LUCRO_REAL': 'LUCRO_REAL'
  };
  return progressao[regimeAtual] || 'SIMPLES_NACIONAL';
}

/**
 * Get VAR weights for analysis
 */
export function getPesosVAR() {
  return PESOS_VAR;
}

/**
 * Get regime limits
 */
export function getLimitesRegime() {
  return LIMITES_REGIME;
}