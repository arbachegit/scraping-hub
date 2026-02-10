const SERPER_API_KEY = process.env.SERPER_API_KEY;
const SERPER_BASE_URL = 'https://google.serper.dev';

/**
 * Make request to Serper API
 * @param {string} endpoint - API endpoint
 * @param {Object} payload - Request payload
 * @returns {Promise<Object>} API response
 */
async function serperRequest(endpoint, payload) {
  const response = await fetch(`${SERPER_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: {
      'X-API-KEY': SERPER_API_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Serper API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Search Google via Serper
 * @param {string} query - Search query
 * @param {number} num - Number of results
 * @returns {Promise<Object>} Search results
 */
export async function search(query, num = 10) {
  return serperRequest('/search', {
    q: query,
    num: Math.min(num, 100),
    gl: 'br',
    hl: 'pt-br'
  });
}

/**
 * Search for company by name, find CNPJ candidates
 * @param {string} companyName - Company name to search
 * @returns {Promise<Array>} List of company candidates with CNPJ
 */
export async function searchCompanyByName(companyName) {
  // Search in CNPJ databases
  const query = `"${companyName}" CNPJ site:cnpj.info OR site:consultacnpj.com OR site:casadosdados.com.br`;
  const results = await search(query, 20);

  const candidates = [];
  const cnpjPattern = /\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}/g;
  const seenCnpjs = new Set();

  // Extract from organic results
  for (const item of results.organic || []) {
    const text = `${item.title || ''} ${item.snippet || ''}`;
    const matches = text.match(cnpjPattern) || [];

    for (const match of matches) {
      const cnpj = match.replace(/[^\d]/g, '');
      if (cnpj.length === 14 && !seenCnpjs.has(cnpj)) {
        seenCnpjs.add(cnpj);

        // Extract location from snippet
        const locationMatch = item.snippet?.match(/([A-Z]{2})\s*[-–]\s*([^,\n]+)/i);

        candidates.push({
          cnpj: cnpj,
          cnpj_formatted: formatCnpj(cnpj),
          razao_social: extractCompanyName(item.title, item.snippet),
          localizacao: locationMatch ? `${locationMatch[2].trim()} - ${locationMatch[1]}` : null,
          fonte_url: item.link,
          snippet: item.snippet
        });
      }
    }
  }

  // Also search in knowledge graph
  const kg = results.knowledgeGraph;
  if (kg) {
    const cnpjFromKg = kg.cnpj || kg.CNPJ;
    if (cnpjFromKg) {
      const cnpj = cnpjFromKg.replace(/[^\d]/g, '');
      if (cnpj.length === 14 && !seenCnpjs.has(cnpj)) {
        candidates.unshift({
          cnpj: cnpj,
          cnpj_formatted: formatCnpj(cnpj),
          razao_social: kg.title || companyName,
          localizacao: kg.headquarters || kg.address,
          fonte_url: kg.website,
          snippet: kg.description,
          knowledge_graph: true
        });
      }
    }
  }

  return candidates;
}

/**
 * Get detailed company info by CNPJ
 * @param {string} cnpj - Company CNPJ
 * @returns {Promise<Object>} Company details
 */
export async function getCompanyDetails(cnpj) {
  const cnpjFormatted = formatCnpj(cnpj);

  // Search for company details
  const query = `CNPJ ${cnpjFormatted}`;
  const results = await search(query, 10);

  // Search for LinkedIn
  const linkedinQuery = `CNPJ ${cnpjFormatted} site:linkedin.com/company`;
  const linkedinResults = await search(linkedinQuery, 3);

  let linkedin = null;
  for (const item of linkedinResults.organic || []) {
    if (item.link?.includes('linkedin.com/company')) {
      linkedin = item.link;
      break;
    }
  }

  // Extract info from knowledge graph
  const kg = results.knowledgeGraph || {};

  return {
    cnpj: cnpj,
    cnpj_formatted: cnpjFormatted,
    razao_social: kg.title || null,
    nome_fantasia: null,
    website: kg.website || null,
    linkedin: linkedin,
    endereco: kg.address || kg.headquarters || null,
    cidade: null,
    estado: null,
    setor: kg.industry || kg.type || null,
    descricao: kg.description || null,
    data_fundacao: kg.founded || kg.foundingDate || null,
    num_funcionarios: kg.employees || kg.numberOfEmployees || null,
    fundadores: extractFounders(results),
    organic_results: results.organic || []
  };
}

/**
 * Extract founders from search results
 * @param {Object} results - Search results
 * @returns {Array} List of founders
 */
function extractFounders(results) {
  const founders = [];
  const kg = results.knowledgeGraph || {};

  // Check for founders in knowledge graph
  if (kg.founders) {
    const foundersList = Array.isArray(kg.founders) ? kg.founders : [kg.founders];
    for (const founder of foundersList) {
      founders.push({
        nome: typeof founder === 'string' ? founder : founder.name,
        linkedin: null
      });
    }
  }

  // Check for CEO/executives
  if (kg.ceo) {
    founders.push({
      nome: typeof kg.ceo === 'string' ? kg.ceo : kg.ceo.name,
      cargo: 'CEO',
      linkedin: null
    });
  }

  return founders;
}

/**
 * Search LinkedIn for a person
 * @param {string} name - Person name
 * @param {string} company - Company name (optional)
 * @returns {Promise<string|null>} LinkedIn URL or null
 */
export async function findPersonLinkedin(name, company = null) {
  let query = `"${name}" site:linkedin.com/in`;
  if (company) {
    query += ` "${company}"`;
  }

  const results = await search(query, 5);

  for (const item of results.organic || []) {
    if (item.link?.includes('linkedin.com/in/')) {
      return item.link;
    }
  }

  return null;
}

/**
 * Format CNPJ with punctuation
 * @param {string} cnpj - CNPJ digits only
 * @returns {string} Formatted CNPJ
 */
function formatCnpj(cnpj) {
  const digits = cnpj.replace(/[^\d]/g, '');
  if (digits.length !== 14) return cnpj;
  return `${digits.slice(0,2)}.${digits.slice(2,5)}.${digits.slice(5,8)}/${digits.slice(8,12)}-${digits.slice(12)}`;
}

/**
 * Extract company name from title/snippet
 * @param {string} title - Result title
 * @param {string} snippet - Result snippet
 * @returns {string|null} Company name
 */
function extractCompanyName(title, snippet) {
  // Try to extract from title (usually format: "COMPANY NAME - CNPJ...")
  if (title) {
    const match = title.match(/^([^-–|]+)/);
    if (match) {
      return match[1].trim();
    }
  }
  return title || null;
}
