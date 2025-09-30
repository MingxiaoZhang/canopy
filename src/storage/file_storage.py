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

    def get_file_path(self, url: str, content_type: ContentType) -> Path:
        """Generate a file path for storing content organized by website

        Args:
            url: The URL being stored
            content_type: ContentType enum

        Returns:
            Path object for the file
        """
        # Create a hash of the URL for filename
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]  # Shorter hash

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

        # Construct filename with timestamp for uniqueness
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{url_hash}_{timestamp}{extension}"

        # Website-based directory structure: crawl_data/domain/content_type/
        file_path = self.base_path / clean_domain / content_type.value / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        return file_path

    async def save_content(self, url: str, content, content_type: ContentType) -> str:
        """Save content to file and return the file path

        Args:
            url: The URL being stored
            content: The content to store (str or bytes)
            content_type: ContentType enum

        Returns:
            File path as string, or None if save failed
        """
        file_path = self.get_file_path(url, content_type)

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