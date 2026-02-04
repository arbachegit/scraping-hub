"""
Scraping Hub - Scrapers
Clientes para APIs de scraping externas
"""

from .coresignal import CoresignalClient
from .firecrawl import FirecrawlClient
from .proxycurl import ProxycurlClient

__all__ = ["CoresignalClient", "ProxycurlClient", "FirecrawlClient"]
