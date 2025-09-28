#!/usr/bin/env python3
"""
Basic web crawling example
Demonstrates simple URL list crawling with all features enabled
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler import CrawlerBuilder

async def main():
    """Basic crawling example using new architecture"""
    print("🌿 Basic Web Crawling Example (New Architecture)")
    print("="*50)

    # Simple URL list crawling
    start_urls = [
        'https://httpbin.org/html',
        'https://example.com',
    ]

    # Create basic crawler with screenshots using new architecture
    crawler = (CrawlerBuilder(start_urls)
               .max_pages(5)
               .with_screenshots()
               .build())

    # Run the crawl
    await crawler.crawl()

    print("\n✅ Basic crawling example completed!")

if __name__ == "__main__":
    asyncio.run(main())