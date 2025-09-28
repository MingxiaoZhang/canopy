import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import logging

class ScreenshotCapture:
    def __init__(self, headless=True, viewport_width=1920, viewport_height=1080):
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.browser = None
        self.context = None
        self.playwright = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def start(self):
        """Initialize browser instance"""
        try:
            self.playwright = await async_playwright().start()

            # Launch Chromium browser
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

            # Create browser context with specific viewport
            self.context = await self.browser.new_context(
                viewport={'width': self.viewport_width, 'height': self.viewport_height},
                user_agent='Mozilla/5.0 (compatible; TarzanCrawler/1.0 Webkit) AppleWebKit/537.36'
            )

        except Exception as e:
            logging.error(f"Failed to start browser: {e}")
            raise

    async def close(self):
        """Clean up browser resources"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logging.error(f"Error closing browser: {e}")

    async def capture_screenshot(self, url, output_path, full_page=True, wait_time=3):
        """
        Capture screenshot of a webpage

        Args:
            url: URL to capture
            output_path: Path to save screenshot
            full_page: Whether to capture full page or just viewport
            wait_time: Seconds to wait for page to load

        Returns:
            str: Path to saved screenshot or None if failed
        """
        if not self.context:
            raise RuntimeError("Browser not initialized. Use 'async with' or call start() first")

        page = None
        try:
            # Create new page
            page = await self.context.new_page()

            # Navigate to URL
            await page.goto(url, wait_until='networkidle', timeout=30000)

            # Wait for additional loading
            await asyncio.sleep(wait_time)

            # Handle cookie banners and popups (basic approach)
            try:
                # Common selectors for cookie banners
                cookie_selectors = [
                    'button[id*="accept"]',
                    'button[class*="accept"]',
                    'button[id*="cookie"]',
                    'button[class*="cookie"]',
                    '[id*="cookieConsent"] button',
                    '.cookie-banner button'
                ]

                for selector in cookie_selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        await elements[0].click()
                        await asyncio.sleep(1)
                        break
            except:
                pass  # Ignore cookie banner handling errors

            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Take screenshot
            screenshot_options = {
                'path': output_path,
                'full_page': full_page,
                'type': 'png'
            }

            await page.screenshot(**screenshot_options)

            return str(output_path)

        except Exception as e:
            logging.error(f"Failed to capture screenshot for {url}: {e}")
            return None
        finally:
            if page:
                await page.close()

    async def capture_multiple_viewports(self, url, base_output_path):
        """
        Capture screenshots at different viewport sizes

        Args:
            url: URL to capture
            base_output_path: Base path for screenshots (will append viewport info)

        Returns:
            dict: Dictionary of viewport names to screenshot paths
        """
        viewports = {
            'desktop': {'width': 1920, 'height': 1080},
            'tablet': {'width': 768, 'height': 1024},
            'mobile': {'width': 375, 'height': 667}
        }

        results = {}

        for viewport_name, viewport_size in viewports.items():
            # Update context viewport
            await self.context.set_viewport_size(viewport_size['width'], viewport_size['height'])

            # Generate output path with viewport suffix
            path_obj = Path(base_output_path)
            output_path = path_obj.parent / f"{path_obj.stem}_{viewport_name}{path_obj.suffix}"

            # Capture screenshot
            screenshot_path = await self.capture_screenshot(url, str(output_path))
            if screenshot_path:
                results[viewport_name] = screenshot_path

        return results