#!/usr/bin/env python3
"""
Test script for graph crawling modes
"""

import asyncio
from src.crawler import BasicCrawler
from src.graph_crawler import GraphCrawlConfig, CrawlMode

async def test_single_domain():
    """Test single domain crawling (traditional mode)"""
    print("🌐 Testing SINGLE_DOMAIN mode...")

    config = GraphCrawlConfig(
        mode=CrawlMode.SINGLE_DOMAIN,
        max_depth=2
    )

    crawler = BasicCrawler(
        start_urls=['https://httpbin.org/html'],
        max_pages=5,
        enable_monitoring=False,
        graph_config=config
    )

    await crawler.crawl()
    print("\n" + "="*50 + "\n")

async def test_cross_domain():
    """Test cross-domain crawling with limits"""
    print("🌍 Testing CROSS_DOMAIN mode...")

    config = GraphCrawlConfig(
        mode=CrawlMode.CROSS_DOMAIN,
        max_depth=2,
        max_domains=3,  # Limit to 3 domains
        min_domain_score=0.1
    )

    crawler = BasicCrawler(
        start_urls=['https://httpbin.org/links/3'],  # Page with external links
        max_pages=5,
        enable_monitoring=False,
        graph_config=config
    )

    await crawler.crawl()
    print("\n" + "="*50 + "\n")

async def test_whitelist_mode():
    """Test whitelist-based crawling"""
    print("📋 Testing WHITELIST mode...")

    config = GraphCrawlConfig(
        mode=CrawlMode.WHITELIST,
        max_depth=2,
        allowed_domains={'httpbin.org', 'example.com', 'jsonplaceholder.typicode.com'}
    )

    crawler = BasicCrawler(
        start_urls=['https://httpbin.org/html'],
        max_pages=5,
        enable_monitoring=False,
        graph_config=config
    )

    await crawler.crawl()
    print("\n" + "="*50 + "\n")

async def main():
    """Run all graph crawling tests"""
    print("🕸️ GRAPH CRAWLING MODE TESTS")
    print("="*60)

    # Test different modes
    await test_single_domain()
    await test_cross_domain()
    await test_whitelist_mode()

    print("✅ All graph crawling tests completed!")

if __name__ == "__main__":
    asyncio.run(main())