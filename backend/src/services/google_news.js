/**
 * Google News Service (via Serper)
 * Notícias e menções na mídia para análise reputacional
 */

import logger from '../utils/logger.js';

const SERPER_API_KEY = process.env.SERPER_API_KEY;
const SERPER_BASE_URL = 'https://google.serper.dev';

/**
 * Search Google News via Serper
 * @param {string} query - Search query
 * @param {number} num - Number of results
 * @returns {Promise<Object>} Search results
 */
async function newsSearch(query, num = 10) {
  const response = await fetch(`${SERPER_BASE_URL}/news`, {
    method: 'POST',
    headers: {
      'X-API-KEY': SERPER_API_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      q: query,
      num: Math.min(num, 100),
      gl: 'br',
      hl: 'pt-br'
    })
  });

  if (!response.ok) {
    throw new Error(`Serper News API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Search for news mentioning a person
 * @param {string} personName - Person name
 * @param {string} company - Company name (optional, for context)
 * @returns {Promise<Array>} List of news articles
 */
export async function searchPersonNews(personName, company = null) {
  let query = `"${personName}"`;
  if (company) {
    query += ` "${company}"`;
  }

  try {
    const results = await newsSearch(query, 30);
    const articles = [];

    for (const item of results.news || []) {
      const sentiment = analyzeSentiment(item.title, item.snippet);

      articles.push({
        title: item.title,
        link: item.link,
        snippet: item.snippet,
        source: item.source,
        date: item.date,
        image_url: item.imageUrl,
        sentiment: sentiment,
        category: categorizeNews(item.title, item.snippet)
      });
    }

    return articles;
  } catch (error) {
    logger.error('Google News search error', { error: error.message, person: personName });
    return [];
  }
}

/**
 * Analyze sentiment of news text (simple rule-based)
 * @param {string} title - Article title
 * @param {string} snippet - Article snippet
 * @returns {string} Sentiment: positive, negative, or neutral
 */
function analyzeSentiment(title, snippet) {
  const text = `${title || ''} ${snippet || ''}`.toLowerCase();

  const negativeWords = [
    'fraude', 'escândalo', 'prisão', 'preso', 'denúncia', 'corrupção',
    'acusado', 'investigado', 'condenado', 'processo', 'crime', 'irregular',
    'demitido', 'renunciou', 'afastado', 'multa', 'cassado', 'improbidade',
    'lavagem', 'operação', 'delação', 'prejuízo', 'falência', 'calote'
  ];

  const positiveWords = [
    'premiado', 'sucesso', 'inovação', 'crescimento', 'expansão', 'recorde',
    'liderança', 'reconhecimento', 'homenagem', 'conquista', 'investimento',
    'parceria', 'lançamento', 'destaque', 'eleito', 'nomeado', 'promovido'
  ];

  let negativeCount = 0;
  let positiveCount = 0;

  for (const word of negativeWords) {
    if (text.includes(word)) negativeCount++;
  }

  for (const word of positiveWords) {
    if (text.includes(word)) positiveCount++;
  }

  if (negativeCount > positiveCount && negativeCount > 0) {
    return 'negative';
  } else if (positiveCount > negativeCount && positiveCount > 0) {
    return 'positive';
  }

  return 'neutral';
}

/**
 * Categorize news article
 * @param {string} title - Article title
 * @param {string} snippet - Article snippet
 * @returns {string} Category
 */
function categorizeNews(title, snippet) {
  const text = `${title || ''} ${snippet || ''}`.toLowerCase();

  if (text.match(/prisão|preso|polícia|operação|investigação|crime|fraude/)) {
    return 'policial';
  }
  if (text.match(/tribunal|justiça|processo|condenação|absolvição|recurso/)) {
    return 'juridico';
  }
  if (text.match(/eleição|partido|candidato|político|câmara|senado|governo/)) {
    return 'politico';
  }
  if (text.match(/empresa|mercado|ações|investimento|startup|negócio|expansão/)) {
    return 'negocios';
  }
  if (text.match(/universidade|pesquisa|estudo|cientista|professor|academia/)) {
    return 'academico';
  }
  if (text.match(/prêmio|homenagem|destaque|reconhecimento|conquista/)) {
    return 'premiacao';
  }

  return 'geral';
}

/**
 * Calculate reputational metrics from news
 * @param {Array} articles - List of news articles
 * @returns {Object} Reputational metrics
 */
export function calculateReputationalMetrics(articles) {
  if (!articles.length) {
    return {
      total_mentions: 0,
      sentiment_score: 0, // -100 to +100
      positive_count: 0,
      negative_count: 0,
      neutral_count: 0,
      risk_level: 'unknown',
      top_sources: [],
      categories: {}
    };
  }

  let positive = 0;
  let negative = 0;
  let neutral = 0;
  const sources = {};
  const categories = {};

  for (const article of articles) {
    // Count sentiment
    if (article.sentiment === 'positive') positive++;
    else if (article.sentiment === 'negative') negative++;
    else neutral++;

    // Count sources
    const source = article.source || 'unknown';
    sources[source] = (sources[source] || 0) + 1;

    // Count categories
    const category = article.category || 'geral';
    categories[category] = (categories[category] || 0) + 1;
  }

  // Calculate sentiment score (-100 to +100)
  const total = positive + negative + neutral;
  const sentimentScore = Math.round(((positive - negative) / total) * 100);

  // Determine risk level
  let riskLevel = 'baixo';
  if (negative >= 3 || (negative > positive && negative >= 2)) {
    riskLevel = 'alto';
  } else if (negative >= 1) {
    riskLevel = 'medio';
  }

  // Top sources
  const topSources = Object.entries(sources)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, count]) => ({ name, count }));

  return {
    total_mentions: total,
    sentiment_score: sentimentScore,
    positive_count: positive,
    negative_count: negative,
    neutral_count: neutral,
    risk_level: riskLevel,
    top_sources: topSources,
    categories: categories
  };
}

/**
 * Get recent negative news (for due diligence)
 * @param {Array} articles - List of news articles
 * @returns {Array} Negative articles
 */
export function getNegativeNews(articles) {
  return articles.filter(a => a.sentiment === 'negative');
}

/**
 * Search and analyze person's media presence
 * @param {string} name - Person name
 * @param {string} company - Company name (optional)
 * @returns {Promise<Object>} Reputational enrichment result
 */
export async function enrichPersonReputation(name, company = null) {
  const result = {
    found: false,
    articles: [],
    metrics: null,
    negative_alerts: [],
    risk_summary: null
  };

  const articles = await searchPersonNews(name, company);

  if (!articles.length) {
    return result;
  }

  result.found = true;
  result.articles = articles;
  result.metrics = calculateReputationalMetrics(articles);
  result.negative_alerts = getNegativeNews(articles).slice(0, 5);

  // Risk summary
  const metrics = result.metrics;
  result.risk_summary = {
    nivel: metrics.risk_level,
    mencoes_negativas: metrics.negative_count,
    principais_riscos: result.negative_alerts.map(a => ({
      titulo: a.title,
      fonte: a.source,
      data: a.date,
      categoria: a.category
    }))
  };

  return result;
}
