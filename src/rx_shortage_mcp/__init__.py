"""rx_shortage_mcp — an MCP server for drug-shortage therapeutic-alternative finding.

Exposes read-only tools an LLM chains to answer: "Drug X is on shortage — what
could be considered instead, and are those alternatives also short?"

Decision-support only. Not a substitution authority. See README for the safety model.
"""

from .server import main

__all__ = ["main"]
__version__ = "0.1.0"
