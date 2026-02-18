"""
Base MCP Server
Classe base para todos os MCP servers do IconsAI

Model Context Protocol (MCP) permite que agentes de IA
acessem fontes de dados externas de forma padronizada.
"""

import json
from abc import ABC, abstractmethod
from typing import Any

import structlog
from mcp.server import Server
from mcp.types import TextContent, Tool

logger = structlog.get_logger()


class BaseMCPServer(ABC):
    """
    Classe base para MCP Servers.

    Implementa:
    - Registro de tools
    - Handling padronizado de chamadas
    - Logging estruturado
    - Formatação de respostas

    Subclasses devem implementar:
    - get_tools(): Lista de tools disponíveis
    - handle_tool(): Processamento de chamadas
    """

    def __init__(self, name: str, version: str = "1.0.0"):
        """
        Inicializa MCP Server.

        Args:
            name: Nome único do server (ex: "serper-mcp")
            version: Versão do server
        """
        self.name = name
        self.version = version
        self.server = Server(name)
        self.logger = structlog.get_logger(name)
        self._register_handlers()

    @abstractmethod
    def get_tools(self) -> list[Tool]:
        """
        Retorna lista de tools disponíveis.

        Cada tool deve ter:
        - name: Identificador único
        - description: Descrição para o agente
        - inputSchema: JSON Schema dos parâmetros

        Returns:
            Lista de Tool objects
        """
        pass

    @abstractmethod
    async def handle_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """
        Processa chamada de tool.

        Args:
            name: Nome da tool chamada
            arguments: Parâmetros da chamada

        Returns:
            Lista de TextContent com resultado
        """
        pass

    def _register_handlers(self) -> None:
        """Registra handlers no MCP Server"""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            tools = self.get_tools()
            self.logger.debug("tools_listed", count=len(tools))
            return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            self.logger.info("tool_called", tool=name, args=list(arguments.keys()))
            try:
                result = await self.handle_tool(name, arguments)
                self.logger.info("tool_success", tool=name)
                return result
            except Exception as e:
                self.logger.error("tool_error", tool=name, error=str(e))
                return self._error_response(str(e))

    def _json_response(self, data: Any) -> list[TextContent]:
        """
        Formata resposta como JSON.

        Args:
            data: Dados para serializar

        Returns:
            Lista com TextContent JSON
        """
        return [
            TextContent(
                type="text",
                text=json.dumps(data, ensure_ascii=False, default=str),
            )
        ]

    def _error_response(self, message: str) -> list[TextContent]:
        """
        Formata resposta de erro.

        Args:
            message: Mensagem de erro

        Returns:
            Lista com TextContent de erro
        """
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"error": message, "success": False}, ensure_ascii=False
                ),
            )
        ]

    def _success_response(
        self, data: Any, message: str = "Success"
    ) -> list[TextContent]:
        """
        Formata resposta de sucesso.

        Args:
            data: Dados do resultado
            message: Mensagem opcional

        Returns:
            Lista com TextContent formatado
        """
        return self._json_response({"success": True, "message": message, "data": data})

    async def run_stdio(self) -> None:
        """Executa server via stdio (padrão MCP)"""
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )

    def get_info(self) -> dict[str, Any]:
        """Retorna informações do server"""
        return {
            "name": self.name,
            "version": self.version,
            "tools": [t.name for t in self.get_tools()],
        }
