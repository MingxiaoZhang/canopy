import json
import gzip
import io
import hashlib
import logging
import aiofiles
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
from PIL import Image
from .content_type import ContentType

logger = logging.getLogger(__name__)


class FileStorage:
    def __init__(self, base_path='crawl_data', compress=True):
        self.base_path = Path(base_path)
        self.compress = compress  # Enable compression by default
        self.setup_directories()

    def setup_directories(self):
        """Create base directory structure - website-specific dirs created as needed"""
        self.base_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _is_text_content(content_type: ContentType) -> bool:
        """Check if content type is text-based"""
        return content_type in [
            ContentType.HTML,
            ContentType.CSS,
            ContentType.JSON,
            ContentType.DOM_TREE
        ]

    @staticmethod
    def _is_image_content(content_type: ContentType) -> bool:
        """Check if content type is image-based"""
        return content_type in [
            ContentType.SCREENSHOT,
            ContentType.COMPONENT_SCREENSHOT
        ]

    def get_file_path(self, url: str, content_type: ContentType, filename_suffix: str = None) -> Path:
        """Generate a file path for storing content organized by domain/page_id

        Args:
            url: The URL being stored
            content_type: ContentType enum
            filename_suffix: Optional suffix to add to filename (for component screenshots)

        Returns:
            Path object for the file

        Structure:
        - Single files (HTML, CSS, DOM tree, screenshot): crawl_data/domain/page_id/content_type.ext
        - Multiple files (component screenshots): crawl_data/domain/page_id/component_screenshots/filename.ext
        """
        # Create a hash of the URL for unique page identifier
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]  # Page identifier

        # Extract domain for organization
        domain = urlparse(url).netloc

        # Clean domain name for directory use
        clean_domain = domain.replace('www.', '').replace(':', '_')

        # File extension mapping based on ContentType
        extensions = {
            ContentType.HTML: '.html.gz' if self.compress else '.html',
            ContentType.CSS: '.css.gz' if self.compress else '.css',
            ContentType.JSON: '.json.gz' if self.compress else '.json',
            ContentType.SCREENSHOT: '.webp' if self.compress else '.png',
            ContentType.COMPONENT_SCREENSHOT: '.webp' if self.compress else '.png',
            ContentType.DOM_TREE: '.json.gz' if self.compress else '.json'
        }
        extension = extensions.get(content_type, '.txt')

        # Base page directory
        page_dir = self.base_path / clean_domain / url_hash

        # Component screenshots go in subdirectory (multiple files)
        if content_type == ContentType.COMPONENT_SCREENSHOT:
            filename = f"{filename_suffix}{extension}" if filename_suffix else f"component{extension}"
            file_path = page_dir / "component_screenshots" / filename
        # CSS files go in subdirectory (multiple files)
        elif content_type == ContentType.CSS:
            filename = f"{filename_suffix}{extension}" if filename_suffix else f"styles{extension}"
            file_path = page_dir / "css" / filename
        else:
            # Single files (HTML, DOM tree, screenshot) go directly in page directory
            filename = f"{content_type.value}{extension}"
            file_path = page_dir / filename

        file_path.parent.mkdir(parents=True, exist_ok=True)

        return file_path

    async def save_content(self, url: str, content, content_type: ContentType, filename_suffix: str = None) -> str:
        """Save content to file and return the file path

        Args:
            url: The URL being stored
            content: The content to store (str or bytes)
            content_type: ContentType enum
            filename_suffix: Optional suffix for filename (for component screenshots)

        Returns:
            File path as string, or None if save failed
        """
        file_path = self.get_file_path(url, content_type, filename_suffix)

        try:
            # Handle text content (HTML, CSS, JSON)
            if self._is_text_content(content_type):
                await self._save_text_content(file_path, content)
                return str(file_path)

            # Handle image content (screenshots)
            if self._is_image_content(content_type):
                await self._save_image_content(file_path, content)
                return str(file_path)

            # Handle other binary content
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            return str(file_path)

        except Exception as e:
            logger.error(f"Error saving content for {url}: {e}")
            return None

    async def _save_text_content(self, file_path: Path, content: str):
        """Save text content with optional compression"""
        if not self.compress:
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            return

        compressed_content = gzip.compress(content.encode('utf-8'))
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(compressed_content)

    async def _save_image_content(self, file_path: Path, content: bytes):
        """Save image content with optional WebP compression"""
        if not self.compress:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            return

        # Convert PNG to WebP for better compression
        image = Image.open(io.BytesIO(content))
        output = io.BytesIO()
        image.save(output, format='WEBP', quality=85, method=6)
        compressed_content = output.getvalue()
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(compressed_content)

    async def save_metadata(self, url: str, metadata: dict) -> str:
        """Save crawl metadata as JSON"""
        metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False)
        return await self.save_content(url, metadata_json, ContentType.JSON)

    async def save_page_metadata(self, url: str) -> str:
        """Save basic page metadata with URL mapping"""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        domain = urlparse(url).netloc.replace('www.', '').replace(':', '_')

        metadata = {
            'url': url,
            'url_hash': url_hash,
            'domain': domain,
            'crawled_at': datetime.now().isoformat()
        }

        # Save metadata.json in the page directory
        metadata_path = self.base_path / domain / url_hash / 'metadata.json'
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(metadata_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(metadata, indent=2, ensure_ascii=False))

        return str(metadata_path)

    def get_storage_stats(self):
        """Get storage statistics"""
        stats = {}
        for content_type in ['html', 'css', 'screenshot', 'logs']:
            type_path = self.base_path / content_type
            if type_path.exists():
                file_count = sum(1 for _ in type_path.rglob('*') if _.is_file())
                total_size = sum(f.stat().st_size for f in type_path.rglob('*') if f.is_file())
                stats[content_type] = {
                    'file_count': file_count,
                    'total_size_mb': round(total_size / (1024 * 1024), 2)
                }
            else:
                stats[content_type] = {'file_count': 0, 'total_size_mb': 0}

        return stats