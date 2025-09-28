#!/usr/bin/env python3
"""
DOM Component Screenshot Example
Demonstrates DOM tree extraction and component-level screenshot capture
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler import CrawlerBuilder

async def main():
    """DOM component extraction example"""
    print("🌳 DOM Component Screenshot Example")
    print("="*50)

    # URLs with rich HTML structure for component testing
    start_urls = [
        'https://httpbin.org/html',       # Simple HTML with basic structure
        'https://example.com',            # Standard website structure
    ]

    # Create crawler with DOM extraction enabled using new architecture
    crawler = (CrawlerBuilder(start_urls)
               .max_pages(3)
               .with_screenshots()
               .with_dom_extraction(capture_screenshots=True, max_depth=8)
               .build())

    # Run the crawl
    await crawler.crawl()

    print("\n📂 Output Structure:")
    print("- crawl_data/html/              # Full HTML content")
    print("- crawl_data/screenshot/        # Full page screenshots")
    print("- crawl_data/component_screenshots/  # Individual component screenshots")
    print("- crawl_data/dom_trees/         # DOM tree structure (JSON)")

    print("\n✅ DOM component extraction completed!")
    print("\nComponent screenshots captured for:")
    print("- header, nav, main, article, section")
    print("- aside, footer, .container, .content")
    print("- #header, #navigation, #main, #sidebar, #footer")

if __name__ == "__main__":
    asyncio.run(main())