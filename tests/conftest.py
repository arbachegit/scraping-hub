"""
Scraping Hub v2.0 - Test Fixtures
Configurações compartilhadas para testes
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ===========================================
# MOCK DATA
# ===========================================

MOCK_CNPJ_DATA = {
    "cnpj": "19131243000197",
    "razao_social": "NUBANK PAGAMENTOS S.A.",
    "nome_fantasia": "NUBANK",
    "natureza_juridica": "Sociedade Empresária Limitada",
    "descricao_situacao_cadastral": "ATIVA",
    "data_inicio_atividade": "2013-05-06",
    "capital_social": 1000000.0,
    "porte": "DEMAIS",
    "cnae_fiscal": 6499999,
    "cnae_fiscal_descricao": "Outras atividades de serviços financeiros",
    "cnaes_secundarios": [],
    "logradouro": "RUA CAPOTE VALENTE",
    "numero": "39",
    "complemento": "ANDAR 19 A 23",
    "bairro": "PINHEIROS",
    "cep": "05409000",
    "municipio": "SAO PAULO",
    "uf": "SP",
    "ddd_telefone_1": "1130420100",
    "email": "contato@nubank.com.br",
    "qsa": [
        {
            "nome_socio": "DAVID VELEZ OSORNO",
            "qualificacao_socio": "Sócio-Administrador",
            "data_entrada_sociedade": "2013-05-06"
        }
    ]
}

MOCK_CEP_DATA = {
    "cep": "05409000",
    "street": "Rua Capote Valente",
    "neighborhood": "Pinheiros",
    "city": "São Paulo",
    "state": "SP",
    "location": {
        "type": "Point",
        "coordinates": {"latitude": -23.5678, "longitude": -46.6789}
    }
}

MOCK_SERPER_SEARCH = {
    "organic": [
        {
            "title": "Nubank - Conta Digital e Cartão de Crédito",
            "link": "https://nubank.com.br",
            "snippet": "O Nubank é o maior banco digital do Brasil..."
        },
        {
            "title": "Nubank - LinkedIn",
            "link": "https://linkedin.com/company/nubank",
            "snippet": "Nubank | 10.000+ funcionários"
        }
    ],
    "knowledgeGraph": {
        "title": "Nubank",
        "type": "Fintech",
        "description": "Banco digital brasileiro",
        "website": "https://nubank.com.br",
        "founded": "2013",
        "headquarters": "São Paulo, Brasil"
    },
    "relatedSearches": [
        {"query": "nubank cartão"},
        {"query": "nubank conta"}
    ],
    "peopleAlsoAsk": [
        {"question": "Qual é o CNPJ do Nubank?"}
    ]
}

MOCK_SERPER_NEWS = {
    "news": [
        {
            "title": "Nubank atinge 100 milhões de clientes",
            "link": "https://exame.com/nubank-100mi",
            "source": "Exame",
            "date": "2024-01-15",
            "snippet": "O banco digital brasileiro..."
        }
    ]
}

MOCK_TAVILY_SEARCH = {
    "results": [
        {
            "title": "Nubank - Fintech Brasileira",
            "url": "https://nubank.com.br",
            "content": "Nubank é uma fintech brasileira fundada em 2013...",
            "score": 0.95
        }
    ],
    "answer": "O Nubank é o maior banco digital da América Latina."
}

MOCK_PERPLEXITY_RESPONSE = {
    "id": "test-123",
    "model": "llama-3.1-sonar-small-128k-online",
    "choices": [
        {
            "message": {
                "content": "O Nubank é uma fintech brasileira fundada em 2013 por David Vélez."
            }
        }
    ],
    "citations": [
        "https://nubank.com.br/sobre-nos",
        "https://wikipedia.org/wiki/Nubank"
    ],
    "usage": {}
}

MOCK_APOLLO_PERSON = {
    "person": {
        "id": "person-123",
        "first_name": "David",
        "last_name": "Vélez",
        "name": "David Vélez",
        "title": "CEO",
        "organization": {
            "name": "Nubank",
            "website_url": "https://nubank.com.br"
        },
        "email": "david@nubank.com.br",
        "linkedin_url": "https://linkedin.com/in/davidvelez"
    }
}

MOCK_APOLLO_ORGANIZATION = {
    "organization": {
        "id": "org-123",
        "name": "Nubank",
        "website_url": "https://nubank.com.br",
        "linkedin_url": "https://linkedin.com/company/nubank",
        "estimated_num_employees": 10000,
        "industry": "Financial Services",
        "founded_year": 2013
    }
}


# ===========================================
# FIXTURES
# ===========================================

@pytest.fixture
def mock_httpx_client():
    """Mock para cliente HTTP"""
    with patch("httpx.AsyncClient") as mock:
        client = AsyncMock()
        mock.return_value.__aenter__.return_value = client
        yield client


@pytest.fixture
def mock_settings():
    """Mock para settings"""
    with patch("config.settings.settings") as mock:
        mock.serper_api_key = "test_serper_key"
        mock.tavily_api_key = "test_tavily_key"
        mock.perplexity_api_key = "test_perplexity_key"
        mock.apollo_api_key = "test_apollo_key"
        mock.anthropic_api_key = "test_anthropic_key"
        mock.brasil_api_url = "https://brasilapi.com.br/api"
        yield mock


@pytest.fixture
def brasil_api_client():
    """Fixture para BrasilAPIClient"""
    from src.scrapers import BrasilAPIClient
    return BrasilAPIClient()


@pytest.fixture
def serper_client(mock_settings):
    """Fixture para SerperClient"""
    from src.scrapers import SerperClient
    return SerperClient(api_key="test_key")


@pytest.fixture
def tavily_client(mock_settings):
    """Fixture para TavilyClient"""
    from src.scrapers import TavilyClient
    return TavilyClient(api_key="test_key")


@pytest.fixture
def perplexity_client(mock_settings):
    """Fixture para PerplexityClient"""
    from src.scrapers import PerplexityClient
    return PerplexityClient(api_key="test_key")


@pytest.fixture
def apollo_client(mock_settings):
    """Fixture para ApolloClient"""
    from src.scrapers import ApolloClient
    return ApolloClient(api_key="test_key")


# ===========================================
# API TEST FIXTURES
# ===========================================

@pytest.fixture
def mock_jwt_token():
    """Token JWT válido para testes"""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QHRlc3QuY29tIiwidXNlcl9pZCI6IjEiLCJyb2xlIjoiYWRtaW4iLCJleHAiOjk5OTk5OTk5OTl9.test"


@pytest.fixture
def auth_headers(mock_jwt_token):
    """Headers de autenticação para testes de API"""
    return {"Authorization": f"Bearer {mock_jwt_token}"}
