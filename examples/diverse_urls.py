#!/usr/bin/env python3
"""
Diverse URLs crawling example
Demonstrates crawling different types of websites and content
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler import CrawlerBuilder

async def main():
    """Diverse URL types crawling example using new architecture"""
    print("🌍 Diverse URLs Crawling Example (New Architecture)")
    print("="*50)

    # Different types of URLs to test various scenarios
    start_urls = [
        'https://httpbin.org/html',              # Simple HTML test page
        'https://httpbin.org/json',              # JSON API endpoint
        'https://example.com',                   # Standard website
        'https://httpbin.org/status/200',        # Status code endpoint
        'https://httpbin.org/redirect/2',        # Redirect test
        'https://httpbin.org/robots.txt',        # Robots.txt file
    ]

    # Create basic crawler for diverse content types using new architecture
    crawler = (CrawlerBuilder(start_urls)
               .max_pages(8)
               .with_screenshots()
               .build())

    # Run the crawl
    await crawler.crawl()

    print("\n✅ Diverse URLs crawling example completed!")

if __name__ == "__main__":
    asyncio.run(main())