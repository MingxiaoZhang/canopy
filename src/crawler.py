import asyncio
import aiohttp
from urllib.parse import urljoin, urlparse
from collections import deque
import time
from .storage import FileStorage
from .parser import HTMLParser
from .screenshot import ScreenshotCapture

class BasicCrawler:
    def __init__(self, start_urls, max_pages=100, enable_screenshots=True):
        self.start_urls = start_urls
        self.max_pages = max_pages
        self.visited = set()
        self.queue = deque(start_urls)
        self.session = None
        self.storage = FileStorage()
        self.enable_screenshots = enable_screenshots
        self.screenshot_capture = None

    async def fetch(self, url):
        """Fetch a single URL and return its content"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; TarzanCrawler/1.0)'
            }
            async with self.session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    return content
                else:
                    print(f"HTTP {response.status} for {url}")
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        return None

    async def crawl_url(self, url):
        """Crawl a single URL and extract data"""
        content = await self.fetch(url)

        if not content:
            return

        # Parse HTML content
        parser = HTMLParser(url)
        parsed_data = parser.parse(content)

        # Save HTML content
        html_path = await self.storage.save_content(url, content, 'html')
        print(f"Saved HTML: {html_path}")

        # Download and save external CSS files
        for css_url in parsed_data['css_links']:
            await self.download_css(css_url)

        # Save inline CSS if present
        if parsed_data['inline_css']:
            await self.save_inline_css(url, parsed_data['inline_css'])

        # Capture screenshot if enabled
        if self.enable_screenshots and self.screenshot_capture:
            await self.capture_webpage_screenshot(url)

        # Add new links to queue (same domain only for now)
        current_domain = urlparse(url).netloc
        for link in parsed_data['links']:
            link_domain = urlparse(link).netloc
            if link_domain == current_domain and link not in self.visited:
                self.queue.append(link)

    async def download_css(self, css_url):
        """Download and save CSS file"""
        css_content = await self.fetch(css_url)
        if css_content:
            css_path = await self.storage.save_content(css_url, css_content, 'css')
            print(f"Saved CSS: {css_path}")

    async def save_inline_css(self, url, inline_css_list):
        """Save inline CSS from style tags"""
        if not inline_css_list:
            return

        # Combine all inline CSS into one file
        combined_css = "\n\n/* ========== Next Style Block ========== */\n\n".join(inline_css_list)

        # Create a fake URL for inline CSS storage
        inline_url = f"{url}#inline-styles"
        css_path = await self.storage.save_content(inline_url, combined_css, 'css')
        print(f"Saved inline CSS: {css_path}")

    async def capture_webpage_screenshot(self, url):
        """Capture screenshot of the webpage"""
        try:
            # Generate screenshot path
            screenshot_path = self.storage.get_file_path(url, 'screenshot')

            # Capture screenshot
            result_path = await self.screenshot_capture.capture_screenshot(url, str(screenshot_path))

            if result_path:
                print(f"Saved screenshot: {result_path}")
            else:
                print(f"Failed to capture screenshot for {url}")

        except Exception as e:
            print(f"Screenshot capture error for {url}: {e}")

    async def crawl(self):
        """Main crawling loop"""
        async with aiohttp.ClientSession() as session:
            self.session = session

            # Initialize screenshot capture if enabled
            screenshot_context = None
            if self.enable_screenshots:
                try:
                    screenshot_context = ScreenshotCapture()
                    await screenshot_context.start()
                    self.screenshot_capture = screenshot_context
                    print("🖼️ Screenshot capture initialized")
                except Exception as e:
                    print(f"⚠️ Screenshot capture failed to initialize: {e}")
                    print("📄 Continuing with HTML/CSS crawling only")
                    self.enable_screenshots = False

            try:
                while self.queue and len(self.visited) < self.max_pages:
                    url = self.queue.popleft()

                    if url in self.visited:
                        continue

                    print(f"Crawling ({len(self.visited)+1}/{self.max_pages}): {url}")

                    await self.crawl_url(url)
                    self.visited.add(url)

                    # Basic politeness delay
                    await asyncio.sleep(1)

                print(f"Crawl completed. Visited {len(self.visited)} pages.")

            finally:
                # Clean up screenshot capture
                if screenshot_context:
                    await screenshot_context.close()
                    print("🖼️ Screenshot capture closed")