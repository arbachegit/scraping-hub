"""
IconsAI Scraping v2.0 - API Routes
"""

from .admin import router as admin_router
from .analytics import router as analytics_router
from .companies import router as companies_router
from .news import router as news_router
from .people import router as people_router
from .politicians import router as politicians_router

__all__ = [
    "admin_router",
    "analytics_router",
    "companies_router",
    "people_router",
    "politicians_router",
    "news_router",
]
