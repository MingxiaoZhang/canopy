"""
Screenshot Feature - Captures screenshots of web pages
"""

import os
import asyncio
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from .base import CrawlerFeature
from ..crawler.result import CrawlResult


class ScreenshotFeature(CrawlerFeature):
    """Feature for capturing page screenshots"""

    def __init__(self, enabled: bool = True, headless: bool = True,
                 viewport_width: int = 1920, viewport_height: int = 1080):
        self.enabled = enabled
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.output_dir = None

    async def initialize(self, crawler):
        """Initialize screenshot capability"""
        if not self.enabled:
            return

        print("🖼️ Screenshot feature initialized")

        # Set up output directory
        today = datetime.now()
        date_path = f"{today.year:04d}/{today.month:02d}/{today.day:02d}"
        self.output_dir = os.path.join("crawl_data", "screenshot", date_path)
        os.makedirs(self.output_dir, exist_ok=True)

    async def before_crawl(self, crawler):
        """Setup before crawling starts"""
        if not self.enabled:
            return

        print("📸 Starting browser for screenshots...")

        # Initialize Playwright browser
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )

        self.context = await self.browser.new_context(
            viewport={'width': self.viewport_width, 'height': self.viewport_height},
            user_agent='Mozilla/5.0 (compatible; TarzanCrawler/1.0 Webkit) AppleWebKit/537.36'
        )

        self.page = await self.context.new_page()
        print("📸 Screenshot feature ready")

    async def process_url(self, url: str, result: CrawlResult, crawler):
        """Capture screenshot for the given URL"""
        if not self.enabled or not self.page:
            return

        # Only capture screenshots for successful responses
        if result.error or not result.content:
            print(f"⚠️ Skipping screenshot for {url}: {result.error}")
            return

        try:
            # Generate output filename
            from hashlib import md5
            url_hash = md5(url.encode()).hexdigest()[:32]
            domain = url.split('/')[2] if '//' in url else 'unknown'
            filename = f"{domain}_{url_hash}.png"
            filepath = os.path.join(self.output_dir, filename)

            # Navigate to URL and capture screenshot
            await self.page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)  # Wait for page to fully load

            # Handle cookie banners
            try:
                cookie_selectors = [
                    'button[id*="accept"]', 'button[class*="accept"]',
                    'button[id*="cookie"]', 'button[class*="cookie"]',
                    '[id*="cookieConsent"] button', '.cookie-banner button'
                ]
                for selector in cookie_selectors:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        await elements[0].click()
                        await asyncio.sleep(1)
                        break
            except:
                pass

            # Ensure directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            # Capture screenshot
            await self.page.screenshot(path=filepath, full_page=True, type='png')
            print(f"📸 Saved screenshot: {filename}")

        except Exception as e:
            print(f"❌ Screenshot error for {url}: {e}")

    async def finalize(self, crawler):
        """Clean up screenshot resources"""
        if not self.enabled:
            return

        print("🖼️ Closing browser...")
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            print(f"⚠️ Error closing browser: {e}")

        print("🖼️ Screenshot feature cleaned up")