-- =============================================
-- FASE 2 - PASSO 2: SANITIZACAO E CONSTRAINTS
-- Data: 2026-03-05
-- RODAR SOMENTE APOS REVISAR RESULTADO DA AUDITORIA
-- =============================================

-- =============================================
-- BLOCO 1/4: Normalizar CNPJ (remover pontuacao)
-- =============================================

UPDATE dim_empresas
SET cnpj = regexp_replace(cnpj, '[^0-9]', '', 'g')
WHERE cnpj ~ '[^0-9]';

-- =============================================
-- BLOCO 2/4: Normalizar CPF (remover pontuacao)
-- Ignora CPFs mascarados (***XXX**) da Receita
-- =============================================

-- Limpar formatacao (pontos, tracos) dos CPFs validos
UPDATE dim_pessoas
SET cpf = regexp_replace(cpf, '[^0-9]', '', 'g')
WHERE cpf IS NOT NULL
  AND cpf ~ '[^0-9]'
  AND cpf NOT LIKE '%*%';

-- CPFs mascarados: setar como NULL (nao sao uteis para dedup)
UPDATE dim_pessoas
SET cpf = NULL
WHERE cpf IS NOT NULL
  AND cpf LIKE '%*%';

-- CPFs vazios: normalizar para NULL
UPDATE dim_pessoas
SET cpf = NULL
WHERE cpf = '';

-- =============================================
-- BLOCO 3/4: Deduplificar pessoas por CPF
-- Estrategia: manter o registro mais completo
-- (mais campos preenchidos), desempate por updated_at
-- =============================================

-- Passo 3a: Criar tabela temporaria com o "vencedor" de cada CPF
CREATE TEMP TABLE _cpf_winners AS
WITH ranked AS (
    SELECT
        id,
        cpf,
        -- Pontuar completude: +1 por campo preenchido
        (CASE WHEN nome_completo IS NOT NULL AND nome_completo != '' THEN 1 ELSE 0 END) +
        (CASE WHEN email IS NOT NULL AND email != '' THEN 1 ELSE 0 END) +
        (CASE WHEN linkedin_url IS NOT NULL AND linkedin_url != '' THEN 1 ELSE 0 END) +
        (CASE WHEN foto_url IS NOT NULL AND foto_url != '' THEN 1 ELSE 0 END) +
        (CASE WHEN raw_apollo_data IS NOT NULL AND raw_apollo_data::text != '{}' AND raw_apollo_data::text != 'null' THEN 2 ELSE 0 END) +
        (CASE WHEN raw_enrichment_extended IS NOT NULL AND raw_enrichment_extended::text != '{}' AND raw_enrichment_extended::text != 'null' THEN 2 ELSE 0 END)
        AS completude_score,
        ROW_NUMBER() OVER (
            PARTITION BY cpf
            ORDER BY
                -- Mais completo primeiro
                (CASE WHEN nome_completo IS NOT NULL AND nome_completo != '' THEN 1 ELSE 0 END) +
                (CASE WHEN email IS NOT NULL AND email != '' THEN 1 ELSE 0 END) +
                (CASE WHEN linkedin_url IS NOT NULL AND linkedin_url != '' THEN 1 ELSE 0 END) +
                (CASE WHEN foto_url IS NOT NULL AND foto_url != '' THEN 1 ELSE 0 END) +
                (CASE WHEN raw_apollo_data IS NOT NULL AND raw_apollo_data::text != '{}' AND raw_apollo_data::text != 'null' THEN 2 ELSE 0 END) +
                (CASE WHEN raw_enrichment_extended IS NOT NULL AND raw_enrichment_extended::text != '{}' AND raw_enrichment_extended::text != 'null' THEN 2 ELSE 0 END)
                DESC,
                -- Desempate: mais recente
                COALESCE(updated_at, created_at) DESC
        ) AS rn
    FROM dim_pessoas
    WHERE cpf IS NOT NULL
      AND cpf != ''
)
SELECT id AS winner_id, cpf
FROM ranked
WHERE rn = 1;

-- Passo 3b: Redirecionar FKs dos "perdedores" para o "vencedor"
UPDATE fato_transacao_empresas t
SET pessoa_id = w.winner_id
FROM dim_pessoas p
JOIN _cpf_winners w ON p.cpf = w.cpf AND p.id != w.winner_id
WHERE t.pessoa_id = p.id
  AND NOT EXISTS (
      -- Evitar violacao de UNIQUE (pessoa_id, empresa_id, tipo_transacao, data_transacao)
      SELECT 1 FROM fato_transacao_empresas existing
      WHERE existing.pessoa_id = w.winner_id
        AND existing.empresa_id = t.empresa_id
        AND existing.tipo_transacao = t.tipo_transacao
  );

-- Passo 3c: Redirecionar FKs em fato_noticias_pessoas
UPDATE fato_noticias_pessoas np
SET pessoa_id = w.winner_id
FROM dim_pessoas p
JOIN _cpf_winners w ON p.cpf = w.cpf AND p.id != w.winner_id
WHERE np.pessoa_id = p.id
  AND NOT EXISTS (
      SELECT 1 FROM fato_noticias_pessoas existing
      WHERE existing.pessoa_id = w.winner_id
        AND existing.noticia_id = np.noticia_id
  );

-- Passo 3d: Deletar transacoes duplicadas que nao puderam ser redirecionadas
DELETE FROM fato_transacao_empresas t
USING dim_pessoas p
JOIN _cpf_winners w ON p.cpf = w.cpf AND p.id != w.winner_id
WHERE t.pessoa_id = p.id;

-- Passo 3e: Deletar noticias-pessoas duplicadas que nao puderam ser redirecionadas
DELETE FROM fato_noticias_pessoas np
USING dim_pessoas p
JOIN _cpf_winners w ON p.cpf = w.cpf AND p.id != w.winner_id
WHERE np.pessoa_id = p.id;

-- Passo 3f: Deletar registros "perdedores" de dim_pessoas
DELETE FROM dim_pessoas p
USING _cpf_winners w
WHERE p.cpf = w.cpf
  AND p.id != w.winner_id
  AND p.cpf IS NOT NULL
  AND p.cpf != '';

-- Limpar temp
DROP TABLE IF EXISTS _cpf_winners;

-- =============================================
-- BLOCO 4/4: Adicionar CONSTRAINTS
-- =============================================

-- 4a. UNIQUE no CPF (somente nao-nulos)
-- Permite multiplos NULLs (pessoas sem CPF)
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_pessoas_cpf_unique
    ON dim_pessoas(cpf) WHERE cpf IS NOT NULL;

-- 4b. CHECK constraint nas fontes de dim_pessoas
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_pessoas_fonte'
    ) THEN
        -- Primeiro, verificar se existem valores fora do enum
        IF NOT EXISTS (
            SELECT 1 FROM dim_pessoas
            WHERE fonte IS NOT NULL
              AND fonte NOT IN ('brasilapi+serper+apollo','perplexity','batch_insert','manual','apollo','brasilapi')
        ) THEN
            ALTER TABLE dim_pessoas ADD CONSTRAINT chk_pessoas_fonte
                CHECK (fonte IS NULL OR fonte IN ('brasilapi+serper+apollo','perplexity','batch_insert','manual','apollo','brasilapi'));
        ELSE
            RAISE NOTICE 'ATENCAO: Existem valores de fonte em dim_pessoas fora do enum esperado. Constraint NAO adicionada.';
        END IF;
    END IF;
END $$;

-- 4c. CHECK constraint nas fontes de dim_empresas
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_empresas_fonte'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM dim_empresas
            WHERE fonte IS NOT NULL
              AND fonte NOT IN ('brasilapi+serper+apollo','perplexity','batch_insert','manual','brasilapi','serper')
        ) THEN
            ALTER TABLE dim_empresas ADD CONSTRAINT chk_empresas_fonte
                CHECK (fonte IS NULL OR fonte IN ('brasilapi+serper+apollo','perplexity','batch_insert','manual','brasilapi','serper'));
        ELSE
            RAISE NOTICE 'ATENCAO: Existem valores de fonte em dim_empresas fora do enum esperado. Constraint NAO adicionada.';
        END IF;
    END IF;
END $$;

-- 4d. CHECK constraint no regime_tributario
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_regime_tipo'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM fato_regime_tributario
            WHERE regime_tributario IS NOT NULL
              AND regime_tributario NOT IN ('MEI','SIMPLES_NACIONAL','SIMPLES_ME','SIMPLES_EPP','LUCRO_PRESUMIDO','LUCRO_REAL','DESCONHECIDO')
        ) THEN
            ALTER TABLE fato_regime_tributario ADD CONSTRAINT chk_regime_tipo
                CHECK (regime_tributario IS NULL OR regime_tributario IN ('MEI','SIMPLES_NACIONAL','SIMPLES_ME','SIMPLES_EPP','LUCRO_PRESUMIDO','LUCRO_REAL','DESCONHECIDO'));
        ELSE
            RAISE NOTICE 'ATENCAO: Existem valores de regime_tributario fora do enum esperado. Constraint NAO adicionada.';
        END IF;
    END IF;
END $$;

-- =============================================
-- VERIFICACAO FINAL
-- =============================================

SELECT 'FASE 2 COMPLETA' AS status,
    (SELECT COUNT(*) FROM dim_pessoas WHERE cpf ~ '[^0-9]') AS cpfs_com_pontuacao,
    (SELECT COUNT(*) FROM dim_empresas WHERE cnpj ~ '[^0-9]') AS cnpjs_com_pontuacao,
    (SELECT COUNT(*) FROM (
        SELECT cpf FROM dim_pessoas WHERE cpf IS NOT NULL GROUP BY cpf HAVING COUNT(*) > 1
    ) d) AS cpfs_duplicados,
    EXISTS(SELECT 1 FROM pg_indexes WHERE indexname = 'idx_dim_pessoas_cpf_unique') AS unique_cpf_ok,
    EXISTS(SELECT 1 FROM pg_constraint WHERE conname = 'chk_pessoas_fonte') AS check_fonte_pessoas_ok,
    EXISTS(SELECT 1 FROM pg_constraint WHERE conname = 'chk_empresas_fonte') AS check_fonte_empresas_ok,
    EXISTS(SELECT 1 FROM pg_constraint WHERE conname = 'chk_regime_tipo') AS check_regime_ok;
