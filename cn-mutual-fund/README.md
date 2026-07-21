# cn-mutual-fund

China Mutual Fund Data MCP Server based on AKShare - Free mutual fund data for MCP.

## Features

- Fund basic info (size, fees, manager, rating, tracking index)
- NAV history (unit/cumulative NAV for return & drawdown calculation)
- Fund manager profiles (tenure, products, historical returns)
- Portfolio holdings (top stocks, bonds, industry allocation)
- Third-party ratings (Morningstar, Shanghai Securities, China Merchants, Jinan)
- Money flow / share changes (subscriptions, redemptions)
- Fund rankings (performance by category)
- Dividend history
- Fund search by keyword

## Installation

```bash
pip install -e .
```

## Usage with Claude Desktop / Claude Code

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "cn-mutual-fund": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "cn_mutual_fund"],
      "cwd": "cn-mutual-fund/src"
    }
  }
}
```

## Data Source

All data comes from AKShare (https://akshare.akfamily.xyz), which aggregates data from:
- 天天基金网 (East Money)
- 雪球 (Xueqiu)
- 巨潮资讯 (CNInfo)
- 新浪财经 (Sina Finance)

## License

Apache-2.0
