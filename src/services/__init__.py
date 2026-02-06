"""
Scraping Hub v2.0 - Services
Serviços de inteligência empresarial
"""

from .ai_analyzer import AIAnalyzer
from .analytics_etl import AnalyticsETL, AnalyticsTracker, get_analytics_etl, get_tracker
from .company_analysis import CompanyAnalysisService
from .company_intel import CompanyIntelService
from .competitor_analysis import CompetitorAnalysisService
from .news_monitor import NewsMonitorService
from .people_intel import PeopleIntelService
from .politician_intel import PoliticianIntelService
from .regional_intel import RegionalIntelService

__all__ = [
    "AIAnalyzer",
    "AnalyticsETL",
    "AnalyticsTracker",
    "get_analytics_etl",
    "get_tracker",
    "CompanyAnalysisService",
    "CompanyIntelService",
    "CompetitorAnalysisService",
    "NewsMonitorService",
    "PeopleIntelService",
    "PoliticianIntelService",
    "RegionalIntelService"
]
