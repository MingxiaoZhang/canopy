#!/usr/bin/env python3
"""
Test the graph crawler with diverse websites
"""

import asyncio
import sys
from src.crawler import CrawlerBuilder

async def test_websites():
    """Test graph crawler with various websites"""

    # Test with diverse real-world websites
    test_urls = [
        'https://example.com',           # Simple static site
        'https://httpbin.org/html',      # Testing site with HTML
        'https://python.org',            # Large site with many links
    ]

    print("🕸️ Testing Graph Crawler with Multiple Websites")
    print("=" * 60)

    # Create crawler with graph crawling, screenshots, and DOM extraction
    crawler = (CrawlerBuilder(test_urls)
               .max_pages(15)                  # Crawl up to 15 pages total
               .with_screenshots()              # Capture screenshots
               .with_dom_extraction(            # Extract DOM structure
                   max_depth=8,
                   capture_screenshots=True     # Capture component screenshots
               )
               .with_graph_crawling(            # Graph-based crawling
                   mode="cross_domain",
                   max_depth=2,                 # Follow links 2 levels deep
                   max_domains=4                # Limit to 4 domains
               )
               .build())

    print(f"\nStarting URLs: {test_urls}")
    print(f"Max pages: 15")
    print(f"Graph mode: cross_domain")
    print(f"Max depth: 2")
    print(f"Max domains: 4")
    print("-" * 60)

    await crawler.crawl()

    print(f"\n✅ Crawling completed!")
    print(f"📊 Total pages crawled: {crawler.pages_crawled}")

if __name__ == "__main__":
    try:
        asyncio.run(test_websites())
    except KeyboardInterrupt:
        print("\n🛑 Crawler stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)