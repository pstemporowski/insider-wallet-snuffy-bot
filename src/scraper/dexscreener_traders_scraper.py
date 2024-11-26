from typing import Any, Dict, List

from loguru import logger
from patchright.async_api import (
    Browser,
    Page,
    TimeoutError,
    async_playwright,
)

from ..utils.scraper import (
    human_delay,
    human_random_behaviour,
    setup_browser,
    wait_for_cloudflare,
)

MS_TIMEOUT = 60000


class DexscreenerTradersScraper:
    def __init__(self):
        pass

    async def get_top_traders(
        self,
        chain_name: str,
        token_address: str,
    ) -> List[Dict[str, Any]]:
        async with async_playwright() as pwright:
            browser = await setup_browser(pwright)
            results = await self._process_token(
                chain_name=chain_name,
                token_address=token_address,
                browser=browser,
            )
            await browser.close()
            return results

    async def _process_token(
        self,
        browser: Browser,
        chain_name: str,
        token_address: str,
    ) -> List[Dict[str, Any]]:
        context = await browser.new_context(
            java_script_enabled=True,
        )
        url = f"https://dexscreener.com/{chain_name}/{token_address}"

        retries = 0
        max_retries = 3
        while retries < max_retries:
            try:
                page = await context.new_page()
                logger.info(f"Navigating to URL: {url}")
                await human_delay(1, 4)
                await page.goto(url)

                await human_delay(1, 3)
                await human_random_behaviour(page)

                await wait_for_cloudflare(page)

                logger.info("Page has loaded successfully.")
                await human_delay(1, 4)

                # Click on the 'Top Traders' tab
                await page.get_by_text("Top Traders", exact=True).click()

                await human_random_behaviour(page)

                logger.info("Clicked on the 'Top Traders' tab.")

                # Extract the wallets table
                results = await self._extract_top_traders(page)
                return results

            except TimeoutError:
                if retries < max_retries:
                    logger.info(
                        f"Retrying due to timeout. Attempt {retries + 1} of {max_retries}."
                    )
                else:
                    logger.error(
                        f"Failed to process token after {max_retries} retries."
                    )
                    return []
                retries += 1

            except Exception as e:
                retries += 1
                errMsg = str(e)
                logger.error(f"Error processing token: {errMsg}")
                return []

            finally:
                await page.close()

    async def _extract_top_traders(self, page: Page) -> List[Dict[str, Any]]:
        traders_data = []
        rank_element = page.locator("div span:has-text('RANK')")
        parent_div = rank_element.locator("..").locator("..")
        trader_rows = await parent_div.locator(":scope > *").all()
        logger.info(f"Found {len(trader_rows)} trader rows")

        for index, row in enumerate(trader_rows):
            try:
                if index == 0:  # Skip header row
                    continue

                # Get the last div containing an 'a' tag
                sol_scan_url = (
                    await row.locator("div:has(a)")
                    .last.locator("a")
                    .get_attribute("href")
                )
                wallet = sol_scan_url.split("/")[-1]

                row_text = await row.inner_text()
                stats = row_text.split("\n")

                # Skip entries where buy amount is "-"
                if stats[2] == "-":
                    continue

                if len(stats) >= 6:
                    buy_usd_amount = stats[2]
                    sell_token_amount = stats[4]
                    token_buy_info = stats[3]
                    token_sell_info = stats[5]
                    pnl = stats[6]

                    # Initialize default values
                    buy_token_amount = None
                    buy_txns = None
                    sell_txns = None

                    # Parse buy info
                    if token_buy_info != "-" and "/" in token_buy_info:
                        buy_parts = token_buy_info.split("/")
                        if len(buy_parts) == 2:
                            buy_token_amount = self._parse_amount(buy_parts[0])
                            buy_txns = buy_parts[1].replace("txns", "").strip()
                            buy_txns = self._parse_amount(buy_txns)

                    pnl = self._parse_amount(pnl)

                    # Parse sell info
                    if token_sell_info != "-" and "/" in token_sell_info:
                        sell_parts = token_sell_info.split("/")
                        if len(sell_parts) == 2:
                            sell_token_amount = self._parse_amount(sell_parts[0])
                            sell_txns = sell_parts[1].replace("txns", "").strip()
                            sell_txns = self._parse_amount(sell_txns)

                    # Parse USD amounts
                    buy_usd_amount = self._parse_amount(buy_usd_amount)
                    if isinstance(sell_token_amount, str):
                        sell_token_amount = self._parse_amount(sell_token_amount)

                    traders_data.append(
                        {
                            "sol_scan_url": sol_scan_url,
                            "wallet": wallet,
                            "buy_token_amount": buy_token_amount,
                            "buy_txns": buy_txns,
                            "sell_token_amount": sell_token_amount,
                            "sell_txns": sell_txns,
                            "buy_usd_amount": buy_usd_amount,
                            "sell_usd_amount": sell_token_amount,
                            "pnl": pnl,
                        }
                    )
            except Exception as e:
                logger.error(f"Error processing trader row: {e}")
                continue

        return traders_data

    def _parse_amount(self, amount_text: str) -> float:
        """
        Parse amounts like '$1.3M', '$45K', handle multipliers.
        """

        try:
            amount_text = amount_text.replace("$", "").strip()
            multiplier = 1
            if amount_text.endswith("K"):
                multiplier = 1e3
                amount_text = amount_text[:-1]
            elif amount_text.endswith("M"):
                multiplier = 1e6
                amount_text = amount_text[:-1]
            elif amount_text.endswith("B"):
                multiplier = 1e9
                amount_text = amount_text[:-1]
            amount = float(amount_text.replace(",", "").strip())
            return amount * multiplier
        except Exception:
            logger.error(f"Error parsing amount: {amount_text}")

            raise
