"""
CSS Download Feature - Downloads external CSS files referenced in HTML
"""

import logging
import hashlib
from pathlib import Path
from urllib.parse import urlparse
import aiohttp
from .base import CrawlerFeature
from ..crawler.result import CrawlResult
from ..storage import ContentType

logger = logging.getLogger(__name__)


class CSSDownloadFeature(CrawlerFeature):
    """Feature for downloading external CSS files"""

    def __init__(self, enabled: bool = True, max_css_files: int = 50):
        self.enabled = enabled
        self.max_css_files = max_css_files
        self.downloaded_count = 0

    async def initialize(self, crawler):
        """Initialize CSS download capability"""
        if not self.enabled:
            return
        logger.info("CSS download feature initialized")

    async def before_crawl(self, crawler):
        """Setup before crawling starts"""
        if not self.enabled:
            return
        logger.info("CSS download feature ready")

    async def process_url(self, url: str, result: CrawlResult, crawler):
        """Download CSS files referenced in the HTML"""
        if not self.enabled:
            return

        # Only process successful responses with parsed data
        if result.error or not result.parsed_data:
            return

        css_links = result.parsed_data.get('css_links', [])
        if not css_links:
            return

        logger.info(f"Found {len(css_links)} CSS files for {url}")

        # Limit number of CSS files to download
        css_links = css_links[:self.max_css_files]

        for css_url in css_links:
            try:
                await self._download_css(css_url, url, crawler)
            except Exception as e:
                logger.warning(f"Failed to download CSS {css_url}: {str(e)[:50]}")

    async def _download_css(self, css_url: str, page_url: str, crawler):
        """Download a single CSS file"""
        try:
            # Use crawler's session to download CSS
            headers = {'User-Agent': 'CanopyCrawler/1.0'}
            timeout = aiohttp.ClientTimeout(total=10)

            async with crawler.session.get(css_url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    css_content = await response.text()

                    # Generate a safe filename from the CSS URL
                    css_filename = self._generate_css_filename(css_url)

                    # Save CSS file using the page's URL so it goes in the same directory
                    await crawler.storage.save_content(
                        page_url,
                        css_content,
                        ContentType.CSS,
                        filename_suffix=css_filename
                    )

                    self.downloaded_count += 1
                    logger.debug(f"Downloaded CSS: {css_filename} from {css_url}")
                else:
                    logger.warning(f"CSS download failed with status {response.status}: {css_url}")

        except Exception as e:
            logger.debug(f"Error downloading CSS {css_url}: {str(e)[:50]}")

    def _generate_css_filename(self, css_url: str) -> str:
        """Generate a safe filename for the CSS file"""
        # Parse URL to get the path
        parsed = urlparse(css_url)
        path = parsed.path

        # Get the filename from the path
        if path:
            filename = Path(path).name
            # Remove extension if present
            if filename.endswith('.css'):
                filename = filename[:-4]
        else:
            # Use URL hash if no path
            filename = hashlib.md5(css_url.encode()).hexdigest()[:12]

        # Sanitize filename
        safe_filename = filename.replace('.', '_').replace('/', '_').replace('\\', '_')
        safe_filename = safe_filename.replace(' ', '_').replace(':', '_')

        return safe_filename

    async def finalize(self, crawler):
        """Clean up CSS download resources"""
        if not self.enabled:
            return
        logger.info(f"CSS download feature completed - downloaded {self.downloaded_count} files")