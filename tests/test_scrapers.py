"""
IconsAI Scraping v2.0 - Tests for Scrapers
Testes para os clientes de API
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import (
    MOCK_APOLLO_ORGANIZATION,
    MOCK_APOLLO_PERSON,
    MOCK_CEP_DATA,
    MOCK_CNPJ_DATA,
    MOCK_PERPLEXITY_RESPONSE,
    MOCK_SERPER_NEWS,
    MOCK_SERPER_SEARCH,
    MOCK_TAVILY_SEARCH,
)

# ===========================================
# BRASIL API TESTS
# ===========================================


class TestBrasilAPIClient:
    """Testes para BrasilAPIClient"""

    @pytest.fixture
    def client(self):
        from src.scrapers import BrasilAPIClient

        return BrasilAPIClient()

    def test_init(self, client):
        """Testa inicialização do cliente"""
        assert client.base_url == "https://brasilapi.com.br/api"
        assert client.api_key == ""  # BrasilAPI não requer autenticação

    def test_headers(self, client):
        """Testa headers do cliente"""
        headers = client._get_headers()
        assert "Accept" in headers
        assert headers["Accept"] == "application/json"
        assert "User-Agent" in headers

    @pytest.mark.asyncio
    async def test_get_cnpj_valid(self, client):
        """Testa busca de CNPJ válido"""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_CNPJ_DATA

            result = await client.get_cnpj("19.131.243/0001-97")

            mock_get.assert_called_once_with("/cnpj/v1/19131243000197")
            assert result["cnpj"] == "19131243000197"
            assert result["razao_social"] == "NUBANK PAGAMENTOS S.A."
            assert result["nome_fantasia"] == "NUBANK"
            assert result["endereco"]["uf"] == "SP"
            assert len(result["socios"]) == 1

    @pytest.mark.asyncio
    async def test_get_cnpj_invalid_length(self, client):
        """Testa CNPJ com tamanho inválido"""
        with pytest.raises(ValueError, match="CNPJ inválido"):
            await client.get_cnpj("12345")

    @pytest.mark.asyncio
    async def test_get_cnpj_not_found(self, client):
        """Testa CNPJ não encontrado"""
        import httpx

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            response = MagicMock()
            response.status_code = 404
            mock_get.side_effect = httpx.HTTPStatusError(
                "Not found", request=MagicMock(), response=response
            )

            result = await client.get_cnpj("00000000000000")
            assert result == {}

    @pytest.mark.asyncio
    async def test_get_cep_valid(self, client):
        """Testa busca de CEP válido"""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MOCK_CEP_DATA

            result = await client.get_cep("05409-000")

            mock_get.assert_called_once_with("/cep/v2/05409000")
            assert result["cep"] == "05409000"
            assert result["cidade"] == "São Paulo"

    @pytest.mark.asyncio
    async def test_get_cep_invalid_length(self, client):
        """Testa CEP com tamanho inválido"""
        with pytest.raises(ValueError, match="CEP inválido"):
            await client.get_cep("123")

    @pytest.mark.asyncio
    async def test_get_banks(self, client):
        """Testa lista de bancos"""
        mock_banks = [{"code": 1, "name": "Banco do Brasil"}, {"code": 341, "name": "Itaú"}]
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_banks

            result = await client.get_banks()

            assert len(result) == 2
            assert result[0]["name"] == "Banco do Brasil"

    @pytest.mark.asyncio
    async def test_get_holidays(self, client):
        """Testa feriados nacionais"""
        mock_holidays = [
            {"date": "2024-01-01", "name": "Ano Novo"},
            {"date": "2024-04-21", "name": "Tiradentes"},
        ]
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_holidays

            result = await client.get_holidays(2024)

            mock_get.assert_called_once_with("/feriados/v1/2024")
            assert len(result) == 2

    def test_normalize_company(self, client):
        """Testa normalização de dados da empresa"""
        normalized = client._normalize_company(MOCK_CNPJ_DATA)

        assert normalized["cnpj"] == "19131243000197"
        assert normalized["razao_social"] == "NUBANK PAGAMENTOS S.A."
        assert normalized["porte"] == "media_grande"
        assert normalized["cnae_principal"]["codigo"] == 6499999
        assert normalized["endereco"]["municipio"] == "SAO PAULO"
        assert normalized["socios"][0]["nome"] == "DAVID VELEZ OSORNO"

    def test_normalize_company_empty(self, client):
        """Testa normalização com dados vazios"""
        result = client._normalize_company({})
        assert result == {}

        result = client._normalize_company(None)
        assert result == {}


# ===========================================
# SERPER TESTS
# ===========================================


class TestSerperClient:
    """Testes para SerperClient"""

    @pytest.fixture
    def client(self):
        from src.scrapers import SerperClient

        return SerperClient(api_key="test_serper_key")

    def test_init(self, client):
        """Testa inicialização do cliente"""
        assert client.base_url == "https://google.serper.dev"
        assert client.api_key == "test_serper_key"

    def test_headers(self, client):
        """Testa headers de autenticação"""
        headers = client._get_headers()
        assert "X-API-KEY" in headers
        assert headers["X-API-KEY"] == "test_serper_key"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_search(self, client):
        """Testa busca padrão"""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MOCK_SERPER_SEARCH

            result = await client.search("Nubank", num=10)

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]["json"]["q"] == "Nubank"
            assert call_args[1]["json"]["gl"] == "br"
            assert call_args[1]["json"]["hl"] == "pt-br"

            assert len(result["organic"]) == 2
            assert result["knowledge_graph"]["title"] == "Nubank"

    @pytest.mark.asyncio
    async def test_search_news(self, client):
        """Testa busca de notícias"""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MOCK_SERPER_NEWS

            result = await client.search_news("Nubank", num=5)

            mock_post.assert_called_once_with(
                "/news", json={"q": "Nubank", "num": 5, "gl": "br", "hl": "pt-br"}
            )
            assert len(result["news"]) == 1
            assert "100 milhões" in result["news"][0]["title"]

    @pytest.mark.asyncio
    async def test_search_images(self, client):
        """Testa busca de imagens"""
        mock_images = {"images": [{"imageUrl": "http://test.com/img.jpg"}]}
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_images

            result = await client.search_images("Nubank logo", num=5)

            mock_post.assert_called_once()
            assert "images" in result

    @pytest.mark.asyncio
    async def test_search_places(self, client):
        """Testa busca de lugares"""
        mock_places = {"places": [{"title": "Nubank HQ", "address": "São Paulo"}]}
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_places

            result = await client.search_places("Nubank São Paulo")

            mock_post.assert_called_once()
            assert "places" in result

    @pytest.mark.asyncio
    async def test_find_company_cnpj(self, client):
        """Testa busca de CNPJ pelo nome"""
        mock_result = {
            "organic": [
                {"title": "CNPJ Nubank", "snippet": "CNPJ: 19.131.243/0001-97 - Nubank Pagamentos"}
            ]
        }
        with patch.object(client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_result

            cnpj = await client.find_company_cnpj("Nubank")

            assert cnpj == "19131243000197"

    @pytest.mark.asyncio
    async def test_find_company_cnpj_not_found(self, client):
        """Testa CNPJ não encontrado"""
        with patch.object(client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"organic": []}

            cnpj = await client.find_company_cnpj("Empresa Inexistente XYZ")

            assert cnpj is None

    @pytest.mark.asyncio
    async def test_find_company_website(self, client):
        """Testa busca de website"""
        mock_result = {"organic": [{"link": "https://nubank.com.br", "title": "Nubank"}]}
        with patch.object(client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_result

            website = await client.find_company_website("Nubank")

            assert website == "https://nubank.com.br"

    @pytest.mark.asyncio
    async def test_find_company_linkedin(self, client):
        """Testa busca de LinkedIn"""
        mock_result = {
            "organic": [
                {"link": "https://linkedin.com/company/nubank", "title": "Nubank | LinkedIn"}
            ]
        }
        with patch.object(client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_result

            linkedin = await client.find_company_linkedin("Nubank")

            assert "linkedin.com/company/nubank" in linkedin

    @pytest.mark.asyncio
    async def test_find_politician_info(self, client):
        """Testa busca de informações de político"""
        with (
            patch.object(client, "search", new_callable=AsyncMock) as mock_search,
            patch.object(client, "search_news", new_callable=AsyncMock) as mock_news,
            patch.object(client, "_find_social", new_callable=AsyncMock) as mock_social,
        ):
            mock_search.return_value = MOCK_SERPER_SEARCH
            mock_news.return_value = MOCK_SERPER_NEWS
            mock_social.return_value = "https://instagram.com/politico"

            result = await client.find_politician_info("João Silva", role="prefeito", state="SP")

            assert result["name"] == "João Silva"
            assert result["role"] == "prefeito"
            assert "search_results" in result
            assert "news" in result


# ===========================================
# TAVILY TESTS
# ===========================================


class TestTavilyClient:
    """Testes para TavilyClient"""

    @pytest.fixture
    def client(self):
        from src.scrapers import TavilyClient

        return TavilyClient(api_key="test_tavily_key")

    def test_init(self, client):
        """Testa inicialização do cliente"""
        assert client.base_url == "https://api.tavily.com"
        assert client.api_key == "test_tavily_key"

    @pytest.mark.asyncio
    async def test_search(self, client):
        """Testa busca padrão"""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MOCK_TAVILY_SEARCH

            result = await client.search("Nubank fintech")

            mock_post.assert_called_once()
            assert "results" in result
            assert "answer" in result

    @pytest.mark.asyncio
    async def test_search_news(self, client):
        """Testa busca de notícias"""
        mock_news = {
            "results": [
                {"title": "Notícia 1", "url": "http://test.com", "published_date": "2024-01-01"}
            ]
        }
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_news

            result = await client.search_news("economia Brasil", days=7)

            assert "results" in result

    @pytest.mark.asyncio
    async def test_research(self, client):
        """Testa pesquisa profunda"""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MOCK_TAVILY_SEARCH

            await client.research("Análise do mercado de fintechs")

            call_args = mock_post.call_args
            # Deep search usa search_depth=advanced
            assert "search_depth" in call_args[1]["json"]


# ===========================================
# PERPLEXITY TESTS
# ===========================================


class TestPerplexityClient:
    """Testes para PerplexityClient"""

    @pytest.fixture
    def client(self):
        from src.scrapers import PerplexityClient

        return PerplexityClient(api_key="test_perplexity_key")

    def test_init(self, client):
        """Testa inicialização do cliente"""
        assert client.base_url == "https://api.perplexity.ai"
        assert client.api_key == "test_perplexity_key"

    def test_headers(self, client):
        """Testa headers de autenticação"""
        headers = client._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_perplexity_key"

    @pytest.mark.asyncio
    async def test_chat(self, client):
        """Testa chat básico"""
        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MOCK_PERPLEXITY_RESPONSE

            result = await client.chat("Quem fundou o Nubank?")

            assert "answer" in result
            assert "citations" in result
            assert "Nubank" in result["answer"]

    @pytest.mark.asyncio
    async def test_analyze_company(self, client):
        """Testa análise de empresa"""
        with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = {"answer": "O Nubank é uma fintech...", "citations": []}

            result = await client.analyze_company("Nubank")

            mock_chat.assert_called_once()
            assert "analysis" in result
            assert "company_name" in result

    @pytest.mark.asyncio
    async def test_find_competitors(self, client):
        """Testa busca de concorrentes"""
        with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = {
                "answer": "Concorrentes: Inter, C6 Bank, PicPay",
                "citations": [],
            }

            result = await client.find_competitors("Nubank", industry="fintech")

            assert "competitors_analysis" in result
            assert "company_name" in result

    @pytest.mark.asyncio
    async def test_suggest_okrs(self, client):
        """Testa sugestão de OKRs"""
        with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = {
                "answer": '{"objectives": [{"name": "Crescimento", "key_results": []}]}',
                "citations": [],
            }

            result = await client.suggest_okrs("Nubank", "fintech context")

            assert "okrs" in result
            assert "company_name" in result


# ===========================================
# APOLLO TESTS
# ===========================================


class TestApolloClient:
    """Testes para ApolloClient"""

    @pytest.fixture
    def client(self):
        from src.scrapers import ApolloClient

        return ApolloClient(api_key="test_apollo_key")

    def test_init(self, client):
        """Testa inicialização do cliente"""
        assert client.base_url == "https://api.apollo.io/v1"
        assert client.api_key == "test_apollo_key"

    def test_headers(self, client):
        """Testa headers"""
        headers = client._get_headers()
        assert "Content-Type" in headers
        assert "Cache-Control" in headers

    @pytest.mark.asyncio
    async def test_search_people(self, client):
        """Testa busca de pessoas"""
        mock_response = {"people": [MOCK_APOLLO_PERSON["person"]], "pagination": {"total": 1}}
        with patch.object(client, "_request_with_key", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.search_people(q_organization_name="Nubank", person_titles=["CEO"])

            assert "people" in result
            assert len(result["people"]) == 1

    @pytest.mark.asyncio
    async def test_enrich_person(self, client):
        """Testa enriquecimento de pessoa"""
        with patch.object(client, "_request_with_key", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = MOCK_APOLLO_PERSON

            result = await client.enrich_person(email="david@nubank.com.br")

            assert result is not None
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_organizations(self, client):
        """Testa busca de organizações"""
        mock_response = {
            "organizations": [MOCK_APOLLO_ORGANIZATION["organization"]],
            "pagination": {"total": 1},
        }
        with patch.object(client, "_request_with_key", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.search_organizations(q_organization_name="Nubank")

            assert "organizations" in result

    @pytest.mark.asyncio
    async def test_get_company_employees(self, client):
        """Testa busca de funcionários"""
        mock_response = {
            "people": [MOCK_APOLLO_PERSON["person"]],
            "pagination": {"total": 1, "total_entries": 1},
        }
        with patch.object(client, "_request_with_key", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.get_company_employees("Nubank", per_page=10)

            assert "employees" in result

    @pytest.mark.asyncio
    async def test_get_decision_makers(self, client):
        """Testa busca de tomadores de decisão"""
        mock_response = {
            "employees": [MOCK_APOLLO_PERSON["person"]],
            "pagination": {"total": 1},
            "total": 1,
        }
        with patch.object(client, "get_company_employees", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            await client.get_decision_makers("Nubank")

            mock_get.assert_called_once()
            # Verifica que busca por seniority
            call_args = mock_get.call_args
            assert "person_seniorities" in call_args[1]


# ===========================================
# WEB SCRAPER TESTS
# ===========================================


class TestWebScraperClient:
    """Testes para WebScraperClient"""

    @pytest.fixture
    def client(self):
        from src.scrapers import WebScraperClient

        return WebScraperClient()

    def test_init(self, client):
        """Testa inicialização do cliente"""
        assert client.timeout == 30.0
        assert client.stats["requests"] == 0

    @pytest.mark.asyncio
    async def test_scrape_basic(self, client):
        """Testa scraping básico (mocked)"""
        mock_html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Welcome</h1>
            <p>Test content here</p>
            <a href="https://test.com/link1">Link 1</a>
        </body>
        </html>
        """

        with patch.object(client, "fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_html

            result = await client.scrape("https://test.com")

            assert result["url"] == "https://test.com"
            assert result["metadata"]["title"] == "Test Page"
            assert "content" in result

    def test_extract_contact_info(self, client):
        """Testa extração de informações de contato"""
        text = """
        Entre em contato:
        Email: contato@empresa.com.br
        Telefone: (11) 99999-9999
        CNPJ: 12.345.678/0001-90
        """

        result = client._extract_contact_info(text)

        assert "contato@empresa.com.br" in result["emails"]
        assert any("99999" in p for p in result["phones"])
        # CNPJ é retornado no formato original
        assert "12.345.678/0001-90" in result["cnpj"]


# ===========================================
# CIRCUIT BREAKER TESTS
# ===========================================


class TestCircuitBreaker:
    """Testes para o Circuit Breaker"""

    def test_circuit_breaker_initial_state(self):
        """Testa estado inicial do Circuit Breaker"""
        from src.utils.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(name="test_breaker", failure_threshold=3, timeout=10.0)

        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed
        assert not breaker.is_open
        assert breaker.can_execute()

    def test_circuit_breaker_opens_after_failures(self):
        """Testa que o circuito abre após falhas consecutivas"""
        from src.utils.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(name="test_open", failure_threshold=3, timeout=60.0)

        # Registrar falhas
        breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED

        breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED

        breaker.record_failure()  # Terceira falha - deve abrir
        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open
        assert not breaker.can_execute()

    def test_circuit_breaker_success_resets_failures(self):
        """Testa que sucesso reseta contador de falhas"""
        from src.utils.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(name="test_reset", failure_threshold=3, timeout=60.0)

        # Duas falhas
        breaker.record_failure()
        breaker.record_failure()
        assert breaker._failure_count == 2

        # Sucesso reseta
        breaker.record_success()
        assert breaker._failure_count == 0
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_half_open_on_timeout(self):
        """Testa transição para HALF_OPEN após timeout"""
        import time

        from src.utils.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(
            name="test_half_open",
            failure_threshold=1,
            timeout=0.1,  # 100ms
        )

        # Abrir circuito
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Esperar timeout
        time.sleep(0.15)

        # Deve estar em HALF_OPEN
        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker.can_execute()

    def test_circuit_breaker_closes_after_success_in_half_open(self):
        """Testa que circuito fecha após sucesso em HALF_OPEN"""
        import time

        from src.utils.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(
            name="test_close", failure_threshold=1, success_threshold=2, timeout=0.1
        )

        # Abrir e esperar timeout
        breaker.record_failure()
        time.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN

        # Primeiro sucesso
        breaker.record_success()
        assert breaker.state == CircuitState.HALF_OPEN

        # Segundo sucesso - deve fechar
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_reopens_on_failure_in_half_open(self):
        """Testa que falha em HALF_OPEN reabre o circuito"""
        import time

        from src.utils.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(name="test_reopen", failure_threshold=1, timeout=0.1)

        # Abrir e esperar timeout
        breaker.record_failure()
        time.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN

        # Falha em HALF_OPEN reabre
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

    def test_circuit_breaker_stats(self):
        """Testa estatísticas do Circuit Breaker"""
        from src.utils.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(name="test_stats", failure_threshold=5, timeout=60.0)

        breaker.record_failure()
        breaker.record_failure()

        stats = breaker.get_stats()

        assert stats["name"] == "test_stats"
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 2
        assert stats["failure_threshold"] == 5

    def test_circuit_breaker_registry(self):
        """Testa registry global de Circuit Breakers"""
        from src.utils.circuit_breaker import CircuitBreakerRegistry

        # Limpar registry
        CircuitBreakerRegistry._breakers.clear()

        # Criar novo
        breaker1 = CircuitBreakerRegistry.get_or_create("service_a")
        CircuitBreakerRegistry.get_or_create("service_b")

        # Deve retornar mesmo objeto
        breaker1_again = CircuitBreakerRegistry.get_or_create("service_a")
        assert breaker1 is breaker1_again

        # Stats de todos
        all_stats = CircuitBreakerRegistry.get_all_stats()
        assert "service_a" in all_stats
        assert "service_b" in all_stats

    def test_scraper_has_circuit_breaker(self):
        """Testa que scrapers têm Circuit Breaker integrado"""
        from src.scrapers import SerperClient

        client = SerperClient(api_key="test_key")

        # Deve ter circuit breaker
        assert hasattr(client, "_circuit_breaker")
        assert hasattr(client, "circuit_breaker")
        assert hasattr(client, "reset_circuit_breaker")

        # Stats devem incluir circuit breaker
        stats = client.get_stats()
        assert "circuit_breaker" in stats
        assert stats["circuit_breaker"]["name"] == "Serper - Google Search"
