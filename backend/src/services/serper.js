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
 * Search for company by name and optional city, find CNPJ candidates
 * @param {string} companyName - Company name to search
 * @param {string} cidade - Optional city to filter results
 * @returns {Promise<Array>} List of company candidates with CNPJ
 */
export async function searchCompanyByName(companyName, cidade = null) {
  // Build search query with exact name match and optional city
  let query = `"${companyName}" CNPJ`;
  if (cidade) {
    query += ` "${cidade}"`;
  }
  query += ` site:cnpj.info OR site:consultacnpj.com OR site:casadosdados.com.br`;
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

        // Extract location from multiple sources
        let localizacao = extractLocation(item.title, item.snippet, item.link);

        candidates.push({
          cnpj: cnpj,
          cnpj_formatted: formatCnpj(cnpj),
          razao_social: extractCompanyName(item.title, item.snippet),
          localizacao: localizacao,
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

  // Filter candidates to only include those with the search term in the name
  const searchTermLower = companyName.toLowerCase();
  const filtered = candidates.filter(c => {
    const name = (c.razao_social || '').toLowerCase();
    return name.includes(searchTermLower);
  });

  return filtered;
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
 * Find company official website via Google search
 * @param {string} companyName - Company name
 * @param {string} cidade - City (optional)
 * @returns {Promise<string|null>} Website URL or null
 */
export async function findCompanyWebsite(companyName, cidade = null) {
  let query = `"${companyName}" site oficial`;
  if (cidade) {
    query += ` ${cidade}`;
  }

  const results = await search(query, 10);
  const kg = results.knowledgeGraph;

  // Check knowledge graph first
  if (kg?.website) {
    return kg.website;
  }

  // Look for official website in organic results
  const excludeDomains = [
    'linkedin.com', 'facebook.com', 'instagram.com', 'twitter.com',
    'youtube.com', 'cnpj.info', 'consultacnpj.com', 'casadosdados.com.br',
    'econodata.com.br', 'empresas.serasaexperian.com.br', 'infoplex.com.br'
  ];

  for (const item of results.organic || []) {
    const url = item.link;
    if (!url) continue;

    // Skip social media and CNPJ databases
    const isExcluded = excludeDomains.some(domain => url.includes(domain));
    if (isExcluded) continue;

    // Check if the result seems like the official website
    const titleLower = (item.title || '').toLowerCase();
    const companyLower = companyName.toLowerCase().split(' ')[0]; // First word

    if (titleLower.includes(companyLower) || url.toLowerCase().includes(companyLower)) {
      return url;
    }
  }

  return null;
}

/**
 * Find company LinkedIn via Google search
 * @param {string} companyName - Company name
 * @returns {Promise<string|null>} LinkedIn URL or null
 */
export async function findCompanyLinkedin(companyName) {
  const query = `"${companyName}" site:linkedin.com/company`;
  const results = await search(query, 5);

  for (const item of results.organic || []) {
    if (item.link?.includes('linkedin.com/company')) {
      return item.link;
    }
  }

  return null;
}

/**
 * Extract contacts from a website URL
 * @param {string} websiteUrl - Website URL to scrape
 * @returns {Promise<Object>} Extracted contacts (email, phone, social)
 */
export async function extractContactsFromWebsite(websiteUrl) {
  if (!websiteUrl) return { emails: [], phones: [], social: {} };

  try {
    // Search for contact page
    const domain = new URL(websiteUrl).hostname;
    const query = `site:${domain} contato OR contact OR fale conosco email telefone`;
    const results = await search(query, 5);

    const contacts = {
      emails: new Set(),
      phones: new Set(),
      social: {}
    };

    // Email patterns
    const emailPattern = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
    // Phone patterns (Brazilian)
    const phonePattern = /(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?(?:9?\d{4}[-.\s]?\d{4})/g;

    // Extract from snippets
    for (const item of results.organic || []) {
      const text = `${item.title || ''} ${item.snippet || ''}`;

      // Find emails
      const emails = text.match(emailPattern) || [];
      emails.forEach(e => {
        if (!e.includes('example') && !e.includes('teste')) {
          contacts.emails.add(e.toLowerCase());
        }
      });

      // Find phones
      const phones = text.match(phonePattern) || [];
      phones.forEach(p => {
        const cleaned = p.replace(/\D/g, '');
        if (cleaned.length >= 10 && cleaned.length <= 13) {
          contacts.phones.add(p.trim());
        }
      });
    }

    // Search for social media
    const socialQuery = `site:${domain} instagram OR facebook OR twitter OR whatsapp`;
    const socialResults = await search(socialQuery, 3);

    for (const item of socialResults.organic || []) {
      const text = `${item.snippet || ''}`;

      // Instagram
      const igMatch = text.match(/@([a-zA-Z0-9_.]+)/);
      if (igMatch && !contacts.social.instagram) {
        contacts.social.instagram = `@${igMatch[1]}`;
      }
    }

    return {
      emails: [...contacts.emails],
      phones: [...contacts.phones],
      social: contacts.social
    };
  } catch (error) {
    console.error('[SERPER] Error extracting contacts:', error.message);
    return { emails: [], phones: [], social: {} };
  }
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

/**
 * Extract location from title, snippet or URL
 * @param {string} title - Result title
 * @param {string} snippet - Result snippet
 * @param {string} url - Result URL
 * @returns {string|null} Location in format "Cidade - UF"
 */
function extractLocation(title, snippet, url) {
  const text = `${title || ''} ${snippet || ''}`;

  // Brazilian states
  const estados = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'];

  // Pattern 1: "Cidade - UF" or "Cidade – UF" (most common)
  const p1 = text.match(/([A-Za-zÀ-ú][A-Za-zÀ-ú\s]{2,25})\s*[-–]\s*([A-Z]{2})(?:\s|,|\.|\)|$)/);
  if (p1 && estados.includes(p1[2])) {
    return `${p1[1].trim()} - ${p1[2]}`;
  }

  // Pattern 2: "Cidade/UF"
  const p2 = text.match(/([A-Za-zÀ-ú][A-Za-zÀ-ú\s]{2,25})\/([A-Z]{2})\b/);
  if (p2 && estados.includes(p2[2])) {
    return `${p2[1].trim()} - ${p2[2]}`;
  }

  // Pattern 3: "em Cidade, UF" or "de Cidade, UF" or "Cidade, UF"
  const p3 = text.match(/(?:em\s+|de\s+)?([A-Za-zÀ-ú][A-Za-zÀ-ú\s]{2,25}),\s*([A-Z]{2})\b/i);
  if (p3 && estados.includes(p3[2].toUpperCase())) {
    return `${p3[1].trim()} - ${p3[2].toUpperCase()}`;
  }

  // Pattern 4: "UF - Cidade" (less common)
  const p4 = text.match(/\b([A-Z]{2})\s*[-–]\s*([A-Za-zÀ-ú][A-Za-zÀ-ú\s]{2,25})(?:,|\.|$)/);
  if (p4 && estados.includes(p4[1])) {
    return `${p4[2].trim()} - ${p4[1]}`;
  }

  // Pattern 5: Extract from URL (some sites include city in URL)
  if (url) {
    // cnpj.info format: /cidade-uf/
    const urlMatch = url.match(/\/([a-z-]+)-([a-z]{2})\//i);
    if (urlMatch && estados.includes(urlMatch[2].toUpperCase())) {
      const cidade = urlMatch[1].replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      return `${cidade} - ${urlMatch[2].toUpperCase()}`;
    }
  }

  // Pattern 6: Just state abbreviation at end of text
  const p6 = text.match(/\b([A-Z]{2})$/);
  if (p6 && estados.includes(p6[1])) {
    return p6[1];
  }

  return null;
}
