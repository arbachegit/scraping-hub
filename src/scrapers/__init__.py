"""
Scraping Hub v2.0 - Scrapers
Clientes para APIs de dados e scraping
"""

from .base import BaseScraper
from .brasil_api import BrasilAPIClient
from .serper import SerperClient
from .tavily import TavilyClient
from .perplexity import PerplexityClient
from .apollo import ApolloClient
from .web_scraper import WebScraperClient

__all__ = [
    "BaseScraper",
    "BrasilAPIClient",
    "SerperClient",
    "TavilyClient",
    "PerplexityClient",
    "ApolloClient",
    "WebScraperClient"
]
