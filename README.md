# Insider Wallet Snuffy

A powerful web scraping tool that tracks and analyzes successful crypto traders by monitoring their wallet activities across multiple platforms.

## What it does

1. **Token Discovery** (via DexScreener)
- Scrapes trending tokens on Solana with specific filters:
  - Market cap > $1M
  - Age > 150 days
  - High maker count (>5000)
- Source: https://dexscreener.com/solana

2. **Top Trader Analysis** (via DexScreener)
- For each discovered token, identifies successful traders by:
  - Analyzing their PnL (Profit and Loss)
  - Filtering for traders with >2x returns
  - Focusing on low transaction counts (<5) to find smart traders
- Source: https://dexscreener.com/{chain}/{token}/traders

3. **Portfolio Analysis** (via GMGN.ai)
- Deep dives into identified wallets to gather:
  - Total PnL
  - Win rates
  - Trading history
  - Current holdings
- Source: https://gmgn.ai/{chain}/address/{wallet}

## Key Features

- Multi-chain support (SOL, ETH, BASE, TRON, BLAST)
- Automated scheduling (runs daily at 12:00 PM and 6:00 PM)
- Human-like behavior simulation to avoid detection
- Comprehensive error handling and logging
- Data export to CSV for further analysis

The tool helps identify successful crypto traders by analyzing their trading patterns and portfolio performance across multiple platforms.