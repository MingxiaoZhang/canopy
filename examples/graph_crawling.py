#!/usr/bin/env python3
"""
Graph crawling example
Demonstrates different graph crawling modes for link discovery
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler import CrawlerBuilder

async def single_domain_example():
    """Example: Crawl within a single domain using new architecture"""
    print("🌐 Single Domain Crawling Example (New Architecture)")
    print("-" * 50)

    crawler = (CrawlerBuilder(['https://httpbin.org/links/3'])
               .max_pages(5)
               .with_graph_crawling(
                   mode="single_domain",
                   max_depth=2
               )
               .build())

    await crawler.crawl()

async def cross_domain_example():
    """Example: Discover and crawl across multiple domains using new architecture"""
    print("\n🌍 Cross-Domain Discovery Example (New Architecture)")
    print("-" * 50)

    crawler = (CrawlerBuilder(['https://httpbin.org/links/5'])
               .max_pages(8)
               .with_graph_crawling(
                   mode="cross_domain",
                   max_depth=2,
                   max_domains=3
               )
               .build())

    await crawler.crawl()

async def whitelist_example():
    """Example: Crawl only specified trusted domains using new architecture"""
    print("\n📋 Whitelist Domain Example (New Architecture)")
    print("-" * 50)

    allowed_domains = {'httpbin.org', 'example.com', 'jsonplaceholder.typicode.com'}

    crawler = (CrawlerBuilder(['https://httpbin.org/html'])
               .max_pages(5)
               .with_graph_crawling(
                   mode="whitelist",
                   max_depth=2,
                   allowed_domains=allowed_domains
               )
               .build())

    await crawler.crawl()

async def advanced_graph_example():
    """Example: Advanced graph crawling with multiple features"""
    print("\n🚀 Advanced Graph Crawling with All Features (New Architecture)")
    print("-" * 60)

    crawler = (CrawlerBuilder(['https://example.com'])
               .max_pages(6)
               .with_screenshots()
               .with_dom_extraction(capture_screenshots=True)
               .with_graph_crawling(
                   mode="cross_domain",
                   max_depth=3,
                   max_domains=5,
                   blocked_domains={'spam-domain.com'},
                   priority_domains={'example.com'}
               )
               .build())

    await crawler.crawl()

async def main():
    """Run graph crawling examples using new architecture"""
    print("🕸️ GRAPH CRAWLING EXAMPLES (New Architecture)")
    print("=" * 70)

    # Run different crawling mode examples
    await single_domain_example()
    await cross_domain_example()
    await whitelist_example()
    await advanced_graph_example()

    print("\n✅ All graph crawling examples completed!")

if __name__ == "__main__":
    asyncio.run(main())