#!/usr/bin/env python3
"""rx_shortage_mcp server entry point.

Headline UX: an LLM (Claude Desktop / Claude Code) orchestrates four read-only
tools to answer "Drug X is short — what could be considered instead, and are
those also short?" The tools are deterministic data-fetchers; ALL reasoning
(class selection, ranking, the cascade narrative, safety framing) lives in the
model. Decision-support only — never a substitution authority.

Tools (added across build phases):
    rx_health          — connectivity check (Phase 0)
    rx_check_shortage  — openFDA shortage status (Phase 1)
    rx_normalize_drug  — messy name → RxCUI (Phase 2)
    rx_get_drug_class  — drug → candidate ATC-4 classes (Phase 3)
    rx_find_alternatives — class → sibling drugs (Phase 3)
"""

import logging
import sys
from typing import TypedDict

from mcp.server.fastmcp import FastMCP

# CRITICAL (stdio transport): stdout carries the JSON-RPC stream. A stray print()
# to stdout corrupts it. ALL logging must go to stderr.
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("rx_shortage_mcp")

mcp = FastMCP("rx_shortage_mcp")


class HealthStatus(TypedDict):
    """Structured result of the rx_health check (drives the tool's outputSchema)."""

    status: str
    server: str
    version: str
    next_step: str


@mcp.tool(
    name="rx_health",
    annotations={
        "title": "Health Check",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def rx_health() -> HealthStatus:
    """Confirm the rx_shortage_mcp server is running and reachable.

    A zero-argument connectivity check. Use it to verify the server is live
    before running the shortage → alternatives → cascade-check chain.

    Returns:
        HealthStatus: {
            "status": str,      # "ok" when healthy
            "server": str,      # "rx_shortage_mcp"
            "version": str,     # package version, e.g. "0.1.0"
            "next_step": str    # what to call next
        }
    """
    from . import __version__

    return {
        "status": "ok",
        "server": "rx_shortage_mcp",
        "version": __version__,
        "next_step": "Server is live. Begin a query with rx_normalize_drug.",
    }


def main() -> None:
    """Console-script entry point — runs the server over stdio."""
    logger.info("Starting rx_shortage_mcp server (stdio transport)")
    mcp.run()


if __name__ == "__main__":
    main()
