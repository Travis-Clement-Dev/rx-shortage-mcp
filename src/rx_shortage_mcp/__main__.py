"""Enable ``python -m rx_shortage_mcp`` to launch the server.

This is the robust launch path used by the README / Claude Desktop config: it
depends only on the package being importable, not on console-script generation.
"""

from .server import main

main()
