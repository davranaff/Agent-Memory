"""MCP Client — connects to external MCP servers to discover and call tools."""

from __future__ import annotations

import logging
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.types import Tool as MCPTool

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for connecting to external MCP servers."""

    def __init__(self) -> None:
        self._connections: dict[str, ClientSession] = {}
        self._tools: dict[str, dict[str, Any]] = {}  # tool_name -> {server_url, tool_info}

    async def connect(self, server_url: str) -> list[dict[str, Any]]:
        """Connect to an external MCP server and discover its tools.

        Args:
            server_url: SSE endpoint URL of the MCP server.

        Returns:
            List of discovered tools with their schemas.
        """
        try:
            async with sse_client(server_url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    # Discover tools
                    tools_response = await session.list_tools()
                    discovered = []

                    for tool in tools_response.tools:
                        tool_info = {
                            "name": tool.name,
                            "description": tool.description or "",
                            "input_schema": tool.inputSchema if hasattr(tool, "inputSchema") else {},
                            "server_url": server_url,
                        }
                        # Register with namespaced name to avoid conflicts
                        full_name = f"mcp:{server_url}:{tool.name}"
                        self._tools[full_name] = tool_info
                        discovered.append(tool_info)

                    logger.info(
                        "Connected to MCP server %s, discovered %d tools",
                        server_url,
                        len(discovered),
                    )
                    return discovered

        except Exception as e:
            logger.error("Failed to connect to MCP server %s: %s", server_url, e)
            raise

    async def call_tool(
        self, server_url: str, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        """Call a tool on an external MCP server.

        Args:
            server_url: SSE endpoint URL of the MCP server.
            tool_name: Name of the tool to call.
            arguments: Arguments to pass to the tool.

        Returns:
            Tool result.
        """
        try:
            async with sse_client(server_url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)

                    # Extract text content
                    if result.content:
                        texts = [c.text for c in result.content if hasattr(c, "text")]
                        return "\n".join(texts) if texts else str(result.content)

                    return str(result)

        except Exception as e:
            logger.error(
                "MCP tool call failed [%s on %s]: %s",
                tool_name,
                server_url,
                e,
            )
            raise

    async def discover_tools(self, server_url: str) -> list[dict[str, Any]]:
        """Discover tools from an MCP server without maintaining a connection.

        This is a convenience wrapper around connect().
        """
        return await self.connect(server_url)

    def get_registered_tools(self) -> dict[str, dict[str, Any]]:
        """Return all registered tools from external MCP servers."""
        return self._tools.copy()

    def list_tool_names(self) -> list[str]:
        """Return names of all registered external tools."""
        return list(self._tools.keys())


# Singleton instance
_mcp_client: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    """Get or create the MCP client singleton."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
