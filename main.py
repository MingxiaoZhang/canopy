#!/usr/bin/env python3
"""
Canopy Web Crawler
A large-scale web crawler for extracting HTML, CSS, and screenshots
"""

import asyncio
import sys
from src.crawler import CrawlerBuilder

async def main():
    """Main entry point for the crawler using new architecture"""
    start_urls = [
        'https://httpbin.org/links/3',  # Page with links to test graph crawling
    ]

    # Create and run crawler with new architecture
    crawler = (CrawlerBuilder(start_urls)
               .max_pages(10)
               .with_screenshots()
               .with_dom_extraction()
               .with_graph_crawling(mode="cross_domain", max_depth=2)
               .build())

    await crawler.crawl()

    print(f"\n✅ Crawled {crawler.pages_crawled} pages successfully!")

if __name__ == "__main__":
    print("🌿 Canopy Web Crawler Starting...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Crawler stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    print("✅ Crawling completed!")