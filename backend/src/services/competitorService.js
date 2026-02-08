/**
 * Competitor Search Service
 * Busca concorrentes por: Localização → Segmento → Porte → Tipo de Cliente
 * Fallback: Google → Perplexity
 */

import pino from 'pino';
import { SerperClient, PerplexityClient, BrasilAPIClient } from './apiClients.js';
import { EmpresaRepository, ConcorrenteRepository, AnaliseRepository } from '../database/supabase.js';

const logger = pino({ name: 'competitor-service' });

export class CompetitorService {
  constructor() {
    this.serper = new SerperClient();
    this.perplexity = new PerplexityClient();
    this.brasilApi = new BrasilAPIClient();
    this.empresaRepo = new EmpresaRepository();
    this.concorrenteRepo = new ConcorrenteRepository();
    this.analiseRepo = new AnaliseRepository();
  }

  /**
   * Busca concorrentes baseado nas características da empresa
   * Ordem de prioridade:
   * 1. Localização (cidade/estado)
   * 2. Segmento/Setor
   * 3. Porte
   * 4. Tipo de clientes atendidos
   */
  async searchCompetitors(empresa) {
    const {
      id: empresaId,
      nome_fantasia: companyName,
      cidade,
      estado,
      setor,
      porte,
      palavras_chave: keywords = []
    } = empresa;

    logger.info({
      company: companyName,
      cidade,
      estado,
      setor,
      porte
    }, 'Iniciando busca de concorrentes');

    const competitors = [];
    const queries = [];

    // 1. Busca por localização + segmento
    if (cidade && setor) {
      queries.push({
        type: 'local_segment',
        query: `empresas ${setor} ${cidade} ${estado || ''} principais concorrentes`,
        priority: 1
      });
    }

    // 2. Busca por segmento + porte
    if (setor) {
      queries.push({
        type: 'segment_porte',
        query: `empresas ${setor} ${porte || ''} Brasil principais líderes mercado`,
        priority: 2
      });
    }

    // 3. Busca por palavras-chave
    if (keywords.length > 0) {
      const keywordsStr = keywords.slice(0, 5).join(' ');
      queries.push({
        type: 'keywords',
        query: `empresas brasileiras ${keywordsStr} ${estado || 'Brasil'}`,
        priority: 3
      });
    }

    // 4. Busca genérica por nome
    queries.push({
      type: 'generic',
      query: `empresas concorrentes ${companyName} Brasil mesmo segmento`,
      priority: 4
    });

    // Executar buscas em ordem de prioridade
    for (const q of queries) {
      logger.info({ type: q.type, query: q.query }, 'Executando busca');

      // Tentar Google primeiro
      let searchResult = await this.serper.search(q.query);
      let fonte = 'google';

      // Fallback para Perplexity
      if (!searchResult?.organic?.length) {
        logger.info('Fallback para Perplexity');
        const perplexityResult = await this.perplexity.search(
          `Liste 5 empresas brasileiras que são concorrentes de ${companyName} no segmento ${setor || ''}. ${q.query}`
        );
        if (perplexityResult?.answer) {
          searchResult = { perplexityAnswer: perplexityResult.answer };
          fonte = 'perplexity';
        }
      }

      if (!searchResult) continue;

      // Extrair nomes de empresas
      const extracted = fonte === 'google'
        ? this.extractCompaniesFromSearch(searchResult.organic || [], companyName)
        : this.extractCompaniesFromText(searchResult.perplexityAnswer, companyName);

      for (const comp of extracted) {
        // Evitar duplicatas
        if (competitors.some(c => c.name.toLowerCase() === comp.name.toLowerCase())) {
          continue;
        }

        // Evitar a própria empresa
        if (comp.name.toLowerCase() === companyName.toLowerCase()) {
          continue;
        }

        competitors.push({
          ...comp,
          searchType: q.type,
          query: q.query,
          fonte
        });
      }

      // Se já temos 5+ concorrentes, parar
      if (competitors.length >= 5) break;
    }

    logger.info({
      company: companyName,
      found: competitors.length
    }, 'Concorrentes encontrados');

    return competitors;
  }

  /**
   * Extrai empresas dos resultados de busca Google
   */
  extractCompaniesFromSearch(results, excludeName) {
    const companies = [];
    const seenNames = new Set();

    for (const result of results.slice(0, 15)) {
      const { title, link, snippet } = result;

      // Evitar LinkedIn e sites genéricos
      if (link?.includes('linkedin.com') || link?.includes('wikipedia.org')) {
        continue;
      }

      // Tentar extrair nome da empresa do título
      const nameMatch = title?.match(/^([A-Z][^|–-]+?)(?:\s*[-–|]|$)/);
      if (nameMatch) {
        const name = nameMatch[1].trim();

        if (
          name &&
          name.length > 3 &&
          name.length < 50 &&
          !seenNames.has(name.toLowerCase()) &&
          name.toLowerCase() !== excludeName.toLowerCase()
        ) {
          seenNames.add(name.toLowerCase());
          companies.push({
            name,
            website: link,
            description: snippet?.slice(0, 200)
          });
        }
      }
    }

    return companies.slice(0, 10);
  }

  /**
   * Extrai empresas de texto do Perplexity
   */
  extractCompaniesFromText(text, excludeName) {
    const companies = [];
    const seenNames = new Set();

    // Padrões para encontrar empresas
    const patterns = [
      /\d+\.\s*\*?\*?([A-Z][^:,\n*]+?)\*?\*?(?:\s*[-–:]|\s*\n)/g,
      /(?:concorrentes?|empresas?):\s*([A-Z][^,.\n]+)/gi,
      /\*\*([A-Z][^*]+)\*\*/g
    ];

    for (const pattern of patterns) {
      let match;
      while ((match = pattern.exec(text)) !== null) {
        const name = match[1].trim().replace(/\*+/g, '');

        if (
          name &&
          name.length > 3 &&
          name.length < 50 &&
          !seenNames.has(name.toLowerCase()) &&
          name.toLowerCase() !== excludeName.toLowerCase()
        ) {
          seenNames.add(name.toLowerCase());
          companies.push({ name });
        }
      }
    }

    return companies.slice(0, 10);
  }

  /**
   * Analisa e salva concorrentes
   * Faz análise simplificada de cada concorrente e salva no banco
   */
  async analyzeAndSaveCompetitors(empresaId, companyName, competitors, sourceKeywords = []) {
    const saved = [];

    for (const comp of competitors) {
      try {
        // 1. Buscar dados básicos
        const companyInfo = await this.serper.findCompanyInfo(comp.name);

        // 2. Tentar buscar CNPJ
        let cnpjData = null;
        const cnpjSearch = await this.serper.search(`${comp.name} CNPJ`);
        if (cnpjSearch?.organic?.[0]) {
          const cnpjMatch = cnpjSearch.organic[0].snippet?.match(/\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}/);
          if (cnpjMatch) {
            cnpjData = await this.brasilApi.getCNPJ(cnpjMatch[0]);
          }
        }

        // 3. Preparar dados da empresa concorrente
        const concorrenteData = {
          cnpj: cnpjData?.cnpj,
          nome_fantasia: comp.name,
          razao_social: cnpjData?.razao_social,
          website: comp.website || companyInfo?.website,
          setor: companyInfo?.industry,
          cidade: cnpjData?.municipio,
          estado: cnpjData?.uf,
          raw_cnpj_data: cnpjData || {},
          raw_search_data: companyInfo || {}
        };

        // 4. Salvar empresa concorrente
        const concorrenteId = await this.empresaRepo.upsert(concorrenteData);

        if (!concorrenteId) continue;

        // 5. Calcular match de keywords
        const compDescription = `${comp.description || ''} ${companyInfo?.description || ''} ${companyInfo?.industry || ''}`.toLowerCase();
        const keywordsMatch = sourceKeywords.filter(kw =>
          compDescription.includes(kw.toLowerCase())
        );

        // 6. Determinar stamp baseado na similaridade
        const similarityScore = keywordsMatch.length / Math.max(sourceKeywords.length, 1);
        let stamp = 'Medio';
        if (similarityScore > 0.6) stamp = 'Forte';
        else if (similarityScore < 0.3) stamp = 'Fraco';

        // 7. Salvar relação de concorrência
        await this.concorrenteRepo.save(empresaId, concorrenteId, {
          tipo: 'direto',
          keywords_match: keywordsMatch,
          similarity_score: similarityScore,
          stamp,
          justification: `${keywordsMatch.length} palavras-chave em comum. Encontrado via ${comp.fonte}.`,
          fonte: comp.fonte,
          query: comp.query
        });

        saved.push({
          id: concorrenteId,
          name: comp.name,
          stamp,
          fonte: comp.fonte
        });

        logger.info({
          concorrente: comp.name,
          stamp,
          keywords: keywordsMatch.length
        }, 'Concorrente salvo');

      } catch (error) {
        logger.warn({ error: error.message, name: comp.name }, 'Erro ao salvar concorrente');
      }
    }

    return saved;
  }
}

export default CompetitorService;
