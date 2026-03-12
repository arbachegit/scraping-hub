-- ============================================================
-- Migration 050: Auto-score credibility on news INSERT
-- Ensures new rows from the scraper get immediate scoring
-- ============================================================

CREATE OR REPLACE FUNCTION fn_auto_score_credibilidade()
RETURNS TRIGGER AS $$
BEGIN
  -- Skip if already scored
  IF NEW.credibilidade_score IS NOT NULL THEN
    RETURN NEW;
  END IF;

  -- 1. Try exact match from curated sources
  SELECT f.credibilidade_score INTO NEW.credibilidade_score
  FROM dim_fontes_noticias f
  WHERE LOWER(TRIM(BOTH FROM f.nome)) = LOWER(TRIM(BOTH FROM NEW.fonte_nome))
  LIMIT 1;

  IF NEW.credibilidade_score IS NOT NULL THEN
    RETURN NEW;
  END IF;

  -- 2. Pattern-based scoring
  -- Government / institutional (1.0)
  IF NEW.fonte_nome ILIKE ANY(ARRAY[
    '%www.gov.br%', '%Prefeitura%', '%Câmara Municipal%', '%Tribunal%',
    '%Ministério%', '%Senado%', '%Diário Oficial%', '%Agência Brasil%',
    '%IBGE%', '%IPEA%', '%BNDES%', '%Banco Central%', '%TCU%', '%TCE%',
    '%INEP%', '%FNDE%', '%DATASUS%', '%SUS%', '%Anvisa%', '%CVM%', '%STF%'
  ]) THEN
    NEW.credibilidade_score := 1.0;
    RETURN NEW;
  END IF;

  -- Premium journalism (0.9)
  IF NEW.fonte_nome ILIKE ANY(ARRAY[
    '%Folha%', '%Estadão%', '%Estado de S%', '%O Globo%',
    '%Valor Econômico%', '%Valor Investe%', '%InfoMoney%', '%Exame%',
    '%Brazil Journal%', '%JOTA%', '%Poder360%'
  ]) THEN
    NEW.credibilidade_score := 0.9;
    RETURN NEW;
  END IF;

  -- Professional journalism (0.8)
  IF NEW.fonte_nome ILIKE ANY(ARRAY[
    '%G1%', '%CNN%', '%UOL%', '%Reuters%', '%Bloomberg%', '%BBC%',
    '%Correio Braziliense%', '%Metrópoles%', '%R7%', '%Terra%',
    '%Gazeta%', '%Record%', '%Band%', '%SBT%', '%Jornal%', '%Agência%'
  ]) THEN
    NEW.credibilidade_score := 0.8;
    RETURN NEW;
  END IF;

  -- Regional/niche (0.6)
  IF NEW.fonte_nome ILIKE ANY(ARRAY[
    '%Notícias%', '%Portal%', '%Revista%', '%Blog%', '%Online%',
    '%News%', '%FM%', '%TV%', '%Rádio%'
  ]) THEN
    NEW.credibilidade_score := 0.6;
    RETURN NEW;
  END IF;

  -- Social media (0.4)
  IF NEW.fonte_nome ILIKE ANY(ARRAY[
    '%YouTube%', '%x.com%', '%twitter%', '%instagram%', '%facebook%', '%tiktok%'
  ]) THEN
    NEW.credibilidade_score := 0.4;
    RETURN NEW;
  END IF;

  -- Default: unknown (0.3)
  NEW.credibilidade_score := 0.3;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if any
DROP TRIGGER IF EXISTS trg_auto_score_credibilidade ON dim_noticias;

-- Create trigger on INSERT
CREATE TRIGGER trg_auto_score_credibilidade
  BEFORE INSERT ON dim_noticias
  FOR EACH ROW
  EXECUTE FUNCTION fn_auto_score_credibilidade();
