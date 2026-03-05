/**
 * VAR Inference Service
 * Estimates revenue and predicts tax regime changes
 */
import {
  LIMITES_REGIME as IMPORTED_LIMITES,
  FATURAMENTO_POR_FUNCIONARIO,
  PESOS_VAR,
  CAPITAL_SOCIAL_THRESHOLDS,
  GROWTH_RATE_PER_YEAR,
  GROWTH_MIN_YEARS,
  VAR_SCORE_THRESHOLDS,
  MONTHS_TO_CHANGE,
  CNAE_SECTOR_MAP,
  REGIME_PROGRESSION,
  REGIME_TRIBUTARIO
} from '../constants.js';

// Extend LIMITES_REGIME with Infinity for LUCRO_REAL and sub-types
const LIMITES_REGIME = {
  ...IMPORTED_LIMITES,
  SIMPLES_ME: IMPORTED_LIMITES.SIMPLES_ME || 360000,
  SIMPLES_EPP: IMPORTED_LIMITES.SIMPLES_EPP || 4800000,
  LUCRO_REAL: Infinity
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
  if (capital_social > CAPITAL_SOCIAL_THRESHOLDS.HIGH.value) {
    estimativaBase *= CAPITAL_SOCIAL_THRESHOLDS.HIGH.multiplier;
  } else if (capital_social > CAPITAL_SOCIAL_THRESHOLDS.MODERATE.value) {
    estimativaBase *= CAPITAL_SOCIAL_THRESHOLDS.MODERATE.multiplier;
  }

  // Ajuste por anos operando (empresas mais velhas tendem a ter mais receita)
  if (anos_operando > GROWTH_MIN_YEARS) {
    estimativaBase *= 1 + (anos_operando * GROWTH_RATE_PER_YEAR);
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
  if (proximidadeLimite > VAR_SCORE_THRESHOLDS.PROXIMITY_HIGH.threshold) {
    score += VAR_SCORE_THRESHOLDS.PROXIMITY_HIGH.score;
    confianca = 'alta';
  } else if (proximidadeLimite > VAR_SCORE_THRESHOLDS.PROXIMITY_MEDIUM.threshold) {
    score += VAR_SCORE_THRESHOLDS.PROXIMITY_MEDIUM.score;
    confianca = 'media';
  } else if (proximidadeLimite > VAR_SCORE_THRESHOLDS.PROXIMITY_LOW.threshold) {
    score += VAR_SCORE_THRESHOLDS.PROXIMITY_LOW.score;
  }

  // Fator 2: MEI com funcionário (limite é 1)
  if (mei_optante && qtd_funcionarios > 1) {
    score += VAR_SCORE_THRESHOLDS.MEI_EXCEEDED_EMPLOYEES;
    confianca = 'alta';
  }

  // Fator 3: Histórico de mudanças (empresas que já mudaram tendem a mudar de novo)
  if (qtd_mudancas_regime >= VAR_SCORE_THRESHOLDS.REGIME_CHANGES_MANY.count) {
    score += VAR_SCORE_THRESHOLDS.REGIME_CHANGES_MANY.score;
  } else if (qtd_mudancas_regime >= VAR_SCORE_THRESHOLDS.REGIME_CHANGES_ONE.count) {
    score += VAR_SCORE_THRESHOLDS.REGIME_CHANGES_ONE.score;
  }

  // Fator 4: Anos no regime atual (quanto mais tempo, maior chance)
  if (anos_operando > VAR_SCORE_THRESHOLDS.MEI_LONG_TENURE.years && regime_atual === REGIME_TRIBUTARIO.MEI) {
    score += VAR_SCORE_THRESHOLDS.MEI_LONG_TENURE.score;
    confianca = 'media';
  }

  // Determinar próximo regime provável
  const proximoRegime = determinarProximoRegime(regime_atual);

  // Tempo estimado para mudança (em meses)
  let mesesParaMudanca = null;
  if (score > MONTHS_TO_CHANGE.HIGH.minScore) {
    mesesParaMudanca = MONTHS_TO_CHANGE.HIGH.months;
  } else if (score > MONTHS_TO_CHANGE.MEDIUM.minScore) {
    mesesParaMudanca = MONTHS_TO_CHANGE.MEDIUM.months;
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
  return CNAE_SECTOR_MAP[codigo] || 'default';
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
  return REGIME_PROGRESSION[regimeAtual] || REGIME_TRIBUTARIO.SIMPLES_NACIONAL;
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