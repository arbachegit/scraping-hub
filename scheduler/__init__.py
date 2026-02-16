"""
IconsAI Scheduler
Automação de coleta de dados empresariais

Execução diária às 2am-5am para empresas das 27 capitais brasileiras.
"""

from .collector import DataCollector

__all__ = ["DataCollector"]
