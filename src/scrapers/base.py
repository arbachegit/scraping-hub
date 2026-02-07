"""
Base Scraper Client
Classe base para todos os clientes de scraping
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class BaseScraper(ABC):
    """Classe base para scrapers"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        rate_limit: int = 100,
        timeout: float = 30.0
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.rate_limit = rate_limit
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

        # Metricas
        self.stats: Dict[str, Any] = {
            "requests": 0,
            "success": 0,
            "errors": 0,
            "last_request": None
        }

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy client initialization"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._get_headers()
            )
        return self._client

    @abstractmethod
    def _get_headers(self) -> Dict[str, str]:
        """Retorna headers de autenticacao"""
        pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Executa request com retry automatico"""
        self.stats["requests"] += 1
        self.stats["last_request"] = datetime.utcnow().isoformat()

        try:
            response = await self.client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json
            )
            response.raise_for_status()
            self.stats["success"] += 1

            return response.json()

        except httpx.HTTPStatusError as e:
            self.stats["errors"] += 1
            logger.error(
                "http_error",
                status=e.response.status_code,
                endpoint=endpoint,
                error=str(e)
            )
            raise

        except Exception as e:
            self.stats["errors"] += 1
            logger.error("request_error", endpoint=endpoint, error=str(e))
            raise

    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """GET request"""
        return await self._request("GET", endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """POST request"""
        return await self._request("POST", endpoint, params=params, json=json)

    async def close(self):
        """Fecha o cliente HTTP"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatisticas de uso"""
        return {
            **self.stats,
            "success_rate": (
                (self.stats["success"] / self.stats["requests"] * 100)
                if self.stats["requests"] > 0 else 0
            )
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
