import asyncio
import time

import pandas as pd
import schedule
from loguru import logger

from .scraper.dexscreener_tokens_scraper import DexscreenerTokensScraper
from .scraper.dexscreener_traders_scraper import DexscreenerTradersScraper
from .scraper.wallet_portfolio_scraper import WalletPortfolioScraper

# Configure loguru to write to file
logger.add("error.log", rotation="500 MB", level="ERROR")


async def main():
    for filter in [
        "?sortBy=marketCapUsd&sortDirection=desc&limit=1000",
        "?rankBy=trendingScoreH24&order=desc&minMarketCap=1000000&minAge=100",
    ]:
        try:
            # Initialize the scraper
            scraper = DexscreenerTokensScraper()

            res = await scraper.get_tokens(
                "solana",
                from_page=1,
                to_page=1,
                filter_args=filter,
            )

            # Create a pandas DataFrame
            df = pd.DataFrame(res)

            # Filter the DataFrame for maker_count > 1000 and market_cap_usd > 500,000
            filtered_df = df[
                (df["maker_count"] > 5000) & (df["market_cap_usd"] > 1000000)
            ]
            addrs = filtered_df["address"].tolist()

            logger.info(f"Found {len(addrs)} tokens")

            scraper = DexscreenerTradersScraper()
            traders = []
            for addr in addrs:
                try:
                    await asyncio.sleep(0.4)
                    logger.info(f"Processing Token {addr}")
                    token_traders = await scraper.get_top_traders(
                        "solana",
                        addr,
                    )
                    logger.info(f"Found {len(token_traders)} traders for {addr}")
                    traders.extend(token_traders)
                except Exception as e:
                    logger.error(f"Error processing address {addr}: {str(e)}")

            pot_wallets = []

            for trader in traders:
                try:
                    buy_value = trader.get("buy_value", 1)
                    pnl = trader.get("pnl", 0)
                    buy_txn = trader.get("buy_txns", 0)

                    if buy_txn > 5:
                        continue
                    if pnl / buy_value < 2:  # Check if trader made at least 2x return
                        continue

                    wallet = trader.get("wallet", None)

                    if wallet is None:
                        continue
                    pot_wallets.append(wallet)
                except Exception:
                    continue

            scraper = WalletPortfolioScraper()

            df = await scraper.get_wallet_stats(pot_wallets)
            df.to_csv(f"output_{int(time.time())}.csv", index=False)
        except Exception as e:
            logger.error(f"An error occurred in main: {str(e)}")


def run_task():
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"An error occurred while running the application: {str(e)}")


def run():
    # Run immediately
    run_task()

    # Schedule the task to run at 12:00 PM (noon) and 6:00 PM
    schedule.every().day.at("12:00").do(run_task)
    schedule.every().day.at("18:00").do(run_task)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    run()
