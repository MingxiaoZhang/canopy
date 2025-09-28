import asyncio
import aiohttp
from urllib.parse import urljoin, urlparse
from collections import deque
import time
import logging
from .storage import FileStorage
from .parser import HTMLParser
from .screenshot import ScreenshotCapture
from .rate_limiter import RateLimiter
from .error_handler import ErrorHandler, RetryConfig

class BasicCrawler:
    def __init__(self, start_urls, max_pages=100, enable_screenshots=True, crawl_delay=1.0, max_retries=3):
        self.start_urls = start_urls
        self.max_pages = max_pages
        self.visited = set()
        self.queue = deque(start_urls)
        self.session = None
        self.storage = FileStorage()
        self.enable_screenshots = enable_screenshots
        self.screenshot_capture = None
        self.rate_limiter = RateLimiter(default_delay=crawl_delay, user_agent="TarzanCrawler/1.0")
        self.error_handler = ErrorHandler(RetryConfig(max_attempts=max_retries))

        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    async def fetch(self, url):
        """Fetch a single URL and return its content with error handling and retries"""
        return await self.error_handler.execute_with_retry(
            self._fetch_with_rate_limiting,
            url,
            url,  # Pass URL as first argument to the function
            domain=urlparse(url).netloc
        )

    async def _fetch_with_rate_limiting(self, url):
        """Internal fetch method with rate limiting"""
        domain = urlparse(url).netloc

        # Initialize domain settings if first time
        await self.rate_limiter.initialize_domain(self.session, domain)

        # Check if URL can be crawled (robots.txt compliance)
        can_crawl, reason = await self.rate_limiter.can_crawl_url(url)
        if not can_crawl:
            print(f"⛔ Skipping {url}: {reason}")
            return None

        # Wait for rate limiting
        await self.rate_limiter.wait_for_rate_limit(url)

        start_time = time.time()
        headers = {
            'User-Agent': self.rate_limiter.user_agent
        }

        # Set timeout and make request
        timeout = aiohttp.ClientTimeout(total=30)
        async with self.session.get(url, headers=headers, timeout=timeout) as response:
            response_time = time.time() - start_time

            # Update rate limiter with response info
            await self.rate_limiter.request_completed(url, response_time, response.status)

            # Handle different HTTP status codes
            if response.status == 200:
                content = await response.text()
                return content
            elif response.status == 429:
                # Rate limited - this will be retried by error handler
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=429,
                    message="Rate limited"
                )
            elif 400 <= response.status < 500:
                # Client error - typically not retryable
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=f"Client error: {response.status}"
                )
            elif 500 <= response.status < 600:
                # Server error - retryable
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=f"Server error: {response.status}"
                )
            else:
                print(f"HTTP {response.status} for {url}")
                return None

    async def crawl_url(self, url):
        """Crawl a single URL and extract data with comprehensive error handling"""
        try:
            content = await self.fetch(url)

            if not content:
                return

            # Parse HTML content with error handling
            try:
                parser = HTMLParser(url)
                parsed_data = parser.parse(content)
            except Exception as e:
                logging.error(f"Failed to parse HTML for {url}: {e}")
                return

            # Save HTML content with error handling
            try:
                html_path = await self.storage.save_content(url, content, 'html')
                print(f"Saved HTML: {html_path}")
            except Exception as e:
                logging.error(f"Failed to save HTML for {url}: {e}")

            # Download and save external CSS files with error handling
            for css_url in parsed_data['css_links']:
                try:
                    await self.download_css(css_url)
                except Exception as e:
                    logging.warning(f"Failed to download CSS {css_url}: {e}")

            # Save inline CSS if present
            if parsed_data['inline_css']:
                try:
                    await self.save_inline_css(url, parsed_data['inline_css'])
                except Exception as e:
                    logging.warning(f"Failed to save inline CSS for {url}: {e}")

            # Capture screenshot if enabled with error handling
            if self.enable_screenshots and self.screenshot_capture:
                try:
                    await self.capture_webpage_screenshot(url)
                except Exception as e:
                    logging.warning(f"Failed to capture screenshot for {url}: {e}")

            # Add new links to queue (same domain only for now)
            try:
                current_domain = urlparse(url).netloc
                for link in parsed_data['links']:
                    link_domain = urlparse(link).netloc
                    if link_domain == current_domain and link not in self.visited:
                        self.queue.append(link)
            except Exception as e:
                logging.warning(f"Failed to process links for {url}: {e}")

        except Exception as e:
            logging.error(f"Critical error crawling {url}: {e}")
            # Continue with next URL rather than crashing

    async def download_css(self, css_url):
        """Download and save CSS file with error handling"""
        try:
            css_content = await self.fetch(css_url)
            if css_content:
                css_path = await self.storage.save_content(css_url, css_content, 'css')
                print(f"Saved CSS: {css_path}")
        except Exception as e:
            # Re-raise for higher level handling
            raise e

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

                print(f"Crawl completed. Visited {len(self.visited)} pages.")

                # Print error summary
                error_summary = self.error_handler.get_error_summary()
                if error_summary['total_errors'] > 0:
                    print(f"\n❌ Error Summary:")
                    print(f"  Total errors: {error_summary['total_errors']}")
                    print(f"  Failed URLs: {error_summary['failed_urls']}")
                    if error_summary['error_types']:
                        print(f"  Error types: {error_summary['error_types']}")
                    if error_summary['circuit_breaker_states']:
                        print(f"  Circuit breakers: {error_summary['circuit_breaker_states']}")

                    # List failed URLs for debugging
                    failed_urls = self.error_handler.get_failed_urls()
                    if failed_urls:
                        print(f"  Failed URLs list: {failed_urls[:5]}{'...' if len(failed_urls) > 5 else ''}")
                else:
                    print("\n✅ No errors encountered!")

                # Print rate limiting stats
                print("\n📊 Rate Limiting Stats:")
                domain_stats = self.rate_limiter.get_domain_stats()
                for domain, stats in domain_stats.items():
                    print(f"  {domain}: {stats['recent_requests']} requests, "
                          f"{stats['crawl_delay']:.1f}s delay, "
                          f"avg response: {stats['avg_response_time']:.1f}s")

            finally:
                # Clean up screenshot capture
                if screenshot_context:
                    await screenshot_context.close()
                    print("🖼️ Screenshot capture closed")