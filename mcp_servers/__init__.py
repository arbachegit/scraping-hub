"""
IconsAI MCP Servers
Model Context Protocol servers para fontes de dados

Servers disponíveis:
- brasil_data_hub_mcp: Dados geográficos (capitais, municípios)
- serper_mcp: Google Search via Serper
- brasilapi_mcp: Dados públicos brasileiros (CNPJ, CEP)
- apollo_mcp: B2B Intelligence (LinkedIn, contatos)
- cnpja_mcp: Regime tributário
- perplexity_mcp: AI Research
"""

from .config import MCPConfig

__all__ = ["MCPConfig"]
__version__ = "1.0.0"
