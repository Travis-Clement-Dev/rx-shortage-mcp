"""Protocol smoke test: spawn the server over stdio and drive it with a real MCP client.

Offline — rx_health calls no external API, so this runs in the normal suite.

We spawn with `sys.executable -m rx_shortage_mcp` (the same interpreter running the
tests). This both (a) exercises the exact `python -m` launch path the README/Claude
Desktop config use, and (b) avoids the nested `uv run` environment confusion that a
`uv run ... uv run` invocation causes.
"""

import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_server_speaks_mcp_over_stdio():
    params = StdioServerParameters(command=sys.executable, args=["-m", "rx_shortage_mcp"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.serverInfo.name == "rx_shortage_mcp"

            tools = await session.list_tools()
            tool_names = {t.name for t in tools.tools}
            assert "rx_health" in tool_names

            result = await session.call_tool("rx_health", {})
            assert result.isError is False
            assert result.structuredContent["status"] == "ok"
            assert result.structuredContent["server"] == "rx_shortage_mcp"
