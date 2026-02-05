"""
Scraping Hub v2.0 - Scrapers
Clientes para APIs de dados e scraping
"""

from .apollo import ApolloClient
from .base import BaseScraper
from .brasil_api import BrasilAPIClient
from .perplexity import PerplexityClient
from .serper import SerperClient
from .tavily import TavilyClient
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
