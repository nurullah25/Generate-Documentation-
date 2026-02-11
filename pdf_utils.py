import os
import sys
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright

def _worker(html: str, out_path: str) -> None:
    # ✅ Ensure Windows subprocess support for Playwright
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    else:
        loop = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            page.emulate_media(media="screen")

            page.pdf(
                path=out_path,
                format="A4",
                print_background=True,
                margin={"top": "18mm", "bottom": "18mm", "left": "14mm", "right": "14mm"},
            )
            browser.close()
    finally:
        if loop is not None:
            loop.close()

def html_to_pdf(html: str, out_path: str) -> None:
    out_path = str(Path(out_path).resolve())
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # ✅ Run Playwright in a separate thread to avoid Streamlit/Tornado loop issues
    with ThreadPoolExecutor(max_workers=1) as ex:
        ex.submit(_worker, html, out_path).result()
