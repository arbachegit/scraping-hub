"""
Tests for Scrapers
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.scrapers import CoresignalClient, FirecrawlClient, ProxycurlClient


class TestCoresignalClient:
    """Testes para CoresignalClient"""

    @pytest.fixture
    def client(self):
        return CoresignalClient(api_key="test_key")

    @pytest.mark.asyncio
    async def test_headers(self, client):
        """Testa headers de autenticacao"""
        headers = client._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_key"

    @pytest.mark.asyncio
    async def test_search_companies(self, client):
        """Testa busca de empresas"""
        with patch.object(client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"data": [{"name": "Test Company"}]}

            result = await client.search_companies(name="Test")

            mock_post.assert_called_once()
            assert len(result) == 1
            assert result[0]["name"] == "Test Company"


class TestProxycurlClient:
    """Testes para ProxycurlClient"""

    @pytest.fixture
    def client(self):
        return ProxycurlClient(api_key="test_key")

    @pytest.mark.asyncio
    async def test_headers(self, client):
        """Testa headers de autenticacao"""
        headers = client._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_key"


class TestFirecrawlClient:
    """Testes para FirecrawlClient"""

    @pytest.fixture
    def client(self):
        return FirecrawlClient(api_key="test_key")

    @pytest.mark.asyncio
    async def test_headers(self, client):
        """Testa headers de autenticacao"""
        headers = client._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_key"
