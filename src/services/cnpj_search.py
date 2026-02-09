"""
CNPJ Search Service
Busca de empresas por nome com validação na Receita Federal
"""

import asyncio
import re
from typing import Any, Dict, List

import structlog

from src.scrapers import BrasilAPIClient, SerperClient

logger = structlog.get_logger()


class CNPJSearchService:
    """
    Serviço de busca de CNPJ por nome de empresa.

    Fluxo:
    1. Busca no Google por "nome empresa CNPJ"
    2. Extrai CNPJs encontrados nos resultados
    3. Valida cada CNPJ na BrasilAPI (Receita Federal)
    4. Retorna lista de empresas para seleção do usuário
    """

    # Regex para extrair CNPJ (com ou sem formatação)
    CNPJ_PATTERN = re.compile(r"(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})")

    def __init__(self):
        self.serper = SerperClient()
        self.brasil_api = BrasilAPIClient()

    async def close(self):
        """Fecha os clientes"""
        await asyncio.gather(self.serper.close(), self.brasil_api.close())

    async def search_by_name(self, company_name: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Busca empresas por nome e retorna opções com dados da Receita.

        Args:
            company_name: Nome da empresa para buscar
            max_results: Número máximo de resultados

        Returns:
            Lista de empresas encontradas com dados da Receita
        """
        logger.info("cnpj_search_start", company_name=company_name)

        # 1. Buscar CNPJs via Google
        cnpjs_found = await self._search_cnpjs_google(company_name)

        if not cnpjs_found:
            logger.warning("cnpj_search_no_results", company_name=company_name)
            return {
                "query": company_name,
                "found": 0,
                "companies": [],
                "message": "Nenhum CNPJ encontrado. Tente refinar a busca.",
            }

        # 2. Validar cada CNPJ na Receita Federal
        companies = await self._validate_cnpjs(cnpjs_found[: max_results * 2])

        # 3. Filtrar por relevância (nome similar)
        relevant_companies = self._filter_by_relevance(companies, company_name, max_results)

        logger.info(
            "cnpj_search_complete", company_name=company_name, found=len(relevant_companies)
        )

        return {
            "query": company_name,
            "found": len(relevant_companies),
            "companies": relevant_companies,
            "message": self._get_result_message(len(relevant_companies)),
        }

    async def _search_cnpjs_google(self, company_name: str) -> List[str]:
        """Busca CNPJs no Google usando sites especializados"""

        # Queries otimizadas para encontrar CNPJ
        queries = [
            f'"{company_name}" CNPJ site:cnpj.info OR site:consultacnpj.com OR site:cnpja.com.br',
            f'"{company_name}" CNPJ Receita Federal',
            f"{company_name} empresa CNPJ Brasil",
        ]

        cnpjs = set()

        for query in queries:
            try:
                results = await self.serper.search(query, num=10)

                # Extrair CNPJs dos snippets e títulos
                for item in results.get("organic", []):
                    text = f"{item.get('title', '')} {item.get('snippet', '')}"
                    found = self.CNPJ_PATTERN.findall(text)

                    for cnpj in found:
                        # Normalizar CNPJ (apenas dígitos)
                        cnpj_clean = re.sub(r"\D", "", cnpj)
                        if len(cnpj_clean) == 14:
                            cnpjs.add(cnpj_clean)

                # Do knowledge graph também
                kg = results.get("knowledge_graph", {})
                if kg:
                    kg_text = str(kg)
                    found = self.CNPJ_PATTERN.findall(kg_text)
                    for cnpj in found:
                        cnpj_clean = re.sub(r"\D", "", cnpj)
                        if len(cnpj_clean) == 14:
                            cnpjs.add(cnpj_clean)

                # Se encontrou CNPJs, não precisa buscar mais
                if len(cnpjs) >= 5:
                    break

            except Exception as e:
                logger.warning("cnpj_google_search_error", query=query[:50], error=str(e))

        logger.info("cnpjs_extracted", count=len(cnpjs))
        return list(cnpjs)

    async def _validate_cnpjs(self, cnpjs: List[str]) -> List[Dict[str, Any]]:
        """Valida CNPJs na Receita Federal via BrasilAPI"""

        companies = []

        # Buscar em paralelo (máximo 5 por vez para não sobrecarregar)
        for i in range(0, len(cnpjs), 5):
            batch = cnpjs[i : i + 5]

            tasks = [self.brasil_api.get_cnpj(cnpj) for cnpj in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for cnpj, result in zip(batch, results, strict=False):
                if isinstance(result, Exception):
                    logger.warning("cnpj_validation_error", cnpj=cnpj[:8], error=str(result))
                    continue

                if result and result.get("cnpj"):
                    companies.append(result)

        return companies

    def _filter_by_relevance(
        self, companies: List[Dict], search_name: str, max_results: int
    ) -> List[Dict[str, Any]]:
        """Filtra e ordena empresas por relevância ao nome buscado"""

        search_name_lower = search_name.lower()
        search_words = set(search_name_lower.split())

        scored_companies = []

        for company in companies:
            # Calcular score de similaridade
            razao = (company.get("razao_social") or "").lower()
            fantasia = (company.get("nome_fantasia") or "").lower()

            # Score baseado em matching
            score = 0

            # Match exato no nome fantasia
            if search_name_lower in fantasia:
                score += 100

            # Match exato na razão social
            if search_name_lower in razao:
                score += 80

            # Match de palavras
            razao_words = set(razao.split())
            fantasia_words = set(fantasia.split())

            matching_words = search_words & (razao_words | fantasia_words)
            score += len(matching_words) * 20

            # Penalizar empresas inativas
            if company.get("situacao_cadastral") != "ATIVA":
                score -= 50

            scored_companies.append({**company, "_relevance_score": score})

        # Ordenar por relevância e retornar top N
        scored_companies.sort(key=lambda x: x["_relevance_score"], reverse=True)

        # Remover score interno antes de retornar
        result = []
        for company in scored_companies[:max_results]:
            company_data = {k: v for k, v in company.items() if not k.startswith("_")}
            result.append(self._format_company_for_display(company_data))

        return result

    def _format_company_for_display(self, company: Dict) -> Dict[str, Any]:
        """Formata dados da empresa para exibição ao usuário"""

        endereco = company.get("endereco", {})
        endereco_str = ""
        if endereco:
            parts = [
                endereco.get("logradouro", ""),
                endereco.get("numero", ""),
                endereco.get("bairro", ""),
                endereco.get("municipio", ""),
                endereco.get("uf", ""),
            ]
            endereco_str = ", ".join(p for p in parts if p)

        return {
            "cnpj": self._format_cnpj(company.get("cnpj", "")),
            "razao_social": company.get("razao_social"),
            "nome_fantasia": company.get("nome_fantasia"),
            "situacao": company.get("situacao_cadastral"),
            "porte": company.get("porte"),
            "data_abertura": company.get("data_abertura"),
            "endereco": endereco_str,
            "atividade_principal": company.get("cnae_principal", {}).get("descricao"),
            "capital_social": company.get("capital_social"),
            "socios": [s.get("nome") for s in company.get("socios", [])[:3]],
        }

    def _format_cnpj(self, cnpj: str) -> str:
        """Formata CNPJ para exibição: XX.XXX.XXX/XXXX-XX"""
        cnpj_clean = re.sub(r"\D", "", cnpj)
        if len(cnpj_clean) == 14:
            return f"{cnpj_clean[:2]}.{cnpj_clean[2:5]}.{cnpj_clean[5:8]}/{cnpj_clean[8:12]}-{cnpj_clean[12:]}"
        return cnpj

    def _get_result_message(self, count: int) -> str:
        """Retorna mensagem apropriada para o número de resultados"""
        if count == 0:
            return "Nenhuma empresa encontrada. Verifique o nome e tente novamente."
        elif count == 1:
            return "1 empresa encontrada. Confirme se os dados estão corretos."
        else:
            return f"{count} empresas encontradas. Selecione a correta."

    async def get_company_by_cnpj(self, cnpj: str) -> Dict[str, Any]:
        """
        Busca empresa diretamente pelo CNPJ.

        Args:
            cnpj: CNPJ da empresa

        Returns:
            Dados completos da empresa
        """
        result = await self.brasil_api.get_cnpj(cnpj)

        if not result:
            return {"error": True, "message": "CNPJ não encontrado na Receita Federal"}

        return {
            "error": False,
            "company": self._format_company_for_display(result),
            "raw_data": result,
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
