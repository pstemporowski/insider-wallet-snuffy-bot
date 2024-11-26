import re
from typing import Any, Dict

from loguru import logger
from patchright.async_api import (
    Browser,
    TimeoutError,
    async_playwright,
)

from ..utils.scraper import (
    human_delay,
    human_random_behaviour,
    setup_browser,
    wait_for_cloudflare,
)
from ..utils.url import get_dexscreener_url

MS_TIMEOUT = 30000


class DexscreenerTokensScraper:
    def __init__(self):
        pass

    async def get_tokens(
        self,
        chain_name: str,
        from_page: int = 1,
        to_page: int = 1,
        filter_args: str = "",
    ):
        async with async_playwright() as pwright:
            browser = await setup_browser(pwright)
            chrome = pwright.devices["Desktop Chrome"]
            results = []
            for page_num in range(from_page, to_page + 1):
                res = await self._process_page(
                    chain_name=chain_name,
                    browser=browser,
                    page_num=page_num,
                    device=chrome,
                    filter_args=filter_args,
                )
                results.extend(res)
                await human_delay(0.3, 0.7)

            return results

    async def _process_page(
        self,
        browser: Browser,
        chain_name: str,
        page_num: int | None = None,
        filter_args: str | None = None,
        device: dict = {},
    ) -> list[dict]:
        retries = 0
        max_retries = 3
        while retries < max_retries:
            try:
                logger.info(f"Processing page {page_num}")
                context = await browser.new_context(
                    java_script_enabled=True,
                )

                page = await context.new_page()

                url = get_dexscreener_url(
                    chain_name=chain_name,
                    page=page_num,
                    filter_args=filter_args,
                )

                logger.info(f"Navigating to URL: {url}")
                await human_delay(1, 5)
                await page.goto(url)

                await wait_for_cloudflare(page)

                logger.info("Page has loaded successfully.")
                await human_delay(1, 5)

                await human_random_behaviour(page)
                selector = "div.ds-dex-table.ds-dex-table-top"
                table_element = await page.query_selector(selector)
                rows = await table_element.query_selector_all("a")
                results = []
                for row in rows:
                    href = await row.get_attribute("href")
                    addr = href.split("/")[-1]

                    divs = await row.query_selector_all("div")
                    texts = []
                    for div in divs:
                        text = await div.inner_text()
                        texts.append(text)
                    parsed_data = self._parse_row(texts)
                    parsed_data["address"] = addr
                    results.append(parsed_data)

                return results

            except TimeoutError:
                if retries < max_retries:
                    logger.info(
                        f"Retrying page processing due to timeout. Attempt {retries + 1} of {max_retries}."
                    )
                else:
                    logger.error(f"Failed to process page after {max_retries} retries.")
                    errMsg = "Process failed due to timeout. This could be due to: 1) Your proxy is being blocked, or 2) The wallet address is invalid. Please check the Recommendations section in the README for proxy configuration guidance and troubleshooting steps."

                    logger.error(errMsg)
                    return
                retries += 1

            except Exception as e:
                retries += 1
                errMsg = str(e)
                logger.error(errMsg)
                return

            finally:
                await page.close()

    def _parse_row(self, texts: list[str]) -> Dict[str, Any]:
        """
        Parse a row of data and convert numbers from strings to appropriate Python formats.
        Handle units like 'd' (days), 'mo' (months), and multipliers like 'K' (thousands), 'M' (millions).
        Remove unnecessary numbers from token names.
        Convert percentages to floats (e.g., '100%' -> 1.0).
        """
        # Headers as per the provided order
        headers = [
            "token_symbol",
            "token_name",
            "price_usd",
            "age",
            "transaction_count",
            "volume_usd",
            "maker_count",
            "price_change_5m",
            "price_change_1h",
            "price_change_6h",
            "price_change_24h",
            "liquidity_usd",
            "market_cap_usd",
        ]

        data = {}
        for header, text in zip(headers, texts):
            try:
                if header == "token_symbol":
                    continue
                elif header == "token_name":
                    # Remove any numbers and newline characters from Token Name
                    token_name = re.sub(r"\n\d+", "", text)
                    token_name = token_name.replace("\n", " ").strip()

                    data["token_name"] = token_name
                elif header == "price_usd":
                    price = text.replace("$", "").replace(",", "").strip()
                    data["price_usd"] = float(price)
                elif header == "age":
                    # Convert to days
                    age_text = text.strip()
                    data["age"] = self._parse_age(age_text)
                elif header in ["transaction_count", "maker_count"]:
                    # Remove commas and convert to int
                    value = int(self._parse_amount(text))
                    data[header] = value
                elif header in ["volume_usd", "liquidity_usd", "market_cap_usd"]:
                    amount = self._parse_amount(text)
                    data[header] = amount
                elif "price_change" in header:
                    # Convert percentage to float
                    percentage_text = text.replace("%", "").replace(",", "").strip()
                    percentage = self._parse_amount(percentage_text)
                    percentage = percentage / 100
                    data[header] = percentage
                else:
                    data[header] = text.strip()
            except Exception as e:
                data[header] = None
                logger.error(f"Error parsing {header}: {e}")
                continue
        return data

    def _parse_amount(self, amount_text: str) -> float:
        """
        Parse amounts like '$1.3M', '$45K', remove '$', handle multipliers.
        """
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

    def _parse_age(self, age_text: str) -> float:
        """
        Parse age strings like '9d', '2mo', '24h', '45m', '1y' and convert to hours.
        """
        if "y" in age_text:
            years = float(age_text.replace("y", "").strip())
            hours = years * 365 * 24  # Convert years to hours
        elif "d" in age_text:
            days = float(age_text.replace("d", "").strip())
            hours = days * 24  # Convert days to hours
        elif "mo" in age_text:
            months = float(age_text.replace("mo", "").strip())
            hours = months * 30 * 24  # Convert months to hours (30 days per month)
        elif "h" in age_text:
            hours = float(age_text.replace("h", "").strip())
        elif "m" in age_text:
            minutes = float(age_text.replace("m", "").strip())
            hours = (
                round(minutes / 60) if minutes >= 30 else minutes / 60
            )  # Convert minutes to hours, round if >= 30 mins
        else:
            hours = float(age_text) * 24  # Assume input is in days if no unit
        return hours
