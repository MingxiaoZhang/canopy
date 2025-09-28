#!/usr/bin/env python3
"""
New Crawler Architecture Examples
Demonstrates the clean, composable crawler with builder pattern
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler import CrawlerBuilder


async def basic_example():
    """Example 1: Basic crawling with HTML and CSS extraction"""
    print("📝 Example 1: Basic Crawling")
    print("-" * 30)

    crawler = (CrawlerBuilder(['https://example.com'])
               .max_pages(2)
               .build())

    await crawler.crawl()
    print(f"✅ Completed: {crawler.pages_crawled} pages\n")


async def screenshot_example():
    """Example 2: Web page screenshots"""
    print("📸 Example 2: Screenshot Capture")
    print("-" * 30)

    crawler = (CrawlerBuilder(['https://httpbin.org/html'])
               .max_pages(1)
               .with_screenshots()
               .build())

    await crawler.crawl()
    print(f"✅ Screenshots saved to crawl_data/screenshot/\n")


async def dom_extraction_example():
    """Example 3: DOM tree extraction with component screenshots"""
    print("🌳 Example 3: DOM Extraction")
    print("-" * 30)

    crawler = (CrawlerBuilder(['https://httpbin.org/html'])
               .max_pages(1)
               .with_screenshots()  # Required for DOM extraction
               .with_dom_extraction(
                   capture_screenshots=True,
                   max_depth=8
               )
               .build())

    await crawler.crawl()
    print(f"✅ DOM trees saved to crawl_data/dom_trees/")
    print(f"✅ Component screenshots saved to crawl_data/component_screenshots/\n")


async def graph_crawling_example():
    """Example 4: Intelligent graph-based crawling"""
    print("🕸️ Example 4: Graph Crawling")
    print("-" * 30)

    crawler = (CrawlerBuilder(['https://example.com'])
               .max_pages(3)
               .with_graph_crawling(
                   mode="cross_domain",
                   max_depth=2,
                   max_domains=5
               )
               .build())

    await crawler.crawl()
    print(f"✅ Graph crawling completed\n")


async def full_featured_example():
    """Example 5: All features combined"""
    print("🚀 Example 5: Full Featured Crawler")
    print("-" * 30)

    crawler = (CrawlerBuilder(['https://example.com'])
               .max_pages(2)
               .with_screenshots()
               .with_dom_extraction(capture_screenshots=True)
               .with_graph_crawling(mode="single_domain")
               .build())

    await crawler.crawl()
    print(f"✅ Full crawl completed with {len(crawler.features)} features")
    print(f"✅ Check crawl_data/ for all extracted content\n")


async def main():
    """Run all examples"""
    print("🧪 New Crawler Architecture Examples")
    print("=" * 50)

    examples = [
        basic_example,
        screenshot_example,
        dom_extraction_example,
        graph_crawling_example,
        full_featured_example
    ]

    for i, example in enumerate(examples, 1):
        # Clean data between examples
        if i > 1:
            os.system("rm -rf crawl_data/")

        await example()

    print("🎉 All examples completed!")
    print("📂 Final results saved in crawl_data/")


if __name__ == "__main__":
    asyncio.run(main())