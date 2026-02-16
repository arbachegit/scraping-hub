/**
 * Reclame Aqui Service (via Serper)
 * Busca reclamações associadas a pessoas ou empresas
 */

import logger from '../utils/logger.js';

const SERPER_API_KEY = process.env.SERPER_API_KEY;
const SERPER_BASE_URL = 'https://google.serper.dev';

/**
 * Search Reclame Aqui via Serper
 * @param {string} query - Search query
 * @param {number} num - Number of results
 * @returns {Promise<Object>} Search results
 */
async function reclameAquiSearch(query, num = 20) {
  const response = await fetch(`${SERPER_BASE_URL}/search`, {
    method: 'POST',
    headers: {
      'X-API-KEY': SERPER_API_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      q: `${query} site:reclameaqui.com.br`,
      num: Math.min(num, 50),
      gl: 'br',
      hl: 'pt-br'
    })
  });

  if (!response.ok) {
    throw new Error(`Serper API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Search for complaints about a company
 * @param {string} companyName - Company name
 * @returns {Promise<Object>} Company complaints data
 */
export async function searchCompanyComplaints(companyName) {
  try {
    const results = await reclameAquiSearch(`"${companyName}"`, 30);
    const complaints = [];
    let companyPage = null;
    let companyStats = null;

    for (const item of results.organic || []) {
      const url = item.link || '';

      // Check if it's a company profile page
      if (url.match(/reclameaqui\.com\.br\/empresa\/[^/]+\/?$/)) {
        companyPage = {
          url: url,
          title: item.title,
          snippet: item.snippet
        };

        // Try to extract stats from snippet
        companyStats = extractStatsFromSnippet(item.snippet);
        continue;
      }

      // Check if it's a complaint page
      if (url.includes('/reclamacao/') || url.includes('/reclame/')) {
        complaints.push({
          url: url,
          title: item.title,
          snippet: item.snippet,
          date: extractDateFromSnippet(item.snippet),
          resolved: item.snippet?.toLowerCase().includes('resolvido')
        });
      }
    }

    return {
      company_page: companyPage,
      stats: companyStats,
      complaints: complaints,
      total_found: complaints.length
    };
  } catch (error) {
    logger.error('Reclame Aqui company search error', { error: error.message, company: companyName });
    return { company_page: null, stats: null, complaints: [], total_found: 0 };
  }
}

/**
 * Search for complaints mentioning a person
 * @param {string} personName - Person name
 * @param {string} company - Company name (optional)
 * @returns {Promise<Object>} Person-related complaints
 */
export async function searchPersonComplaints(personName, company = null) {
  let query = `"${personName}"`;
  if (company) {
    query += ` "${company}"`;
  }

  try {
    const results = await reclameAquiSearch(query, 20);
    const mentions = [];

    for (const item of results.organic || []) {
      const text = `${item.title || ''} ${item.snippet || ''}`;

      // Only include if person name appears in content
      if (text.toLowerCase().includes(personName.toLowerCase().split(' ')[0])) {
        mentions.push({
          url: item.link,
          title: item.title,
          snippet: item.snippet,
          company_mentioned: extractCompanyFromUrl(item.link),
          date: extractDateFromSnippet(item.snippet)
        });
      }
    }

    return {
      person_name: personName,
      mentions: mentions,
      total_found: mentions.length,
      risk_indicator: mentions.length > 0 ? 'presente_em_reclamacoes' : 'sem_mencoes'
    };
  } catch (error) {
    logger.error('Reclame Aqui person search error', { error: error.message, person: personName });
    return { person_name: personName, mentions: [], total_found: 0, risk_indicator: 'erro_busca' };
  }
}

/**
 * Extract stats from company page snippet
 * @param {string} snippet - Page snippet
 * @returns {Object|null} Extracted stats
 */
function extractStatsFromSnippet(snippet) {
  if (!snippet) return null;

  const stats = {};

  // Try to extract reputation score
  const reputationMatch = snippet.match(/(\d+[,.]?\d*)\s*(?:de\s*10|\/10)/i);
  if (reputationMatch) {
    stats.reputation_score = parseFloat(reputationMatch[1].replace(',', '.'));
  }

  // Try to extract resolution rate
  const resolvedMatch = snippet.match(/(\d+[,.]?\d*)%?\s*(?:resolvid|solucionad)/i);
  if (resolvedMatch) {
    stats.resolution_rate = parseFloat(resolvedMatch[1].replace(',', '.'));
  }

  // Try to extract complaint count
  const countMatch = snippet.match(/(\d+(?:\.\d+)?)\s*(?:reclamações?|queixas?)/i);
  if (countMatch) {
    stats.complaint_count = parseInt(countMatch[1].replace(/\./g, ''));
  }

  // Try to extract "voltaria a fazer negócio"
  const wouldReturnMatch = snippet.match(/(\d+[,.]?\d*)%?\s*(?:voltaria|fariam negócio)/i);
  if (wouldReturnMatch) {
    stats.would_return_rate = parseFloat(wouldReturnMatch[1].replace(',', '.'));
  }

  return Object.keys(stats).length > 0 ? stats : null;
}

/**
 * Extract date from snippet
 * @param {string} snippet - Text snippet
 * @returns {string|null} Date if found
 */
function extractDateFromSnippet(snippet) {
  if (!snippet) return null;

  // Pattern: DD/MM/YYYY or DD de mês de YYYY
  const datePattern = /(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})/;
  const match = snippet.match(datePattern);

  if (match) {
    const day = match[1].padStart(2, '0');
    const month = match[2].padStart(2, '0');
    const year = match[3].length === 2 ? `20${match[3]}` : match[3];
    return `${year}-${month}-${day}`;
  }

  return null;
}

/**
 * Extract company name from Reclame Aqui URL
 * @param {string} url - Reclame Aqui URL
 * @returns {string|null} Company name
 */
function extractCompanyFromUrl(url) {
  if (!url) return null;

  // Pattern: /empresa/company-slug/
  const match = url.match(/\/empresa\/([^\/]+)/);
  if (match) {
    return match[1].replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  return null;
}

/**
 * Analyze complaint risk level
 * @param {Object} companyData - Company complaints data
 * @returns {Object} Risk analysis
 */
export function analyzeComplaintRisk(companyData) {
  const risk = {
    level: 'baixo', // baixo, medio, alto, critico
    score: 0, // 0-100
    factors: []
  };

  if (!companyData || !companyData.stats) {
    risk.level = 'desconhecido';
    return risk;
  }

  const stats = companyData.stats;

  // Factor 1: Reputation score (inverted - lower is worse)
  if (stats.reputation_score !== undefined) {
    if (stats.reputation_score < 5) {
      risk.score += 30;
      risk.factors.push('Reputação baixa (< 5/10)');
    } else if (stats.reputation_score < 7) {
      risk.score += 15;
      risk.factors.push('Reputação regular (< 7/10)');
    }
  }

  // Factor 2: Resolution rate (lower is worse)
  if (stats.resolution_rate !== undefined) {
    if (stats.resolution_rate < 50) {
      risk.score += 25;
      risk.factors.push('Taxa de resolução baixa (< 50%)');
    } else if (stats.resolution_rate < 70) {
      risk.score += 10;
      risk.factors.push('Taxa de resolução moderada (< 70%)');
    }
  }

  // Factor 3: Would return rate
  if (stats.would_return_rate !== undefined) {
    if (stats.would_return_rate < 30) {
      risk.score += 20;
      risk.factors.push('Poucos clientes voltariam (< 30%)');
    }
  }

  // Factor 4: High complaint volume
  if (stats.complaint_count !== undefined) {
    if (stats.complaint_count > 1000) {
      risk.score += 15;
      risk.factors.push('Alto volume de reclamações (> 1000)');
    }
  }

  // Determine level
  if (risk.score >= 60) {
    risk.level = 'critico';
  } else if (risk.score >= 40) {
    risk.level = 'alto';
  } else if (risk.score >= 20) {
    risk.level = 'medio';
  }

  return risk;
}

/**
 * Enrichment for due diligence - check person/company in Reclame Aqui
 * @param {string} name - Person or company name
 * @param {boolean} isPerson - True if searching for person, false for company
 * @param {string} company - Company name (if isPerson is true)
 * @returns {Promise<Object>} Reclame Aqui enrichment result
 */
export async function enrichReclameAqui(name, isPerson = true, company = null) {
  const result = {
    found: false,
    type: isPerson ? 'pessoa' : 'empresa',
    data: null,
    risk: null
  };

  if (isPerson) {
    const personData = await searchPersonComplaints(name, company);
    result.found = personData.total_found > 0;
    result.data = personData;
    result.risk = {
      level: personData.total_found > 2 ? 'medio' : (personData.total_found > 0 ? 'baixo' : 'nenhum'),
      mentions: personData.total_found
    };
  } else {
    const companyData = await searchCompanyComplaints(name);
    result.found = companyData.company_page !== null || companyData.total_found > 0;
    result.data = companyData;
    result.risk = analyzeComplaintRisk(companyData);
  }

  return result;
}
