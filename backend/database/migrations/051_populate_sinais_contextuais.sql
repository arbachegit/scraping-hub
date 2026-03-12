-- ============================================================
-- Migration 051: Populate dim_sinais_contextuais
-- Predefined contextual signals for news detection
-- ============================================================

-- Economia
INSERT INTO dim_sinais_contextuais (nome, slug, categoria, tipo, keywords_regex, descricao, prioridade, ativo)
VALUES
  ('Inflação em Alta', 'inflacao-alta', 'economia', 'alerta', 'infla[çc][ãa]o.*(alta|sobe|aceler|press[ãa]o|estoura)', 'Indicadores de pressão inflacionária', 90, true),
  ('Inflação Controlada', 'inflacao-controlada', 'economia', 'positivo', 'infla[çc][ãa]o.*(control|queda|desacel|recua)', 'Indicadores de desaceleração inflacionária', 70, true),
  ('Crescimento PIB', 'crescimento-pib', 'economia', 'positivo', '(PIB|produto interno).*(cresc|avanç|alta|expan)', 'Crescimento do produto interno bruto', 85, true),
  ('Recessão', 'recessao', 'economia', 'alerta', '(recess[ãa]o|contra[çc][ãa]o|encolh|PIB.*(queda|retra|nega))', 'Indicadores de recessão econômica', 95, true),
  ('Investimento Estrangeiro', 'investimento-estrangeiro', 'economia', 'positivo', '(investimento estrangeiro|IED|capital externo|ingressos)', 'Fluxo de investimento estrangeiro', 75, true),
  ('Desemprego', 'desemprego', 'economia', 'alerta', '(desemprego|desocupa[çc][ãa]o).*(alta|sobe|cresc|recorde)', 'Aumento do desemprego', 90, true),
  ('Selic', 'taxa-selic', 'economia', 'sinal', '(Selic|taxa.*(jur|b[áa]sic)).*(sobe|alta|elev|aument|corte|queda|redu)', 'Movimentação da taxa Selic', 85, true),
  ('Câmbio', 'cambio-dolar', 'economia', 'sinal', '(d[óo]lar|c[âa]mbio|real).*(alta|queda|desvalor|valor)', 'Variação cambial significativa', 80, true)
ON CONFLICT (slug) DO NOTHING;

-- Política
INSERT INTO dim_sinais_contextuais (nome, slug, categoria, tipo, keywords_regex, descricao, prioridade, ativo)
VALUES
  ('Reforma Tributária', 'reforma-tributaria', 'politica', 'sinal', '(reforma tribut[áa]r|IBS|CBS|imposto.*(reform|mud))', 'Avanços na reforma tributária', 90, true),
  ('Reforma Administrativa', 'reforma-administrativa', 'politica', 'sinal', '(reforma administrat|servi[çc]o p[úu]blico.*(reform|reestrutur))', 'Mudanças na administração pública', 80, true),
  ('Crise Política', 'crise-politica', 'politica', 'alerta', '(crise pol[íi]tic|impeachment|instabilidade|ruptura institucional)', 'Instabilidade política', 95, true),
  ('Coalizão', 'coalizao', 'politica', 'sinal', '(coaliz[ãa]o|base aliada|acordo partid|negocia[çc][ãa]o pol)', 'Movimentações de coalizão política', 70, true),
  ('Eleição', 'eleicao', 'politica', 'sinal', '(elei[çc][ãa]o|pesquisa eleitoral|candidat|campanha eleitoral|TSE)', 'Temas eleitorais', 85, true),
  ('Orçamento Público', 'orcamento-publico', 'politica', 'sinal', '(or[çc]amento|LOA|LDO|PPA|emenda parlamentar|gasto p[úu]blico)', 'Questões orçamentárias', 80, true)
ON CONFLICT (slug) DO NOTHING;

-- Mercado
INSERT INTO dim_sinais_contextuais (nome, slug, categoria, tipo, keywords_regex, descricao, prioridade, ativo)
VALUES
  ('Bolsa em Alta', 'bolsa-alta', 'mercado', 'positivo', '(Ibovespa|bolsa|B3).*(alta|recorde|sobe|avan)', 'Mercado acionário em alta', 75, true),
  ('Bolsa em Queda', 'bolsa-queda', 'mercado', 'alerta', '(Ibovespa|bolsa|B3).*(queda|cai|recua|tombo)', 'Mercado acionário em queda', 80, true),
  ('IPO/Abertura Capital', 'ipo', 'mercado', 'sinal', '(IPO|abertura de capital|oferta p[úu]blica|listagem)', 'Nova abertura de capital', 70, true),
  ('Fusão e Aquisição', 'fusao-aquisicao', 'mercado', 'sinal', '(fus[ãa]o|aquisi[çc][ãa]o|M&A|compra.*(empresa|controle)|incorpora)', 'Movimentação de M&A', 75, true),
  ('Risco Fiscal', 'risco-fiscal', 'mercado', 'alerta', '(risco fiscal|d[íi]vida p[úu]blica|d[ée]ficit|furo.*(teto|meta)|arcabou[çc]o)', 'Deterioração fiscal', 90, true)
ON CONFLICT (slug) DO NOTHING;

-- Saúde
INSERT INTO dim_sinais_contextuais (nome, slug, categoria, tipo, keywords_regex, descricao, prioridade, ativo)
VALUES
  ('Epidemia', 'epidemia', 'saude', 'alerta', '(epidemia|pandemia|surto|emerg[êe]ncia sanit[áa]r|dengue.*explos)', 'Emergência sanitária', 95, true),
  ('Investimento Hospitalar', 'investimento-hospitalar', 'saude', 'positivo', '(hospital.*(novo|inaugur|invest|constru)|UPA|UBS.*(novo|inaug))', 'Investimento em infraestrutura hospitalar', 70, true),
  ('Política de Saúde', 'politica-saude', 'saude', 'sinal', '(SUS.*(reform|mud|ampl)|pol[íi]tica.*(sa[úu]de|vacinação)|Farmácia Popular)', 'Mudanças em políticas de saúde', 75, true)
ON CONFLICT (slug) DO NOTHING;

-- Educação
INSERT INTO dim_sinais_contextuais (nome, slug, categoria, tipo, keywords_regex, descricao, prioridade, ativo)
VALUES
  ('Financiamento Educacional', 'financiamento-educacional', 'educacao', 'sinal', '(FUNDEB|financiamento.*(educ|escola)|FIES|ProUni|bolsa.*estud)', 'Mudanças no financiamento educacional', 80, true),
  ('Reforma Educacional', 'reforma-educacional', 'educacao', 'sinal', '(reforma.*(educ|ensino|curr[íi]culo)|BNCC|novo ensino m[ée]dio)', 'Reformas no sistema educacional', 75, true),
  ('Avaliação Educacional', 'avaliacao-educacional', 'educacao', 'sinal', '(ENEM|IDEB|PISA|Saeb|avalia[çc][ãa]o.*(educ|escola|desempenho))', 'Resultados de avaliações educacionais', 70, true)
ON CONFLICT (slug) DO NOTHING;

-- Infraestrutura e Energia
INSERT INTO dim_sinais_contextuais (nome, slug, categoria, tipo, keywords_regex, descricao, prioridade, ativo)
VALUES
  ('Concessão/PPP', 'concessao-ppp', 'infraestrutura', 'sinal', '(concess[ãa]o|PPP|parceria p[úu]blico|leil[ãa]o.*infra|privatiza)', 'Concessão ou parceria público-privada', 75, true),
  ('Energia Renovável', 'energia-renovavel', 'energia', 'positivo', '(energia.*(renov[áa]vel|solar|e[óo]lica|limpa)|transi[çc][ãa]o energ)', 'Avanços em energia renovável', 70, true),
  ('Crise Energética', 'crise-energetica', 'energia', 'alerta', '(crise energ|apag[ãa]o|racionamento|bandeira vermelha|reservat[óo]rio.*(baix|cr[íi]tic))', 'Crise no setor energético', 90, true)
ON CONFLICT (slug) DO NOTHING;

-- Agricultura
INSERT INTO dim_sinais_contextuais (nome, slug, categoria, tipo, keywords_regex, descricao, prioridade, ativo)
VALUES
  ('Safra Recorde', 'safra-recorde', 'agricultura', 'positivo', '(safra.*(recorde|recor|recor)|produ[çc][ãa]o.*(recorde|recor)|colheita.*recor)', 'Safra recorde de grãos', 75, true),
  ('Exportação Agro', 'exportacao-agro', 'agricultura', 'sinal', '(exporta[çc][ãa]o.*(agro|soja|carne|milho|caf[ée])|balan[çc]a comercial.*agro)', 'Exportações do agronegócio', 70, true)
ON CONFLICT (slug) DO NOTHING;

-- Segurança Pública
INSERT INTO dim_sinais_contextuais (nome, slug, categoria, tipo, keywords_regex, descricao, prioridade, ativo)
VALUES
  ('Violência Urbana', 'violencia-urbana', 'seguranca_publica', 'alerta', '(homic[íi]dio.*(alta|cresc|recorde)|viol[êe]ncia.*(aument|explos)|chacina)', 'Aumento da violência urbana', 85, true),
  ('Política de Segurança', 'politica-seguranca', 'seguranca_publica', 'sinal', '(pol[íi]cia.*(reform|reestrutur)|pol[íi]tica.*(seguran|penal)|sistema prision)', 'Mudanças em políticas de segurança', 70, true)
ON CONFLICT (slug) DO NOTHING;
