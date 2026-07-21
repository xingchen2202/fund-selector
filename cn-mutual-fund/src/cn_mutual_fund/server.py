"""
cn-mutual-fund: China Mutual Fund Data MCP Server based on AKShare.

Provides free Chinese mainland mutual fund (公募基金) data via MCP protocol.
Covers fund info, NAV history, manager profiles, portfolio holdings, ratings,
money flow, rankings, dividend data, and fund search.
"""

from mcp.server.fastmcp import FastMCP

# Create the MCP server instance
mcp = FastMCP(
    name="cn-mutual-fund",
    instructions=(
        "cn-mutual-fund provides free Chinese mainland mutual fund (公募基金) data via AKShare. "
        "Use the available tools to get fund basic info, NAV history, manager profiles, "
        "portfolio holdings (top stocks, bonds, industry allocation), fund ratings "
        "(Morningstar, Shanghai Securities, China Merchants, Jinan), "
        "money flow / share changes, fund rankings, dividend history, and fund search. "
        "Fund codes are 6-digit codes (e.g., '110011' for 易方达中小盘, '161725' for 招商中证白酒)."
    ),
)


def register_all_tools():
    """Register all tool modules with the MCP server."""
    # V0.1: Fund Info + NAV + Manager
    from .tools.fund_info import register as reg_fund_info
    from .tools.fund_nav import register as reg_fund_nav
    from .tools.fund_manager import register as reg_fund_manager

    reg_fund_info(mcp)
    reg_fund_nav(mcp)
    reg_fund_manager(mcp)

    # V0.2: Portfolio + Rating + Flow + Ranking + Dividend
    from .tools.fund_portfolio import register as reg_fund_portfolio
    from .tools.fund_rating import register as reg_fund_rating
    from .tools.fund_flow import register as reg_fund_flow
    from .tools.fund_ranking import register as reg_fund_ranking
    from .tools.fund_dividend import register as reg_fund_dividend

    reg_fund_portfolio(mcp)
    reg_fund_rating(mcp)
    reg_fund_flow(mcp)
    reg_fund_ranking(mcp)
    reg_fund_dividend(mcp)


# Register all tools at import time
register_all_tools()
