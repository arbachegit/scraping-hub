"""
Repository para rastreamento de fontes de dados.

Conforme CLAUDE.md: ALWAYS registrar fontes de dados em TODOS os projetos.

Este módulo garante rastreabilidade de todas as fontes de dados
utilizadas pelo sistema, permitindo auditoria e compliance.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from .client import get_supabase

logger = structlog.get_logger()


class FontesDadosRepository:
    """
    Repository para tabela fontes_dados.

    Responsável por:
    - Registrar uso de fontes de dados
    - Atualizar timestamps de última coleta
    - Consultar fontes por categoria
    - Gerar relatórios de rastreabilidade
    """

    TABLE_NAME = "fontes_dados"

    def __init__(self):
        self.client = get_supabase()

    def _is_available(self) -> bool:
        """Verifica se banco de dados está disponível."""
        return self.client is not None

    async def registrar_uso(
        self,
        nome: str,
        categoria: str,
        fonte_primaria: str,
        url: str,
        formato: str = "JSON",
        confiabilidade: str = "alta",
        cobertura: Optional[str] = None
    ) -> bool:
        """
        Registra uso de uma fonte de dados.

        Se a fonte já existir, atualiza data_ultima_atualizacao.
        Se não existir, cria novo registro.

        Args:
            nome: Nome identificador da fonte (ex: "BrasilAPI - CNPJ")
            categoria: Categoria da fonte ('api', 'scraping', 'manual')
            fonte_primaria: Provedor da fonte (ex: "BrasilAPI")
            url: URL da API/fonte
            formato: Formato dos dados ('JSON', 'HTML', 'XML')
            confiabilidade: Nível de confiança ('alta', 'media', 'baixa')
            cobertura: Descrição do que a fonte cobre

        Returns:
            True se registrado com sucesso, False caso contrário
        """
        if not self._is_available():
            logger.warning("db_not_available_fontes_registrar")
            return False

        try:
            record = {
                "nome": nome,
                "categoria": categoria,
                "fonte_primaria": fonte_primaria,
                "url": url,
                "formato": formato,
                "confiabilidade": confiabilidade,
                "data_ultima_atualizacao": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            if cobertura:
                record["cobertura"] = cobertura

            self.client.table(self.TABLE_NAME).upsert(
                record,
                on_conflict="nome,categoria"
            ).execute()

            logger.info(
                "fonte_uso_registrado",
                nome=nome,
                categoria=categoria,
                fonte=fonte_primaria
            )
            return True

        except Exception as e:
            logger.error(
                "fonte_registro_erro",
                nome=nome,
                error=str(e)
            )
            return False

    async def obter_fonte(
        self,
        nome: str,
        categoria: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtém informações de uma fonte específica.

        Args:
            nome: Nome da fonte
            categoria: Categoria da fonte

        Returns:
            Dicionário com dados da fonte ou None se não encontrada
        """
        if not self._is_available():
            return None

        try:
            result = self.client.table(self.TABLE_NAME).select("*").eq(
                "nome", nome
            ).eq(
                "categoria", categoria
            ).limit(1).execute()

            if result.data:
                return result.data[0]

        except Exception as e:
            logger.error("fonte_obter_erro", error=str(e))

        return None

    async def listar_por_categoria(
        self,
        categoria: str
    ) -> List[Dict[str, Any]]:
        """
        Lista todas as fontes de uma categoria.

        Args:
            categoria: Categoria a filtrar ('api', 'scraping', etc.)

        Returns:
            Lista de fontes na categoria
        """
        if not self._is_available():
            return []

        try:
            result = self.client.table(self.TABLE_NAME).select("*").eq(
                "categoria", categoria
            ).order("fonte_primaria").execute()

            return result.data or []

        except Exception as e:
            logger.error("fonte_listar_erro", error=str(e))
            return []

    async def listar_todas(self) -> List[Dict[str, Any]]:
        """
        Lista todas as fontes de dados registradas.

        Returns:
            Lista completa de fontes
        """
        if not self._is_available():
            return []

        try:
            result = self.client.table(self.TABLE_NAME).select("*").order(
                "categoria"
            ).order(
                "nome"
            ).execute()

            return result.data or []

        except Exception as e:
            logger.error("fonte_listar_todas_erro", error=str(e))
            return []

    async def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Obtém estatísticas das fontes de dados.

        Returns:
            Dicionário com estatísticas agregadas
        """
        if not self._is_available():
            return {}

        try:
            todas = await self.listar_todas()

            stats = {
                "total_fontes": len(todas),
                "por_categoria": {},
                "por_confiabilidade": {},
                "com_api_key": 0,
                "sem_api_key": 0,
                "ultima_atualizacao": None
            }

            for fonte in todas:
                # Por categoria
                cat = fonte.get("categoria", "outros")
                stats["por_categoria"][cat] = stats["por_categoria"].get(cat, 0) + 1

                # Por confiabilidade
                conf = fonte.get("confiabilidade", "desconhecida")
                stats["por_confiabilidade"][conf] = stats["por_confiabilidade"].get(conf, 0) + 1

                # API key
                if fonte.get("api_key_necessaria"):
                    stats["com_api_key"] += 1
                else:
                    stats["sem_api_key"] += 1

                # Última atualização
                ultima = fonte.get("data_ultima_atualizacao")
                if ultima:
                    if not stats["ultima_atualizacao"] or ultima > stats["ultima_atualizacao"]:
                        stats["ultima_atualizacao"] = ultima

            return stats

        except Exception as e:
            logger.error("fonte_estatisticas_erro", error=str(e))
            return {}


# Singleton para uso direto
_fontes_repository: Optional[FontesDadosRepository] = None


def get_fontes_repository() -> FontesDadosRepository:
    """Retorna singleton do repository de fontes."""
    global _fontes_repository
    if _fontes_repository is None:
        _fontes_repository = FontesDadosRepository()
    return _fontes_repository


# Helper functions para uso simplificado nos scrapers
async def registrar_fonte_api(
    nome: str,
    provedor: str,
    url: str,
    cobertura: Optional[str] = None
) -> bool:
    """
    Atalho para registrar uso de fonte tipo API.

    Args:
        nome: Nome da fonte (ex: "Serper - Google Search")
        provedor: Provedor da API (ex: "Serper.dev")
        url: URL do endpoint
        cobertura: O que a fonte cobre

    Returns:
        True se registrado com sucesso
    """
    repo = get_fontes_repository()
    return await repo.registrar_uso(
        nome=nome,
        categoria="api",
        fonte_primaria=provedor,
        url=url,
        formato="JSON",
        confiabilidade="alta",
        cobertura=cobertura
    )


async def registrar_fonte_scraping(
    nome: str,
    site: str,
    url: str,
    cobertura: Optional[str] = None
) -> bool:
    """
    Atalho para registrar uso de fonte tipo scraping.

    Args:
        nome: Nome da fonte (ex: "Website Empresa XYZ")
        site: Site de origem
        url: URL raspada
        cobertura: O que a fonte cobre

    Returns:
        True se registrado com sucesso
    """
    repo = get_fontes_repository()
    return await repo.registrar_uso(
        nome=nome,
        categoria="scraping",
        fonte_primaria=site,
        url=url,
        formato="HTML",
        confiabilidade="media",
        cobertura=cobertura
    )
