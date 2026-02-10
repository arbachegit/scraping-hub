const PERPLEXITY_API_KEY = process.env.PERPLEXITY_API_KEY;
const PERPLEXITY_BASE_URL = 'https://api.perplexity.ai';

/**
 * Search for company CNPJ using Perplexity AI
 * @param {string} companyName - Company name
 * @param {string} cidade - Optional city
 * @returns {Promise<Array>} List of candidates with CNPJ
 */
export async function searchCompanyByName(companyName, cidade = null) {
  if (!PERPLEXITY_API_KEY) {
    console.warn('[PERPLEXITY] API key not configured');
    return [];
  }

  try {
    let query = `Qual é o CNPJ da empresa "${companyName}"`;
    if (cidade) {
      query += ` localizada em ${cidade}`;
    }
    query += `? Retorne apenas o CNPJ no formato XX.XXX.XXX/XXXX-XX e a razão social.`;

    const response = await fetch(`${PERPLEXITY_BASE_URL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${PERPLEXITY_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'llama-3.1-sonar-small-128k-online',
        messages: [
          {
            role: 'system',
            content: 'Você é um assistente que busca informações de empresas brasileiras. Retorne apenas dados factuais encontrados na internet.'
          },
          {
            role: 'user',
            content: query
          }
        ],
        temperature: 0.1,
        max_tokens: 500
      })
    });

    if (!response.ok) {
      console.error('[PERPLEXITY] API error:', response.status);
      return [];
    }

    const data = await response.json();
    const content = data.choices?.[0]?.message?.content || '';

    console.log(`[PERPLEXITY] Response for "${companyName}":`, content.substring(0, 200));

    // Extract CNPJ from response
    const cnpjPattern = /\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}/g;
    const matches = content.match(cnpjPattern) || [];

    const candidates = [];
    const seenCnpjs = new Set();

    for (const match of matches) {
      const cnpj = match.replace(/[^\d]/g, '');
      if (cnpj.length === 14 && !seenCnpjs.has(cnpj)) {
        seenCnpjs.add(cnpj);
        candidates.push({
          cnpj: cnpj,
          cnpj_formatted: formatCnpj(cnpj),
          razao_social: extractRazaoSocial(content, companyName),
          localizacao: cidade || null,
          fonte: 'perplexity'
        });
      }
    }

    return candidates;
  } catch (error) {
    console.error('[PERPLEXITY] Error:', error.message);
    return [];
  }
}

/**
 * Search for company details using Perplexity
 * @param {string} cnpj - Company CNPJ
 * @returns {Promise<Object|null>} Company details
 */
export async function getCompanyDetails(cnpj) {
  if (!PERPLEXITY_API_KEY) {
    return null;
  }

  try {
    const cnpjFormatted = formatCnpj(cnpj);
    const query = `Quais são os dados da empresa com CNPJ ${cnpjFormatted}?
    Retorne: razão social, nome fantasia, endereço, cidade, estado, telefone, email, website, setor de atuação.`;

    const response = await fetch(`${PERPLEXITY_BASE_URL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${PERPLEXITY_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'llama-3.1-sonar-small-128k-online',
        messages: [
          {
            role: 'system',
            content: 'Você é um assistente que busca informações de empresas brasileiras. Retorne dados estruturados.'
          },
          {
            role: 'user',
            content: query
          }
        ],
        temperature: 0.1,
        max_tokens: 1000
      })
    });

    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    const content = data.choices?.[0]?.message?.content || '';

    return {
      cnpj: cnpj,
      raw_response: content,
      fonte: 'perplexity'
    };
  } catch (error) {
    console.error('[PERPLEXITY] Error getting details:', error.message);
    return null;
  }
}

/**
 * Format CNPJ with punctuation
 */
function formatCnpj(cnpj) {
  const digits = cnpj.replace(/[^\d]/g, '');
  if (digits.length !== 14) return cnpj;
  return `${digits.slice(0,2)}.${digits.slice(2,5)}.${digits.slice(5,8)}/${digits.slice(8,12)}-${digits.slice(12)}`;
}

/**
 * Extract razao social from response
 */
function extractRazaoSocial(content, searchName) {
  // Try to find company name patterns
  const patterns = [
    /razão social[:\s]+([A-ZÀ-Ú][A-ZÀ-Ú\s\.\-&]+(?:LTDA|S\.?A\.?|ME|EPP|EIRELI)?)/i,
    /empresa[:\s]+([A-ZÀ-Ú][A-ZÀ-Ú\s\.\-&]+(?:LTDA|S\.?A\.?|ME|EPP|EIRELI)?)/i,
    /([A-ZÀ-Ú][A-ZÀ-Ú\s\.\-&]+(?:LTDA|S\.?A\.?|ME|EPP|EIRELI))/
  ];

  for (const pattern of patterns) {
    const match = content.match(pattern);
    if (match) {
      return match[1].trim();
    }
  }

  return searchName;
}
