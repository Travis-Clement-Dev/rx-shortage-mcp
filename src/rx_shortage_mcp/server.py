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
from typing import Annotated, TypedDict

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .openfda import ShortageResult, check_shortage
from .rxnav import NormalizeResult, normalize_drug

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


@mcp.tool(
    name="rx_check_shortage",
    annotations={
        "title": "Check Drug Shortage Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def rx_check_shortage(
    drug_name: Annotated[
        str,
        Field(
            description="Generic or ingredient drug name to check, e.g. 'furosemide', 'bumetanide'. "
            "Prefer the normalized ingredient name from rx_normalize_drug when you have one.",
            min_length=1,
            max_length=200,
        ),
    ],
) -> ShortageResult:
    """Check the current U.S. FDA (openFDA) shortage status of a drug.

    Queries the openFDA Drug Shortages dataset by generic name and aggregates the
    NDC/package-level records into a single status summary. National-level data only —
    it does NOT reflect a specific pharmacy's local/regional stock.

    Use this twice in the workflow: (1) to confirm the original drug is short, and
    (2) to re-check EACH candidate alternative — an alternative may itself be in
    shortage (the "cascade" check that is the point of this server).

    Args:
        drug_name: Generic/ingredient name (e.g. 'furosemide').

    Returns:
        ShortageResult — drug, in_shortage (bool), overall_status ('Current' /
        'To Be Discontinued' / 'Resolved' / 'no_record'), statuses (list of
        {status, count}), record_count, last_updated (MM/DD/YYYY or null),
        therapeutic_categories, reasons, and next_step guidance.
    """
    return await check_shortage(drug_name.strip())


@mcp.tool(
    name="rx_normalize_drug",
    annotations={
        "title": "Normalize Drug Name to RxCUI",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def rx_normalize_drug(
    name: Annotated[
        str,
        Field(
            description="A messy drug name to normalize: brand ('Lipitor'), generic, salt form "
            "('morphine sulfate'), abbreviation ('HCTZ'), or a typo. ",
            min_length=1,
            max_length=200,
        ),
    ],
) -> NormalizeResult:
    """Normalize a messy drug name/brand/typo to an RxNorm RxCUI and clean name.

    This is the FIRST step of the workflow. It uses RxNorm's prescribable search
    (exact-then-normalized), falling back to approximate matching for typos.

    IMPORTANT: if `match_type` is 'approximate', the result is a best guess — present
    the `candidates` to the user and confirm the intended drug before proceeding. Do
    not silently assume the top candidate is correct.

    Args:
        name: The drug name as the user typed it.

    Returns:
        NormalizeResult — found (bool), rxcui, name (resolved RxNorm name), match_type
        ('exact' / 'approximate' / 'none'), candidates (ranked, for approximate matches),
        and next_step guidance.
    """
    return await normalize_drug(name.strip())


def main() -> None:
    """Console-script entry point — runs the server over stdio."""
    logger.info("Starting rx_shortage_mcp server (stdio transport)")
    mcp.run()


if __name__ == "__main__":
    main()
