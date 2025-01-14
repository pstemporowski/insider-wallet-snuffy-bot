import asyncio
import re
import time
import unicodedata
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger
from patchright.async_api import Browser, Page, async_playwright

from ..models.chains import Chain
from ..models.days_options import DaysOptions
from ..utils.parsers import convert_percentage_to_float, convert_profic_string_to_float
from ..utils.scraper import (
    human_delay,
    human_random_behaviour,
    setup_browser,
    wait_for_cloudflare,
)
from ..utils.url import get_gmgn_url

MS_TIMEOUT = 30000


class WalletPortfolioScraper:
    def _parse_balance_text(
        self,
        text: str,
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Parse balance text like '0.1 SOL ($22.08)' into amount and USD amount.
        """

        # Remove any commas and non-breaking spaces
        text = text.replace(",", "").replace("\u00a0", " ")

        # Regular expressions to extract token amount and USD amount
        token_amount = None
        usd_amount = None

        # Match token amount before the currency symbol
        token_match = re.match(r"([-+]?\d*\.\d+|\d+)", text)
        if token_match:
            token_amount = float(token_match.group(1))

        # Match USD amount inside parentheses, handling K/M/B suffixes
        usd_match = re.search(r"\(\$([-+]?\d*\.?\d+)([KMB])?\)", text)
        if usd_match:
            base_amount = float(usd_match.group(1))
            multiplier = {"K": 1000, "M": 1000000, "B": 1000000000}.get(
                usd_match.group(2), 1
            )
            usd_amount = base_amount * multiplier

        return token_amount, usd_amount

    async def _close_modals(self, page: Page):
        modal_selectors = [
            "button:has-text('I Know')",
            "#chakra-modal--body-\\:rt\\: div.css-147wlxj:has-text('Got it')",
            "#chakra-modal--body-\\:r13\\: div button",
            "#chakra-modal-\\:ri\\: button",
            "#chakra-modal-\\:rj\\: button",
            "#chakra-modal-\\:r1k\\: button",
            "#chakra-modal-\\:rl\\: button",
        ]
        for selector in modal_selectors:
            try:
                if await page.locator(selector).is_visible():
                    await human_delay(0.5, 2)
                    await page.locator(selector).click()
            except Exception as e:
                logger.warning(f"Modal handling failed: {str(e)}")

    async def get_wallet_stats(
        self,
        wallets: List[str],
        chain: Chain = Chain.SOL,
        days_option=DaysOptions.MONTH,
    ):
        async with async_playwright() as pwright:
            browser = await setup_browser(pwright)

            try:
                max_concurrent_tasks = 1  # Maximum number of concurrent tasks
                semaphore = asyncio.Semaphore(max_concurrent_tasks)
                tasks = [
                    self._process_wallet(
                        wallet,
                        chain=chain,
                        days_option=days_option,
                        semaphore=semaphore,
                        browser=browser,
                    )
                    for wallet in wallets
                ]

                results = await asyncio.gather(*tasks)
                stats_df = pd.DataFrame(results)
                stats_df.to_csv(f"tmp_wallet_stats_{time.time()}.csv", index=False)
                return stats_df
            finally:
                await browser.close()
                await pwright.stop()

    async def _click_30_days(self, page: Page):
        button = page.locator(
            "xpath=//*[@id='__next']/div/div/main/div[2]/div[1]/div[2]/div[1]/div[1]/div[2]"
        )

        await button.click()

    async def _process_wallet(
        self,
        wallet: str,
        chain: Chain,
        semaphore: asyncio.Semaphore,
        browser=Browser,
        days_option=DaysOptions.MONTH,
    ) -> Dict:
        retries = 0
        max_retries = 3

        while retries < max_retries:
            async with semaphore:
                try:
                    context = await browser.new_context(
                        java_script_enabled=True,
                        bypass_csp=True,
                    )

                    page = await context.new_page()

                    url = get_gmgn_url(wallet, chain_name=chain.value)
                    logger.info(f"Processing wallet: {wallet}")
                    logger.info(f"Navigating to: {url}")

                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=MS_TIMEOUT,
                    )

                    await wait_for_cloudflare(page=page)
                    await human_delay(1, 3)
                    await self._close_modals(page)
                    await human_random_behaviour(page)

                    await self._click_30_days(page)
                    await human_delay(1, 5)

                    stats = await self._get_wallet_stats_data(page)
                    stats["wallet"] = wallet
                    stats["chain"] = chain.value
                    stats["error"] = None
                    stats["days_option"] = days_option.value

                    logger.info(f"Wallet {wallet} processed successfully")
                    return stats

                except Exception as e:
                    retries += 1
                    errMsg = str(e)

                    if "Timeout" in errMsg:
                        errMsg = "Timeout error"

                    errMsg = f"Error processing wallet {wallet}: {errMsg}. Retrying..."
                    logger.error(errMsg)

                    if retries >= max_retries:
                        if "Timeout" in errMsg:
                            errMsg = "Process failed due to timeout. This could be due to: 1) Your proxy is being blocked, or 2) The wallet address is invalid. Please check the Recommendations section in the README for proxy configuration guidance and troubleshooting steps."
                            logger.error(errMsg)

                        logger.error(
                            f"Failed to process wallet {wallet} after {max_retries} attempts"
                        )
                        stats = {
                            "wallet": wallet,
                            "chain": chain.value,
                            "days_option": days_option.value,
                            "error": errMsg,
                        }

                        return stats

                finally:
                    await page.close()
                    await context.close()
                    await asyncio.sleep(5)

    async def _get_wallet_stats_data(self, page: Page) -> Dict:
        selectors = {
            "pnl": "xpath=//*[@id='__next']/div/div/main/div[2]/div[1]/div[2]/div[2]/div[1]/div[1]/div[2]",
            "winrate": "xpath=//*[@id='__next']/div/div/main/div[2]/div[1]/div[2]/div[2]/div[1]/div[2]/div[2]",
            "total_pnl": "xpath=//*[@id='__next']/div/div/main/div[2]/div[1]/div[2]/div[3]/div[2]/div[2]",
            "unrealized_profit": "xpath=//*[@id='__next']/div/div/main/div[2]/div[1]/div[2]/div[3]/div[3]/div[2]",
            "total_cost": "xpath=//*[@id='__next']/div/div/main/div[2]/div[1]/div[2]/div[3]/div[4]/div[2]",
            "token_avg_cost": "xpath=//*[@id='__next']/div/div/main/div[2]/div[1]/div[2]/div[3]/div[5]/div[2]",
            "token_avg_realized_profit": "xpath=//*[@id='__next']/div/div/main/div[2]/div[1]/div[2]/div[3]/div[6]/div[2]",
            "balance": "xpath=//*[@id='__next']/div/div/main/div[2]/div[1]/div[2]/div[3]/div[7]/div[2]",
        }

        str_values = {}
        for key, selector in selectors.items():
            element = page.locator(selector).first
            text = await element.inner_text(timeout=MS_TIMEOUT)
            text = unicodedata.normalize("NFC", text)
            text = text.replace("\u00a0", " ").strip()
            str_values[key] = text

        pnl_pct = convert_percentage_to_float(str_values["pnl"])
        winrate = convert_percentage_to_float(str_values["winrate"])
        unrealized_usd_profit = convert_profic_string_to_float(
            str_values["unrealized_profit"]
        )
        total_usd_cost = convert_profic_string_to_float(str_values["total_cost"])
        token_avg_usd_cost = convert_profic_string_to_float(
            str_values["token_avg_cost"]
        )
        token_avg_realized_usd_profit = convert_profic_string_to_float(
            str_values["token_avg_realized_profit"]
        )

        total_pnl_pct = None
        balance = None
        total_pnl_usd_amount = None
        usd_balance = None

        try:
            total_pnl_usd_amount, total_pnl_pct = self._parse_numeric_value(
                str_values["total_pnl"]
            )
            balance, usd_balance = self._parse_balance_text(str_values["balance"])

        except Exception as e:
            logger.error(f"Error parsing numeric values: {e}")

        return {
            "total_pnl_usd_amount": total_pnl_usd_amount,
            "total_pnl_pct": total_pnl_pct,
            "unrealized_usd_profit": unrealized_usd_profit,
            "total_usd_cost": total_usd_cost,
            "token_avg_usd_cost": token_avg_usd_cost,
            "token_avg_realized_usd_profit": token_avg_realized_usd_profit,
            "balance": balance,
            "usd_balance": usd_balance,
            "pnl_pct": pnl_pct,
            "winrate": winrate,
        }

    def _parse_numeric_value(self, text: str, split_index: int = 0) -> tuple:
        """
        Parse numeric values from text that may contain amount and percentage.
        """

        split_text = text.split(" ")
        amount = convert_profic_string_to_float(split_text[split_index])
        percentage = None
        if len(split_text) > 1 and "%" in split_text[1]:
            percentage = convert_percentage_to_float(split_text[1])
        return amount, percentage
