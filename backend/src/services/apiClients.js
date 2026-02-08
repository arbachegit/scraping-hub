/**
 * API Clients - Apollo, Serper, Perplexity
 */

import axios from 'axios';
import pino from 'pino';

const logger = pino({ name: 'api-clients' });

/**
 * Apollo Client - LinkedIn Data
 */
export class ApolloClient {
  constructor() {
    this.apiKey = process.env.APOLLO_API_KEY;
    this.baseUrl = 'https://api.apollo.io/v1';
  }

  async getCompanyEmployees(organizationName, domain = null, perPage = 50) {
    if (!this.apiKey) {
      logger.warn('Apollo API não configurada');
      return { employees: [], fonte: 'apollo' };
    }

    try {
      const response = await axios.post(
        `${this.baseUrl}/mixed_people/search`,
        {
          q_organization_name: organizationName,
          organization_domains: domain ? [domain] : undefined,
          per_page: perPage
        },
        {
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            'X-Api-Key': this.apiKey
          }
        }
      );

      const employees = (response.data?.people || []).map(p => ({
        id: p.id,
        name: p.name,
        title: p.title,
        email: p.email,
        phone: p.phone_numbers?.[0]?.sanitized_number,
        linkedin_url: p.linkedin_url,
        photo_url: p.photo_url,
        city: p.city,
        state: p.state,
        seniority: p.seniority,
        departments: p.departments?.join(', '),
        organization_name: p.organization?.name || organizationName,
        fonte: 'apollo'
      }));

      logger.info({ count: employees.length, company: organizationName }, 'Apollo: funcionários encontrados');
      return { employees, fonte: 'apollo' };

    } catch (error) {
      logger.error({ error: error.message }, 'Apollo: erro');
      return { employees: [], fonte: 'apollo', error: error.message };
    }
  }
}

/**
 * Serper Client - Google Search
 */
export class SerperClient {
  constructor() {
    this.apiKey = process.env.SERPER_API_KEY;
    this.baseUrl = 'https://google.serper.dev';
  }

  async search(query) {
    if (!this.apiKey) {
      logger.warn('Serper API não configurada');
      return null;
    }

    try {
      const response = await axios.post(
        `${this.baseUrl}/search`,
        { q: query, gl: 'br', hl: 'pt-br' },
        {
          headers: {
            'X-API-KEY': this.apiKey,
            'Content-Type': 'application/json'
          }
        }
      );

      return response.data;

    } catch (error) {
      logger.error({ error: error.message }, 'Serper: erro');
      return null;
    }
  }

  async findCompanyInfo(companyName) {
    const result = await this.search(`${companyName} empresa Brasil site oficial`);
    if (!result) return null;

    const organic = result.organic || [];
    const knowledgeGraph = result.knowledgeGraph || {};

    return {
      website: organic[0]?.link,
      description: knowledgeGraph.description || organic[0]?.snippet,
      industry: knowledgeGraph.type,
      fonte: 'google'
    };
  }

  async searchCompetitors(params) {
    const { location, segment, porte, keywords } = params;

    // Construir query baseada nos parâmetros
    let query = `empresas ${segment || ''}`;

    if (location) {
      query += ` ${location}`;
    }

    if (porte) {
      query += ` porte ${porte}`;
    }

    if (keywords?.length) {
      query += ` ${keywords.slice(0, 3).join(' ')}`;
    }

    query += ' Brasil lista principais';

    logger.info({ query }, 'Buscando concorrentes');
    return await this.search(query);
  }
}

/**
 * Perplexity Client - AI Search
 */
export class PerplexityClient {
  constructor() {
    this.apiKey = process.env.PERPLEXITY_API_KEY;
    this.baseUrl = 'https://api.perplexity.ai';
  }

  async search(query) {
    if (!this.apiKey) {
      logger.warn('Perplexity API não configurada');
      return null;
    }

    try {
      const response = await axios.post(
        `${this.baseUrl}/chat/completions`,
        {
          model: 'llama-3.1-sonar-small-128k-online',
          messages: [
            {
              role: 'system',
              content: 'Você é um assistente especializado em pesquisa de empresas brasileiras. Responda de forma concisa e factual.'
            },
            {
              role: 'user',
              content: query
            }
          ],
          max_tokens: 1000
        },
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json'
          }
        }
      );

      return {
        answer: response.data?.choices?.[0]?.message?.content,
        fonte: 'perplexity'
      };

    } catch (error) {
      logger.error({ error: error.message }, 'Perplexity: erro');
      return null;
    }
  }

  async findPeople(companyName) {
    const query = `Quem são os principais executivos, fundadores e líderes da empresa ${companyName} Brasil? Liste nomes, cargos e LinkedIn se disponível.`;
    return await this.search(query);
  }

  async findCompetitors(companyName, location, segment, porte) {
    let query = `Liste 5-10 empresas brasileiras concorrentes ou similares a ${companyName}`;

    if (location) query += ` na região de ${location}`;
    if (segment) query += ` no segmento de ${segment}`;
    if (porte) query += ` de porte ${porte}`;

    query += '. Para cada uma, informe: nome, website, e por que é concorrente.';

    return await this.search(query);
  }
}

/**
 * BrasilAPI Client - CNPJ Data
 */
export class BrasilAPIClient {
  constructor() {
    this.baseUrl = 'https://brasilapi.com.br/api';
  }

  async getCNPJ(cnpj) {
    try {
      const cleanCnpj = cnpj.replace(/\D/g, '');
      const response = await axios.get(`${this.baseUrl}/cnpj/v1/${cleanCnpj}`);
      return response.data;
    } catch (error) {
      logger.error({ error: error.message, cnpj }, 'BrasilAPI: erro');
      return null;
    }
  }
}

export default {
  ApolloClient,
  SerperClient,
  PerplexityClient,
  BrasilAPIClient
};
