import os
import aiofiles
from pathlib import Path
import hashlib
from datetime import datetime
from urllib.parse import urlparse

class FileStorage:
    def __init__(self, base_path='crawl_data'):
        self.base_path = Path(base_path)
        self.setup_directories()

    def setup_directories(self):
        """Create necessary directory structure"""
        for subdir in ['html', 'css', 'screenshot', 'logs']:
            (self.base_path / subdir).mkdir(parents=True, exist_ok=True)

    def get_file_path(self, url, content_type='html'):
        """Generate a file path for storing content"""
        # Create a hash of the URL for filename
        url_hash = hashlib.md5(url.encode()).hexdigest()

        # Extract domain for organization
        domain = urlparse(url).netloc

        # Date-based directory structure
        date_str = datetime.now().strftime('%Y/%m/%d')

        # File extension mapping
        extensions = {
            'html': '.html',
            'css': '.css',
            'screenshot': '.png',
            'json': '.json'
        }
        extension = extensions.get(content_type, '.txt')

        # Construct filename with domain prefix
        filename = f"{domain}_{url_hash}{extension}"

        # Full path
        file_path = self.base_path / content_type / date_str / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        return file_path

    async def save_content(self, url, content, content_type='html'):
        """Save content to file and return the file path"""
        file_path = self.get_file_path(url, content_type)

        try:
            if content_type in ['html', 'css', 'json']:
                # Text content
                async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                    await f.write(content)
            else:
                # Binary content (screenshots, etc.)
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(content)

            return str(file_path)
        except Exception as e:
            print(f"Error saving content for {url}: {e}")
            return None

    async def save_metadata(self, url, metadata):
        """Save crawl metadata as JSON"""
        import json
        metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False)
        return await self.save_content(url, metadata_json, 'json')

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