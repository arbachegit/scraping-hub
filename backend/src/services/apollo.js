const APOLLO_API_KEY = process.env.APOLLO_API_KEY;
const APOLLO_BASE_URL = 'https://api.apollo.io/v1';

/**
 * Make request to Apollo API
 * @param {string} endpoint - API endpoint
 * @param {Object} payload - Request payload
 * @returns {Promise<Object>} API response
 */
async function apolloRequest(endpoint, payload) {
  if (!APOLLO_API_KEY) {
    console.warn('[APOLLO] API key not configured');
    return null;
  }

  const response = await fetch(`${APOLLO_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-cache',
      'X-Api-Key': APOLLO_API_KEY
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    console.error(`[APOLLO] Error: ${response.status}`);
    return null;
  }

  return response.json();
}

/**
 * Search for company by name in Brazil
 * @param {string} companyName - Company name
 * @param {string} state - State (SP, RJ, etc)
 * @returns {Promise<Object|null>} Company data with LinkedIn and website
 */
export async function searchCompany(companyName, state = null) {
  const locations = state ? [`${state}, Brazil`] : ['Brazil'];

  const result = await apolloRequest('/mixed_companies/search', {
    q_organization_name: companyName,
    organization_locations: locations,
    page: 1,
    per_page: 5
  });

  if (!result || !result.organizations || result.organizations.length === 0) {
    return null;
  }

  // Find best match
  const org = result.organizations[0];

  return {
    name: org.name,
    website: org.website_url,
    linkedin: org.linkedin_url,
    twitter: org.twitter_url,
    facebook: org.facebook_url,
    industry: org.industry,
    num_employees: org.estimated_num_employees,
    founded_year: org.founded_year,
    logo_url: org.logo_url,
    phone: org.phone,
    city: org.city,
    state: org.state,
    country: org.country,
    description: org.short_description,
    raw_apollo: org
  };
}

/**
 * Enrich company by domain
 * @param {string} domain - Company website domain
 * @returns {Promise<Object|null>} Enriched company data
 */
export async function enrichCompanyByDomain(domain) {
  const result = await apolloRequest('/organizations/enrich', {
    domain: domain
  });

  if (!result || !result.organization) {
    return null;
  }

  const org = result.organization;

  return {
    name: org.name,
    website: org.website_url,
    linkedin: org.linkedin_url,
    twitter: org.twitter_url,
    industry: org.industry,
    num_employees: org.estimated_num_employees,
    founded_year: org.founded_year,
    logo_url: org.logo_url,
    description: org.short_description,
    raw_apollo: org
  };
}

/**
 * Search for person by name and company
 * @param {string} personName - Person full name
 * @param {string} companyName - Company name
 * @returns {Promise<Object|null>} Person data with LinkedIn
 */
export async function searchPerson(personName, companyName) {
  const result = await apolloRequest('/mixed_people/search', {
    q_person_name: personName,
    q_organization_name: companyName,
    organization_locations: ['Brazil'],
    page: 1,
    per_page: 5
  });

  if (!result || !result.people || result.people.length === 0) {
    return null;
  }

  // Find best match by name similarity
  const nameLower = personName.toLowerCase();
  const person = result.people.find(p => {
    const pName = (p.name || '').toLowerCase();
    return pName.includes(nameLower) || nameLower.includes(pName);
  }) || result.people[0];

  return {
    name: person.name,
    first_name: person.first_name,
    last_name: person.last_name,
    title: person.title,
    email: person.email,
    linkedin: person.linkedin_url,
    twitter: person.twitter_url,
    phone_numbers: person.phone_numbers,
    photo_url: person.photo_url,
    city: person.city,
    state: person.state,
    headline: person.headline,
    seniority: person.seniority,
    departments: person.departments,
    company: {
      name: person.organization_name || person.organization?.name,
      website: person.organization?.website_url,
      linkedin: person.organization?.linkedin_url
    },
    raw_apollo: person
  };
}

/**
 * Enrich person by email
 * @param {string} email - Person email
 * @param {string} firstName - First name (optional)
 * @param {string} lastName - Last name (optional)
 * @param {string} companyName - Company name (optional)
 * @returns {Promise<Object|null>} Enriched person data
 */
export async function enrichPersonByEmail(email, firstName = null, lastName = null, companyName = null) {
  const payload = { email };
  if (firstName) payload.first_name = firstName;
  if (lastName) payload.last_name = lastName;
  if (companyName) payload.organization_name = companyName;

  const result = await apolloRequest('/people/match', payload);

  if (!result || !result.person) {
    return null;
  }

  const person = result.person;

  return {
    name: person.name,
    first_name: person.first_name,
    last_name: person.last_name,
    title: person.title,
    email: person.email,
    linkedin: person.linkedin_url,
    twitter: person.twitter_url,
    photo_url: person.photo_url,
    headline: person.headline,
    seniority: person.seniority,
    company: {
      name: person.organization_name,
      website: person.organization?.website_url,
      linkedin: person.organization?.linkedin_url
    },
    raw_apollo: person
  };
}

/**
 * Get company executives
 * @param {string} companyName - Company name
 * @param {string} domain - Company domain (optional)
 * @returns {Promise<Array>} List of executives
 */
export async function getCompanyExecutives(companyName, domain = null) {
  const payload = {
    q_organization_name: companyName,
    person_seniorities: ['owner', 'founder', 'c_suite', 'partner', 'vp', 'director'],
    organization_locations: ['Brazil'],
    page: 1,
    per_page: 20
  };

  if (domain) {
    payload.organization_domains = [domain];
  }

  const result = await apolloRequest('/mixed_people/search', payload);

  if (!result || !result.people) {
    return [];
  }

  return result.people.map(person => ({
    name: person.name,
    title: person.title,
    email: person.email,
    linkedin: person.linkedin_url,
    photo_url: person.photo_url,
    seniority: person.seniority,
    raw_apollo: person
  }));
}

/**
 * Enrich socios list with Apollo data
 * @param {Array} socios - List of socios from BrasilAPI
 * @param {string} companyName - Company name
 * @returns {Promise<Array>} Enriched socios
 */
export async function enrichSocios(socios, companyName) {
  const enriched = [];

  for (const socio of socios) {
    // Try to find on Apollo by name + company
    const apolloData = await searchPerson(socio.nome, companyName);

    if (apolloData) {
      enriched.push({
        ...socio,
        linkedin: apolloData.linkedin || socio.linkedin,
        email: apolloData.email || socio.email,
        foto_url: apolloData.photo_url,
        headline: apolloData.headline,
        raw_apollo: apolloData.raw_apollo
      });
    } else {
      enriched.push(socio);
    }

    // Rate limit: wait 200ms between requests
    await new Promise(resolve => setTimeout(resolve, 200));
  }

  return enriched;
}
