"""Entry point for cn-mutual-fund MCP server."""

import sys

from .server import mcp

if __name__ == "__main__":
    mcp.run()
