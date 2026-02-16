/**
 * Google Scholar Service (via Serper)
 * Publicações acadêmicas, citações, h-index
 */

import logger from '../utils/logger.js';

const SERPER_API_KEY = process.env.SERPER_API_KEY;
const SERPER_BASE_URL = 'https://google.serper.dev';

/**
 * Search Google Scholar via Serper
 * @param {string} query - Search query
 * @param {number} num - Number of results
 * @returns {Promise<Object>} Search results
 */
async function scholarSearch(query, num = 10) {
  const response = await fetch(`${SERPER_BASE_URL}/scholar`, {
    method: 'POST',
    headers: {
      'X-API-KEY': SERPER_API_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      q: query,
      num: Math.min(num, 20)
    })
  });

  if (!response.ok) {
    throw new Error(`Serper Scholar API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Search for academic publications by person name
 * @param {string} authorName - Author name
 * @param {string} institution - Optional institution filter
 * @returns {Promise<Array>} List of publications
 */
export async function searchPublicationsByAuthor(authorName, institution = null) {
  let query = `author:"${authorName}"`;
  if (institution) {
    query += ` "${institution}"`;
  }

  try {
    const results = await scholarSearch(query, 20);
    const publications = [];

    for (const item of results.organic || []) {
      publications.push({
        title: item.title,
        link: item.link,
        snippet: item.snippet,
        publication_info: item.publicationInfo || item.publication,
        cited_by: extractCitationCount(item),
        year: extractYear(item),
        authors: extractAuthors(item)
      });
    }

    return publications;
  } catch (error) {
    logger.error('Google Scholar search error', { error: error.message, author: authorName });
    return [];
  }
}

/**
 * Get citation count from publication item
 * @param {Object} item - Publication item
 * @returns {number} Citation count
 */
function extractCitationCount(item) {
  // Serper returns citation info in different formats
  if (item.citedBy) {
    const match = String(item.citedBy).match(/\d+/);
    return match ? parseInt(match[0]) : 0;
  }
  if (item.inlineLinks) {
    for (const link of item.inlineLinks) {
      if (link.title?.toLowerCase().includes('cited by')) {
        const match = link.title.match(/\d+/);
        return match ? parseInt(match[0]) : 0;
      }
    }
  }
  return 0;
}

/**
 * Extract year from publication item
 * @param {Object} item - Publication item
 * @returns {number|null} Publication year
 */
function extractYear(item) {
  const text = `${item.publicationInfo || ''} ${item.snippet || ''}`;
  const yearMatch = text.match(/\b(19|20)\d{2}\b/);
  return yearMatch ? parseInt(yearMatch[0]) : null;
}

/**
 * Extract authors from publication item
 * @param {Object} item - Publication item
 * @returns {Array} List of author names
 */
function extractAuthors(item) {
  if (item.authors) {
    return item.authors;
  }

  const pubInfo = item.publicationInfo || '';
  // Authors are usually before the year or venue
  const authorPart = pubInfo.split(/\s+-\s+|\s+\d{4}/)[0];
  if (authorPart) {
    return authorPart.split(/,\s*/).filter(a => a.length > 2);
  }

  return [];
}

/**
 * Calculate academic metrics from publications
 * @param {Array} publications - List of publications
 * @returns {Object} Academic metrics
 */
export function calculateAcademicMetrics(publications) {
  if (!publications.length) {
    return {
      total_publications: 0,
      total_citations: 0,
      h_index: 0,
      avg_citations: 0,
      first_publication_year: null,
      last_publication_year: null,
      top_publication: null
    };
  }

  // Sort by citations descending
  const sorted = [...publications].sort((a, b) => (b.cited_by || 0) - (a.cited_by || 0));

  const totalCitations = publications.reduce((sum, p) => sum + (p.cited_by || 0), 0);

  // Calculate h-index
  let hIndex = 0;
  for (let i = 0; i < sorted.length; i++) {
    if (sorted[i].cited_by >= i + 1) {
      hIndex = i + 1;
    } else {
      break;
    }
  }

  // Get publication year range
  const years = publications.map(p => p.year).filter(y => y);
  const firstYear = years.length ? Math.min(...years) : null;
  const lastYear = years.length ? Math.max(...years) : null;

  return {
    total_publications: publications.length,
    total_citations: totalCitations,
    h_index: hIndex,
    avg_citations: Math.round(totalCitations / publications.length * 10) / 10,
    first_publication_year: firstYear,
    last_publication_year: lastYear,
    top_publication: sorted[0] || null
  };
}

/**
 * Analyze academic competencies
 * @param {Object} metrics - Academic metrics
 * @returns {Object} Competencies analysis
 */
export function analyzeAcademicCompetencies(metrics) {
  const competencies = {
    nivel_academico: 'iniciante', // iniciante, pesquisador, senior, autoridade
    score_publicacoes: 0,
    score_impacto: 0,
    areas_atuacao: []
  };

  if (!metrics.total_publications) {
    return competencies;
  }

  // Publication score (0-50)
  competencies.score_publicacoes = Math.min(metrics.total_publications * 3, 50);

  // Impact score based on citations and h-index (0-50)
  const citationScore = Math.min(metrics.total_citations * 0.1, 25);
  const hScore = Math.min(metrics.h_index * 2.5, 25);
  competencies.score_impacto = Math.round(citationScore + hScore);

  // Determine level
  const totalScore = competencies.score_publicacoes + competencies.score_impacto;
  if (totalScore >= 80 && metrics.h_index >= 20) {
    competencies.nivel_academico = 'autoridade';
  } else if (totalScore >= 50 && metrics.h_index >= 10) {
    competencies.nivel_academico = 'senior';
  } else if (totalScore >= 20) {
    competencies.nivel_academico = 'pesquisador';
  }

  return competencies;
}

/**
 * Search and analyze person's academic presence
 * @param {string} name - Person name
 * @param {string} institution - Institution name (optional)
 * @returns {Promise<Object>} Academic enrichment result
 */
export async function enrichPersonAcademic(name, institution = null) {
  const result = {
    found: false,
    publications: [],
    metrics: null,
    competencies: null
  };

  const publications = await searchPublicationsByAuthor(name, institution);

  if (!publications.length) {
    return result;
  }

  result.found = true;
  result.publications = publications;
  result.metrics = calculateAcademicMetrics(publications);
  result.competencies = analyzeAcademicCompetencies(result.metrics);

  return result;
}
