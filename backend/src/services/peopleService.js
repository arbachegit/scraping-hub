/**
 * People Search Service
 * Fallback: Apollo → Perplexity → Google
 */

import pino from 'pino';
import { ApolloClient, PerplexityClient, SerperClient } from './apiClients.js';
import { PessoaRepository } from '../database/supabase.js';

const logger = pino({ name: 'people-service' });

export class PeopleService {
  constructor() {
    this.apollo = new ApolloClient();
    this.perplexity = new PerplexityClient();
    this.serper = new SerperClient();
    this.pessoaRepo = new PessoaRepository();
  }

  /**
   * Busca pessoas de uma empresa com fallback
   * Prioridade: Apollo → Perplexity → Google
   */
  async searchPeople(companyName, domain = null) {
    logger.info({ company: companyName }, 'Iniciando busca de pessoas');

    let result = {
      employees: [],
      fonte: null,
      fallbackUsed: false
    };

    // 1. Tentar Apollo primeiro
    try {
      const apolloResult = await this.apollo.getCompanyEmployees(companyName, domain, 50);

      if (apolloResult.employees?.length > 0) {
        result.employees = apolloResult.employees;
        result.fonte = 'Apollo';
        logger.info({ count: result.employees.length, fonte: 'Apollo' }, 'Pessoas encontradas');
        return result;
      }
    } catch (error) {
      logger.warn({ error: error.message }, 'Apollo falhou');
    }

    // 2. Fallback: Perplexity
    try {
      logger.info('Fallback para Perplexity');
      const perplexityResult = await this.perplexity.findPeople(companyName);

      if (perplexityResult?.answer) {
        const extracted = this.extractPeopleFromText(perplexityResult.answer, companyName);
        if (extracted.length > 0) {
          result.employees = extracted;
          result.fonte = 'Perplexity';
          result.fallbackUsed = true;
          logger.info({ count: result.employees.length, fonte: 'Perplexity' }, 'Pessoas encontradas');
          return result;
        }
      }
    } catch (error) {
      logger.warn({ error: error.message }, 'Perplexity falhou');
    }

    // 3. Fallback: Google/Serper
    try {
      logger.info('Fallback para Google');
      const googleResult = await this.serper.search(
        `${companyName} empresa executivos fundadores CEO diretores LinkedIn`
      );

      if (googleResult?.organic) {
        const extracted = this.extractPeopleFromSearch(googleResult.organic, companyName);
        if (extracted.length > 0) {
          result.employees = extracted;
          result.fonte = 'Google';
          result.fallbackUsed = true;
          logger.info({ count: result.employees.length, fonte: 'Google' }, 'Pessoas encontradas');
          return result;
        }
      }
    } catch (error) {
      logger.warn({ error: error.message }, 'Google falhou');
    }

    logger.warn({ company: companyName }, 'Nenhuma pessoa encontrada em nenhuma fonte');
    return result;
  }

  /**
   * Extrai pessoas de texto do Perplexity
   */
  extractPeopleFromText(text, companyName) {
    const people = [];
    const seenNames = new Set();

    // Padrões para encontrar pessoas
    const patterns = [
      /([A-Z][a-záàâãéèêíìîóòôõúùûç]+(?:\s+[A-Z][a-záàâãéèêíìîóòôõúùûç]+)+)\s*[-–:,]\s*(CEO|CTO|CFO|COO|Fundador|Founder|Diretor|Director|Presidente|VP|Head|Sócio|Partner|Gerente|Manager)/gi,
      /(CEO|CTO|CFO|COO|Fundador|Founder|Diretor|Director|Presidente):\s*([A-Z][a-záàâãéèêíìîóòôõúùûç]+(?:\s+[A-Z][a-záàâãéèêíìîóòôõúùûç]+)+)/gi
    ];

    for (const pattern of patterns) {
      let match;
      while ((match = pattern.exec(text)) !== null) {
        const [, part1, part2] = match;
        const name = /^[A-Z]/.test(part1) ? part1.trim() : part2.trim();
        const title = /^[A-Z]/.test(part1) ? part2.trim() : part1.trim();

        if (name && !seenNames.has(name) && name.length > 5) {
          seenNames.add(name);
          people.push({
            name,
            title,
            organization_name: companyName,
            fonte: 'perplexity'
          });
        }
      }
    }

    return people.slice(0, 20);
  }

  /**
   * Extrai pessoas dos resultados de busca Google
   */
  extractPeopleFromSearch(results, companyName) {
    const people = [];
    const seenNames = new Set();

    for (const result of results.slice(0, 10)) {
      const { title, link } = result;

      // Se é um perfil LinkedIn
      if (link?.includes('linkedin.com/in/')) {
        const nameMatch = title?.match(/^([A-Z][a-záàâãéèêíìîóòôõúùûç]+(?:\s+[A-Z][a-záàâãéèêíìîóòôõúùûç]+)+)/);
        if (nameMatch) {
          const name = nameMatch[1];
          if (!seenNames.has(name)) {
            seenNames.add(name);

            // Tentar extrair cargo
            const cargoMatch = title?.match(/[-–|]\s*([^|]+?)(?:\s*[-–|]|$)/);
            const cargo = cargoMatch ? cargoMatch[1].trim() : '';

            people.push({
              name,
              title: cargo,
              linkedin_url: link,
              organization_name: companyName,
              fonte: 'google'
            });
          }
        }
      }
    }

    return people.slice(0, 15);
  }

  /**
   * Salva pessoas no banco de dados
   */
  async savePeople(empresaId, employees) {
    let savedCount = 0;

    for (const emp of employees) {
      try {
        emp.empresa_atual_id = empresaId;
        const pessoaId = await this.pessoaRepo.upsert(emp);
        if (pessoaId) savedCount++;
      } catch (error) {
        logger.warn({ error: error.message, name: emp.name }, 'Erro ao salvar pessoa');
      }
    }

    logger.info({ saved: savedCount, total: employees.length }, 'Pessoas salvas');
    return savedCount;
  }
}

export default PeopleService;
