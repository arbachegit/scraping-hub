"""
Scraping Hub v2.0 - Tests for Services
Testes básicos para os serviços de inteligência
"""


import pytest

# ===========================================
# AI ANALYZER TESTS
# ===========================================

class TestAIAnalyzer:
    """Testes para AIAnalyzer service"""

    def test_init(self):
        """Testa inicialização do analisador"""
        from src.services import AIAnalyzer

        analyzer = AIAnalyzer()
        assert analyzer.model in AIAnalyzer.MODELS.values()
        assert analyzer.timeout == 120.0

    def test_init_with_model(self):
        """Testa inicialização com modelo específico"""
        from src.services import AIAnalyzer
        from config.settings import settings

        analyzer = AIAnalyzer(model="fast")
        # Se settings.anthropic_model estiver configurado, usa ele
        # Senão, usa o mapeamento MODELS
        if settings.anthropic_model:
            assert analyzer.model == settings.anthropic_model
        else:
            assert analyzer.model == AIAnalyzer.MODELS["fast"]

    def test_models_available(self):
        """Testa modelos disponíveis"""
        from src.services import AIAnalyzer

        assert "fast" in AIAnalyzer.MODELS
        assert "balanced" in AIAnalyzer.MODELS
        assert "powerful" in AIAnalyzer.MODELS


# ===========================================
# COMPANY INTEL TESTS
# ===========================================

class TestCompanyIntelService:
    """Testes para CompanyIntelService"""

    def test_init(self):
        """Testa inicialização do serviço"""
        from src.services import CompanyIntelService

        service = CompanyIntelService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Testa uso como context manager"""
        from src.services import CompanyIntelService

        async with CompanyIntelService() as service:
            assert service is not None


# ===========================================
# PEOPLE INTEL TESTS
# ===========================================

class TestPeopleIntelService:
    """Testes para PeopleIntelService"""

    def test_init(self):
        """Testa inicialização do serviço"""
        from src.services import PeopleIntelService

        service = PeopleIntelService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Testa uso como context manager"""
        from src.services import PeopleIntelService

        async with PeopleIntelService() as service:
            assert service is not None


# ===========================================
# POLITICIAN INTEL TESTS
# ===========================================

class TestPoliticianIntelService:
    """Testes para PoliticianIntelService"""

    def test_init(self):
        """Testa inicialização do serviço"""
        from src.services import PoliticianIntelService

        service = PoliticianIntelService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Testa uso como context manager"""
        from src.services import PoliticianIntelService

        async with PoliticianIntelService() as service:
            assert service is not None


# ===========================================
# NEWS MONITOR TESTS
# ===========================================

class TestNewsMonitorService:
    """Testes para NewsMonitorService"""

    def test_init(self):
        """Testa inicialização do serviço"""
        from src.services import NewsMonitorService

        service = NewsMonitorService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Testa uso como context manager"""
        from src.services import NewsMonitorService

        async with NewsMonitorService() as service:
            assert service is not None


# ===========================================
# COMPETITOR ANALYSIS TESTS
# ===========================================

class TestCompetitorAnalysisService:
    """Testes para CompetitorAnalysisService"""

    def test_init(self):
        """Testa inicialização do serviço"""
        from src.services import CompetitorAnalysisService

        service = CompetitorAnalysisService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Testa uso como context manager"""
        from src.services import CompetitorAnalysisService

        async with CompetitorAnalysisService() as service:
            assert service is not None
