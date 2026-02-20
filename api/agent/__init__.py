"""
IconsAI Agent - Conversational AI for Business Intelligence Queries

This module provides a natural language interface for querying
empresas, pessoas, and noticias data using AI-powered intent parsing.

Fallback Chain: Perplexity -> Claude -> OpenAI
"""

from api.agent.router import router as agent_router

__all__ = ["agent_router"]
