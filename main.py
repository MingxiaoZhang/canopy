#!/usr/bin/env python3
"""
Tarzan Web Crawler
A large-scale web crawler for extracting HTML, CSS, and screenshots
"""

import asyncio
import sys
from src.crawler import BasicCrawler

async def main():
    """Main entry point for the crawler"""
    # Example usage - testing with a site that has CSS
    start_urls = [
        'https://example.com',  # Has inline CSS
        # Add more URLs here
    ]

    # Create and run crawler
    crawler = BasicCrawler(start_urls, max_pages=10)
    await crawler.crawl()

    # Print storage statistics
    print("\nStorage Statistics:")
    stats = crawler.storage.get_storage_stats()
    for content_type, data in stats.items():
        print(f"  {content_type}: {data['file_count']} files, {data['total_size_mb']} MB")

if __name__ == "__main__":
    print("🌿 Tarzan Web Crawler Starting...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Crawler stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    print("✅ Crawling completed!")