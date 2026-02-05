"""
Scraping Hub v2.0 - API Routes
"""

from .companies import router as companies_router
from .people import router as people_router
from .politicians import router as politicians_router
from .news import router as news_router

__all__ = [
    "companies_router",
    "people_router",
    "politicians_router",
    "news_router"
]
