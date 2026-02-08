"""
Star Schema Repository - Persistencia de dados dimensionais
Empresas, Pessoas, Analises, Concorrentes
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from .client import get_supabase

logger = structlog.get_logger()


class EmpresaRepository:
    """
    Repository para dim_empresas
    """

    TABLE_NAME = "dim_empresas"

    def __init__(self):
        self.client = get_supabase()

    def _is_available(self) -> bool:
        return self.client is not None

    async def upsert(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Insere ou atualiza empresa
        Retorna o ID da empresa
        """
        if not self._is_available():
            logger.warning("db_not_available", operation="upsert_empresa")
            return None

        try:
            # Usar nome_fantasia como razao_social se não tiver
            nome_fantasia = data.get("nome_fantasia") or data.get("name")
            razao_social = data.get("razao_social") or nome_fantasia

            record = {
                "cnpj": self._clean_cnpj(data.get("cnpj")),
                "cnae_principal": data.get("cnae_principal") or data.get("cnae"),
                "cnae_descricao": data.get("cnae_descricao"),
                "razao_social": razao_social,
                "nome_fantasia": nome_fantasia,
                "logradouro": data.get("logradouro"),
                "numero": data.get("numero"),
                "complemento": data.get("complemento"),
                "bairro": data.get("bairro"),
                "cidade": data.get("cidade") or data.get("municipio"),
                "estado": data.get("estado") or data.get("uf"),
                "cep": data.get("cep"),
                "fundadores": json.dumps(data.get("fundadores", []), ensure_ascii=False),
                "website": data.get("website"),
                "linkedin_url": data.get("linkedin_url"),
                "telefone": data.get("telefone") or data.get("ddd_telefone_1"),
                "email": data.get("email"),
                "porte": data.get("porte"),
                "natureza_juridica": data.get("natureza_juridica"),
                "situacao_cadastral": data.get("situacao_cadastral") or data.get("descricao_situacao_cadastral"),
                "data_abertura": data.get("data_inicio_atividade") or data.get("data_abertura"),
                "capital_social": data.get("capital_social"),
                "setor": data.get("setor") or data.get("industry"),
                "qtd_funcionarios": data.get("qtd_funcionarios") or data.get("employee_count"),
                "palavras_chave": json.dumps(data.get("palavras_chave", []), ensure_ascii=False),
                "raw_cnpj_data": json.dumps(data.get("raw_cnpj_data", {}), default=str, ensure_ascii=False),
                "raw_search_data": json.dumps(data.get("raw_search_data", {}), default=str, ensure_ascii=False),
                "updated_at": datetime.utcnow().isoformat()
            }

            # Remover campos None
            record = {k: v for k, v in record.items() if v is not None}

            # Upsert por CNPJ se disponivel
            if record.get("cnpj"):
                result = self.client.table(self.TABLE_NAME).upsert(
                    record,
                    on_conflict="cnpj"
                ).execute()
            else:
                # Buscar por nome se nao tem CNPJ
                existing = self.client.table(self.TABLE_NAME).select("id").eq(
                    "nome_fantasia", record.get("nome_fantasia")
                ).execute()

                if existing.data:
                    record["id"] = existing.data[0]["id"]

                result = self.client.table(self.TABLE_NAME).upsert(record).execute()

            if result.data:
                empresa_id = result.data[0].get("id")
                logger.info("empresa_saved", id=empresa_id, nome=record.get("nome_fantasia"))
                return empresa_id

        except Exception as e:
            logger.error("empresa_save_error", error=str(e), data=data.get("nome_fantasia"))

        return None

    async def get_by_cnpj(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """Busca empresa por CNPJ"""
        if not self._is_available():
            return None

        try:
            cnpj_clean = self._clean_cnpj(cnpj)
            result = self.client.table(self.TABLE_NAME).select("*").eq("cnpj", cnpj_clean).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("empresa_get_error", error=str(e))
            return None

    async def get_by_nome(self, nome: str) -> Optional[Dict[str, Any]]:
        """Busca empresa por nome"""
        if not self._is_available():
            return None

        try:
            result = self.client.table(self.TABLE_NAME).select("*").ilike(
                "nome_fantasia", f"%{nome}%"
            ).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("empresa_get_error", error=str(e))
            return None

    async def get_by_id(self, empresa_id: str) -> Optional[Dict[str, Any]]:
        """Busca empresa por ID"""
        if not self._is_available():
            return None

        try:
            result = self.client.table(self.TABLE_NAME).select("*").eq("id", empresa_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("empresa_get_error", error=str(e))
            return None

    def _clean_cnpj(self, cnpj: Optional[str]) -> Optional[str]:
        """Remove formatacao do CNPJ"""
        if not cnpj:
            return None
        return "".join(c for c in cnpj if c.isdigit())

    async def update_keywords(self, empresa_id: str, keywords: List[str]) -> bool:
        """Atualiza palavras-chave da empresa"""
        if not self._is_available():
            return False

        try:
            result = self.client.table(self.TABLE_NAME).update({
                "palavras_chave": json.dumps(keywords, ensure_ascii=False),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", empresa_id).execute()

            return bool(result.data)
        except Exception as e:
            logger.error("empresa_keywords_update_error", error=str(e))
            return False


class PessoaRepository:
    """
    Repository para dim_pessoas
    """

    TABLE_NAME = "dim_pessoas"

    def __init__(self):
        self.client = get_supabase()

    def _is_available(self) -> bool:
        return self.client is not None

    async def upsert(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Insere ou atualiza pessoa
        Retorna o ID da pessoa
        """
        if not self._is_available():
            logger.warning("db_not_available", operation="upsert_pessoa")
            return None

        try:
            nome_completo = data.get("name") or data.get("nome_completo") or ""
            partes_nome = nome_completo.split(" ", 1)

            record = {
                "nome_completo": nome_completo,
                "primeiro_nome": partes_nome[0] if partes_nome else None,
                "sobrenome": partes_nome[1] if len(partes_nome) > 1 else None,
                "email": data.get("email"),
                "telefone": data.get("phone") or data.get("telefone"),
                "linkedin_url": data.get("linkedin_url"),
                "linkedin_id": data.get("linkedin_id") or data.get("id"),
                "foto_url": data.get("photo_url") or data.get("foto_url"),
                "cidade": data.get("city") or data.get("cidade"),
                "estado": data.get("state") or data.get("estado"),
                "cargo_atual": data.get("title") or data.get("cargo_atual"),
                "empresa_atual_id": data.get("empresa_atual_id"),
                "empresa_atual_nome": data.get("organization_name") or data.get("empresa_atual_nome"),
                "senioridade": data.get("seniority") or data.get("senioridade"),
                "departamento": data.get("departments") or data.get("departamento"),
                "headline": data.get("headline"),
                "skills": json.dumps(data.get("skills", []), ensure_ascii=False),
                "fonte": data.get("fonte", "apollo"),  # apollo, perplexity, google
                "raw_apollo_data": json.dumps(data.get("raw_apollo_data", data), default=str, ensure_ascii=False),
                "updated_at": datetime.utcnow().isoformat()
            }

            # Remover campos None
            record = {k: v for k, v in record.items() if v is not None}

            # Upsert por linkedin_url se disponivel
            if record.get("linkedin_url"):
                result = self.client.table(self.TABLE_NAME).upsert(
                    record,
                    on_conflict="linkedin_url"
                ).execute()
            else:
                # Buscar por nome + empresa
                query = self.client.table(self.TABLE_NAME).select("id").eq(
                    "nome_completo", record.get("nome_completo")
                )
                if record.get("empresa_atual_nome"):
                    query = query.eq("empresa_atual_nome", record.get("empresa_atual_nome"))

                existing = query.execute()

                if existing.data:
                    record["id"] = existing.data[0]["id"]

                result = self.client.table(self.TABLE_NAME).upsert(record).execute()

            if result.data:
                pessoa_id = result.data[0].get("id")
                logger.info("pessoa_saved", id=pessoa_id, nome=record.get("nome_completo"))
                return pessoa_id

        except Exception as e:
            logger.error("pessoa_save_error", error=str(e), data=data.get("name"))

        return None

    async def get_by_empresa(self, empresa_id: str) -> List[Dict[str, Any]]:
        """Lista pessoas de uma empresa"""
        if not self._is_available():
            return []

        try:
            result = self.client.table(self.TABLE_NAME).select("*").eq(
                "empresa_atual_id", empresa_id
            ).execute()
            return result.data or []
        except Exception as e:
            logger.error("pessoa_list_error", error=str(e))
            return []


class AnaliseEmpresaRepository:
    """
    Repository para fato_analises_empresa
    """

    TABLE_NAME = "fato_analises_empresa"

    def __init__(self):
        self.client = get_supabase()

    def _is_available(self) -> bool:
        return self.client is not None

    async def save(self, empresa_id: str, analise: Dict[str, Any]) -> Optional[str]:
        """
        Salva analise de empresa
        Retorna ID da analise
        """
        if not self._is_available():
            logger.warning("db_not_available", operation="save_analise")
            return None

        try:
            blocks = analise.get("blocks", {})
            synthesis = analise.get("synthesis", {})
            swot = synthesis.get("swot", {})

            record = {
                "empresa_id": empresa_id,
                "tipo_analise": analise.get("tipo_analise", "completa"),
                "versao_modelo": analise.get("metadata", {}).get("model"),
                "tempo_processamento_segundos": analise.get("metadata", {}).get("processing_time_seconds"),

                # 11 Blocos
                "bloco_1_empresa": blocks.get("1_empresa", {}).get("content"),
                "bloco_2_pessoas": blocks.get("2_pessoas", {}).get("content"),
                "bloco_3_formacao": blocks.get("3_formacao", {}).get("content"),
                "bloco_4_ativo_humano": blocks.get("4_ativo_humano", {}).get("content"),
                "bloco_5_capacidade": blocks.get("5_capacidade", {}).get("content"),
                "bloco_6_comunicacao": blocks.get("6_comunicacao", {}).get("content"),
                "bloco_7_fraquezas": blocks.get("7_fraquezas", {}).get("content"),
                "bloco_8_visao_leigo": blocks.get("8_visao_leigo", {}).get("content"),
                "bloco_9_visao_profissional": blocks.get("9_visao_profissional", {}).get("content"),
                "bloco_10_visao_concorrente": blocks.get("10_visao_concorrente", {}).get("content"),
                "bloco_11_visao_fornecedor": blocks.get("11_visao_fornecedor", {}).get("content"),

                # Sintese
                "hipotese_objetivo": json.dumps(synthesis.get("hypothesis_objective", {}), ensure_ascii=False),
                "okrs_sugeridos": json.dumps(synthesis.get("suggested_okr", {}), ensure_ascii=False),

                # SWOT
                "swot_forcas": json.dumps(swot.get("strengths", []), ensure_ascii=False),
                "swot_fraquezas": json.dumps(swot.get("weaknesses", []), ensure_ascii=False),
                "swot_oportunidades": json.dumps(swot.get("opportunities", []), ensure_ascii=False),
                "swot_ameacas": json.dumps(swot.get("threats", []), ensure_ascii=False),
                "tows_estrategias": json.dumps(swot.get("tows_strategies", {}), ensure_ascii=False),

                # Palavras-chave
                "palavras_chave": json.dumps(analise.get("palavras_chave", []), ensure_ascii=False),
                "palavras_chave_por_bloco": json.dumps(analise.get("palavras_chave_por_bloco", {}), ensure_ascii=False),

                # Qualidade
                "score_qualidade": analise.get("metadata", {}).get("data_quality_score"),
                "fontes_utilizadas": json.dumps(analise.get("metadata", {}).get("sources_used", []), ensure_ascii=False),

                # Raw data
                "raw_perplexity": json.dumps(analise.get("raw_data", {}).get("perplexity_research", {}), default=str, ensure_ascii=False),
                "raw_tavily": json.dumps(analise.get("raw_data", {}).get("tavily_research", {}), default=str, ensure_ascii=False),
            }

            # Remover campos None
            record = {k: v for k, v in record.items() if v is not None}

            result = self.client.table(self.TABLE_NAME).insert(record).execute()

            if result.data:
                analise_id = result.data[0].get("id")
                logger.info("analise_saved", id=analise_id, empresa_id=empresa_id)
                return analise_id

        except Exception as e:
            logger.error("analise_save_error", error=str(e), empresa_id=empresa_id)

        return None

    async def get_ultima_analise(self, empresa_id: str) -> Optional[Dict[str, Any]]:
        """Busca ultima analise de uma empresa"""
        if not self._is_available():
            return None

        try:
            result = self.client.table(self.TABLE_NAME).select("*").eq(
                "empresa_id", empresa_id
            ).order("data_analise", desc=True).limit(1).execute()

            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("analise_get_error", error=str(e))
            return None


class EventoPessoaRepository:
    """
    Repository para fato_eventos_pessoa (portfolio)
    """

    TABLE_NAME = "fato_eventos_pessoa"

    def __init__(self):
        self.client = get_supabase()

    def _is_available(self) -> bool:
        return self.client is not None

    async def save_emprego(self, pessoa_id: str, emprego: Dict[str, Any], empresa_id: Optional[str] = None) -> Optional[str]:
        """Salva evento de emprego"""
        return await self._save_evento(
            pessoa_id=pessoa_id,
            tipo_evento="emprego",
            titulo=emprego.get("title"),
            instituicao=emprego.get("organization_name") or emprego.get("company"),
            data_inicio=emprego.get("start_date"),
            data_fim=emprego.get("end_date"),
            atual=emprego.get("is_current", False),
            descricao=emprego.get("description"),
            empresa_id=empresa_id,
            raw_data=emprego
        )

    async def save_educacao(self, pessoa_id: str, educacao: Dict[str, Any]) -> Optional[str]:
        """Salva evento de educacao"""
        return await self._save_evento(
            pessoa_id=pessoa_id,
            tipo_evento="educacao",
            titulo=educacao.get("degree") or educacao.get("grau"),
            instituicao=educacao.get("school_name") or educacao.get("instituicao"),
            data_inicio=educacao.get("start_date"),
            data_fim=educacao.get("end_date"),
            area_estudo=educacao.get("field_of_study") or educacao.get("area"),
            grau=educacao.get("degree_type"),
            raw_data=educacao
        )

    async def save_certificacao(self, pessoa_id: str, cert: Dict[str, Any]) -> Optional[str]:
        """Salva certificacao"""
        return await self._save_evento(
            pessoa_id=pessoa_id,
            tipo_evento="certificacao",
            titulo=cert.get("name") or cert.get("titulo"),
            instituicao=cert.get("issuing_organization") or cert.get("emissor"),
            data_inicio=cert.get("issue_date"),
            validade=cert.get("expiration_date"),
            credencial_id=cert.get("credential_id"),
            url_credencial=cert.get("credential_url"),
            raw_data=cert
        )

    async def _save_evento(
        self,
        pessoa_id: str,
        tipo_evento: str,
        titulo: Optional[str] = None,
        instituicao: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        atual: bool = False,
        descricao: Optional[str] = None,
        empresa_id: Optional[str] = None,
        grau: Optional[str] = None,
        area_estudo: Optional[str] = None,
        credencial_id: Optional[str] = None,
        url_credencial: Optional[str] = None,
        validade: Optional[str] = None,
        raw_data: Optional[Dict] = None
    ) -> Optional[str]:
        """Salva evento generico"""
        if not self._is_available():
            return None

        try:
            record = {
                "pessoa_id": pessoa_id,
                "empresa_id": empresa_id,
                "tipo_evento": tipo_evento,
                "titulo": titulo,
                "instituicao": instituicao,
                "data_inicio": self._parse_date(data_inicio),
                "data_fim": self._parse_date(data_fim),
                "atual": atual,
                "descricao": descricao,
                "grau": grau,
                "area_estudo": area_estudo,
                "credencial_id": credencial_id,
                "url_credencial": url_credencial,
                "validade": self._parse_date(validade),
                "raw_data": json.dumps(raw_data or {}, default=str, ensure_ascii=False)
            }

            # Remover campos None
            record = {k: v for k, v in record.items() if v is not None}

            result = self.client.table(self.TABLE_NAME).insert(record).execute()

            if result.data:
                return result.data[0].get("id")

        except Exception as e:
            logger.error("evento_save_error", error=str(e), tipo=tipo_evento)

        return None

    async def get_portfolio(self, pessoa_id: str) -> Dict[str, List[Dict]]:
        """Busca portfolio completo de uma pessoa"""
        if not self._is_available():
            return {"empregos": [], "educacao": [], "certificacoes": []}

        try:
            result = self.client.table(self.TABLE_NAME).select("*").eq(
                "pessoa_id", pessoa_id
            ).order("data_inicio", desc=True).execute()

            portfolio: Dict[str, List[Dict]] = {
                "empregos": [],
                "educacao": [],
                "certificacoes": [],
                "outros": []
            }

            for evento in result.data or []:
                tipo = evento.get("tipo_evento", "outros")
                if tipo == "emprego":
                    portfolio["empregos"].append(evento)
                elif tipo == "educacao":
                    portfolio["educacao"].append(evento)
                elif tipo == "certificacao":
                    portfolio["certificacoes"].append(evento)
                else:
                    portfolio["outros"].append(evento)

            return portfolio

        except Exception as e:
            logger.error("portfolio_get_error", error=str(e))
            return {"empregos": [], "educacao": [], "certificacoes": []}

    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse date string para formato ISO"""
        if not date_str:
            return None
        # Tentar varios formatos
        for fmt in ["%Y-%m-%d", "%Y-%m", "%Y", "%d/%m/%Y", "%m/%Y"]:
            try:
                from datetime import datetime
                dt = datetime.strptime(str(date_str), fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None


class ConcorrenteRepository:
    """
    Repository para fato_concorrentes
    """

    TABLE_NAME = "fato_concorrentes"

    def __init__(self):
        self.client = get_supabase()

    def _is_available(self) -> bool:
        return self.client is not None

    async def save(
        self,
        empresa_id: str,
        concorrente_id: str,
        palavras_chave_match: List[str],
        score_similaridade: float,
        stamp: str,
        stamp_justificativa: str,
        tipo_concorrencia: str = "direto",
        fonte_descoberta: str = "perplexity",
        query_utilizada: Optional[str] = None
    ) -> Optional[str]:
        """Salva relacao de concorrencia"""
        if not self._is_available():
            return None

        try:
            record = {
                "empresa_id": empresa_id,
                "concorrente_id": concorrente_id,
                "tipo_concorrencia": tipo_concorrencia,
                "palavras_chave_match": json.dumps(palavras_chave_match, ensure_ascii=False),
                "score_similaridade": score_similaridade,
                "stamp": stamp,
                "stamp_justificativa": stamp_justificativa,
                "fonte_descoberta": fonte_descoberta,
                "query_utilizada": query_utilizada,
                "updated_at": datetime.utcnow().isoformat()
            }

            result = self.client.table(self.TABLE_NAME).upsert(
                record,
                on_conflict="empresa_id,concorrente_id"
            ).execute()

            if result.data:
                logger.info("concorrente_saved", empresa_id=empresa_id, concorrente_id=concorrente_id)
                return result.data[0].get("id")

        except Exception as e:
            logger.error("concorrente_save_error", error=str(e))

        return None

    async def get_concorrentes(self, empresa_id: str) -> List[Dict[str, Any]]:
        """Lista concorrentes de uma empresa"""
        if not self._is_available():
            return []

        try:
            result = self.client.table(self.TABLE_NAME).select(
                "*, concorrente:concorrente_id(id, nome_fantasia, cnpj, setor, website)"
            ).eq("empresa_id", empresa_id).execute()

            return result.data or []
        except Exception as e:
            logger.error("concorrentes_get_error", error=str(e))
            return []


class BuscaRepository:
    """
    Repository para fato_buscas (historico)
    """

    TABLE_NAME = "fato_buscas"

    def __init__(self):
        self.client = get_supabase()

    def _is_available(self) -> bool:
        return self.client is not None

    async def registrar(
        self,
        user_email: str,
        tipo_busca: str,
        termo_busca: str,
        empresa_id: Optional[str] = None,
        pessoa_id: Optional[str] = None,
        tempo_processamento_ms: Optional[int] = None,
        apis_chamadas: Optional[List[str]] = None,
        status: str = "completed",
        erro: Optional[str] = None
    ) -> Optional[str]:
        """Registra busca no historico"""
        if not self._is_available():
            return None

        try:
            record = {
                "user_email": user_email,
                "tipo_busca": tipo_busca,
                "termo_busca": termo_busca,
                "empresa_id": empresa_id,
                "pessoa_id": pessoa_id,
                "tempo_processamento_ms": tempo_processamento_ms,
                "apis_chamadas": json.dumps(apis_chamadas or [], ensure_ascii=False),
                "status": status,
                "erro": erro
            }

            result = self.client.table(self.TABLE_NAME).insert(record).execute()

            if result.data:
                return result.data[0].get("id")

        except Exception as e:
            logger.error("busca_save_error", error=str(e))

        return None
