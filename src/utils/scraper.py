import asyncio
import math
import random
import time

from patchright.async_api import Browser, Page, Playwright

MS_TIMEOUT = 60000


async def setup_browser(playwright: Playwright | None) -> Browser:
    return await playwright.chromium.launch(
        headless=False,
        timeout=MS_TIMEOUT,
        args=["--window-position=20,1"],
    )


async def human_random_behaviour(page: Page):
    # Natural reading pause
    await human_delay(0.4, 0.8)

    # Multiple micro-movements to simulate human hand tremor
    for _ in range(random.randint(2, 4)):
        await page.mouse.move(
            random.randint(100, 800) + random.randint(-10, 10),
            random.randint(100, 600) + random.randint(-10, 10),
            steps=random.randint(3, 7),
        )
        await human_delay(0.1, 0.3)

    # Natural scrolling pattern with acceleration/deceleration
    scroll_segments = random.randint(2, 4)
    for i in range(scroll_segments):
        scroll_speed = random.randint(30, 150)
        scroll_direction = random.choice([-1, 1])
        await page.mouse.wheel(0, scroll_speed * scroll_direction)
        await human_delay(0.2, 0.8)

    # Occasional text selection (like humans do while reading)
    if random.random() < 0.4:
        await page.mouse.down()
        await page.mouse.move(
            random.randint(200, 600),
            random.randint(100, 400),
            steps=random.randint(4, 8),
        )
        await page.mouse.up()

    # Random cursor hover over interactive elements
    await page.mouse.move(
        random.randint(100, 800),
        random.randint(100, 600),
        steps=random.randint(5, 10),
    )

    # Variable speed scrolling (humans don't scroll at constant speed)
    if random.random() < 0.5:
        scroll_distance = random.randint(100, 400)
        steps = random.randint(4, 8)
        for step in range(steps):
            momentum = abs(math.sin(step / steps * math.pi))
            await page.mouse.wheel(0, int(scroll_distance / steps * momentum))
            await human_delay(0.1, 0.3)


async def human_delay(self, min_delay=0.1, max_delay=0.5):
    delay = random.uniform(min_delay, max_delay)
    await asyncio.sleep(delay)


async def wait_for_cloudflare(
    page: Page,
):
    timeout = 60
    start_time = time.time()
    while await page.title() == "Just a moment...":
        if time.time() - start_time > timeout:
            raise TimeoutError("Cloudflare check timeout after 60 seconds")
        await asyncio.sleep(1)
    await page.wait_for_load_state("domcontentloaded", timeout=MS_TIMEOUT)
