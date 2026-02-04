"""
Scraping Hub - Scrapers
Clientes para APIs de scraping externas
"""

from .coresignal import CoresignalClient
from .proxycurl import ProxycurlClient
from .firecrawl import FirecrawlClient

__all__ = ["CoresignalClient", "ProxycurlClient", "FirecrawlClient"]
