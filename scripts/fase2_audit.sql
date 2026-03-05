-- =============================================
-- FASE 2 - PASSO 1: AUDITORIA (SOMENTE LEITURA)
-- Data: 2026-03-05
-- Rodar ANTES da correcao para entender o estado dos dados
-- =============================================

-- 1. CNPJ com formatacao inconsistente
SELECT 'CNPJs com pontuacao' AS check_name,
       COUNT(*) AS total
FROM dim_empresas
WHERE cnpj ~ '[^0-9]';

-- 2. CPFs com formatacao inconsistente
SELECT 'CPFs com pontuacao' AS check_name,
       COUNT(*) AS total
FROM dim_pessoas
WHERE cpf IS NOT NULL AND cpf ~ '[^0-9]';

-- 3. CPFs mascarados (da Receita Federal)
SELECT 'CPFs mascarados (***XXX**)' AS check_name,
       COUNT(*) AS total
FROM dim_pessoas
WHERE cpf IS NOT NULL AND cpf LIKE '%*%';

-- 4. Pessoas duplicadas por CPF
SELECT 'Pessoas com CPF duplicado' AS check_name,
       COUNT(*) AS total
FROM (
    SELECT cpf, COUNT(*) AS qtd
    FROM dim_pessoas
    WHERE cpf IS NOT NULL
      AND cpf != ''
      AND cpf NOT LIKE '%*%'
    GROUP BY cpf
    HAVING COUNT(*) > 1
) dupes;

-- 5. Detalhes das duplicatas (top 20)
SELECT cpf,
       COUNT(*) AS qtd_registros,
       array_agg(id ORDER BY updated_at DESC NULLS LAST) AS ids,
       array_agg(nome_completo) AS nomes,
       array_agg(fonte) AS fontes
FROM dim_pessoas
WHERE cpf IS NOT NULL
  AND cpf != ''
  AND cpf NOT LIKE '%*%'
GROUP BY cpf
HAVING COUNT(*) > 1
ORDER BY COUNT(*) DESC
LIMIT 20;

-- 6. Valores distintos do campo 'fonte' em dim_pessoas
SELECT fonte, COUNT(*) AS total
FROM dim_pessoas
GROUP BY fonte
ORDER BY total DESC;

-- 7. Valores distintos do campo 'fonte' em dim_empresas
SELECT fonte, COUNT(*) AS total
FROM dim_empresas
GROUP BY fonte
ORDER BY total DESC;

-- 8. Valores distintos de regime_tributario em fato_regime_tributario
SELECT regime_tributario, COUNT(*) AS total
FROM fato_regime_tributario
GROUP BY regime_tributario
ORDER BY total DESC;

-- 9. Empresas duplicadas por CNPJ
SELECT 'Empresas com CNPJ duplicado' AS check_name,
       COUNT(*) AS total
FROM (
    SELECT cnpj, COUNT(*) AS qtd
    FROM dim_empresas
    WHERE cnpj IS NOT NULL AND cnpj != ''
    GROUP BY cnpj
    HAVING COUNT(*) > 1
) dupes;

-- 10. FKs orfas em fato_transacao_empresas
SELECT 'Transacoes com pessoa_id inexistente' AS check_name,
       COUNT(*) AS total
FROM fato_transacao_empresas t
LEFT JOIN dim_pessoas p ON t.pessoa_id = p.id
WHERE p.id IS NULL;

-- 11. FKs orfas em fato_transacao_empresas (empresa)
SELECT 'Transacoes com empresa_id inexistente' AS check_name,
       COUNT(*) AS total
FROM fato_transacao_empresas t
LEFT JOIN dim_empresas e ON t.empresa_id = e.id
WHERE e.id IS NULL;

-- 12. Resumo geral
SELECT
    (SELECT COUNT(*) FROM dim_empresas) AS total_empresas,
    (SELECT COUNT(*) FROM dim_pessoas) AS total_pessoas,
    (SELECT COUNT(*) FROM fato_transacao_empresas) AS total_transacoes,
    (SELECT COUNT(*) FROM fato_regime_tributario) AS total_regimes,
    (SELECT COUNT(*) FROM dim_pessoas WHERE cpf IS NOT NULL AND cpf != '') AS pessoas_com_cpf,
    (SELECT COUNT(*) FROM dim_pessoas WHERE cpf IS NULL OR cpf = '') AS pessoas_sem_cpf;
