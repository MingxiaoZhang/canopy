"""
Base Crawler - Core crawling functionality with composable features
"""

import aiohttp
import time
from typing import List
from ..features.base import CrawlerFeature
from .result import CrawlResult
from ..utils.parser import HTMLParser
from ..storage.storage import FileStorage


class BaseCrawler:
    """
    Clean base crawler focused on core crawling logic
    Features are added via composition using the builder pattern
    """

    def __init__(self, start_urls: List[str], max_pages: int = 100):
        self.start_urls = start_urls
        self.max_pages = max_pages
        self.features: List[CrawlerFeature] = []
        self.visited = set()
        self.pages_crawled = 0
        self.session = None
        self.storage = FileStorage()

    def add_feature(self, feature: CrawlerFeature):
        """Add a feature to this crawler"""
        self.features.append(feature)
        return self

    async def crawl(self) -> None:
        """Main crawling workflow"""
        async with aiohttp.ClientSession() as session:
            self.session = session

            # Initialize all features
            for feature in self.features:
                await feature.initialize(self)

            # Notify features that crawling is starting
            for feature in self.features:
                await feature.before_crawl(self)

            try:
                # Main crawling loop
                await self._crawl_loop()
            finally:
                # Clean up all features
                for feature in self.features:
                    await feature.finalize(self)

    async def _crawl_loop(self):
        """Core crawling loop with real HTTP fetching"""
        for url in self.start_urls:
            if self.pages_crawled >= self.max_pages:
                break

            # Fetch real content
            result = await self._fetch_url(url)

            # Let features process the result
            for feature in self.features:
                await feature.process_url(url, result, self)

            self.visited.add(url)
            self.pages_crawled += 1
            print(f"Crawled ({self.pages_crawled}/{self.max_pages}): {url}")

    async def _fetch_url(self, url: str) -> CrawlResult:
        """Fetch a single URL and return the result"""
        start_time = time.time()

        try:
            headers = {'User-Agent': 'TarzanCrawler/2.0'}
            timeout = aiohttp.ClientTimeout(total=30)

            async with self.session.get(url, headers=headers, timeout=timeout) as response:
                response_time = time.time() - start_time

                if response.status == 200:
                    content = await response.text()

                    # Parse HTML content
                    parser = HTMLParser(url)
                    parsed_data = parser.parse(content)

                    # Save HTML content
                    await self.storage.save_content(url, content, 'html')

                    # Save inline CSS if present
                    if parsed_data.get('inline_css'):
                        # Join all CSS blocks into a single string
                        css_content = '\n\n'.join(parsed_data['inline_css'])
                        await self.storage.save_content(url, css_content, 'css')

                    return CrawlResult(
                        url=url,
                        content=content,
                        parsed_data=parsed_data,
                        response_time=response_time,
                        status_code=response.status
                    )
                else:
                    return CrawlResult(
                        url=url,
                        error=f"HTTP {response.status}",
                        response_time=response_time,
                        status_code=response.status
                    )

        except Exception as e:
            return CrawlResult(
                url=url,
                error=str(e),
                response_time=time.time() - start_time
            )