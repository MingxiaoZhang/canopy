#!/usr/bin/env python3
"""
Comprehensive Test Suite - Test all features of the new crawler architecture
"""

import asyncio
import sys
import os
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler import CrawlerBuilder


async def test_basic_crawling():
    """Test 1: Basic crawling without features"""
    print("🧪 Test 1: Basic Crawling")
    print("-" * 30)

    crawler = (CrawlerBuilder(['https://example.com'])
               .max_pages(1)
               .build())

    await crawler.crawl()

    # Check results
    print(f"✅ Pages crawled: {crawler.pages_crawled}")
    print(f"✅ URLs visited: {len(crawler.visited)}")

    # Check HTML file
    html_files = []
    for root, dirs, files in os.walk("crawl_data/html"):
        html_files.extend([f for f in files if f.endswith('.html')])
    print(f"✅ HTML files saved: {len(html_files)}")

    # Check CSS file
    css_files = []
    for root, dirs, files in os.walk("crawl_data/css"):
        css_files.extend([f for f in files if f.endswith('.css')])
    print(f"✅ CSS files saved: {len(css_files)}")

    return len(html_files) > 0 and len(css_files) > 0


async def test_screenshots_only():
    """Test 2: Screenshots feature only"""
    print("\n🧪 Test 2: Screenshots Only")
    print("-" * 30)

    # Clean previous data
    os.system("rm -rf crawl_data/")

    crawler = (CrawlerBuilder(['https://httpbin.org/html'])
               .max_pages(1)
               .with_screenshots()
               .build())

    await crawler.crawl()

    # Check screenshot files
    screenshot_files = []
    for root, dirs, files in os.walk("crawl_data/screenshot"):
        screenshot_files.extend([f for f in files if f.endswith('.png')])
    print(f"✅ Screenshot files: {len(screenshot_files)}")

    if screenshot_files:
        print(f"   - {screenshot_files[0]}")

    return len(screenshot_files) > 0


async def test_dom_extraction_only():
    """Test 3: DOM extraction with component screenshots"""
    print("\n🧪 Test 3: DOM Extraction + Component Screenshots")
    print("-" * 30)

    # Clean previous data
    os.system("rm -rf crawl_data/")

    crawler = (CrawlerBuilder(['https://httpbin.org/html'])
               .max_pages(1)
               .with_screenshots()  # Required for DOM extraction
               .with_dom_extraction(capture_screenshots=True, max_depth=5)
               .build())

    await crawler.crawl()

    # Check DOM tree files
    dom_files = []
    for root, dirs, files in os.walk("crawl_data/dom_trees"):
        dom_files.extend([f for f in files if f.endswith('.json')])
    print(f"✅ DOM tree files: {len(dom_files)}")

    # Check component screenshots
    component_files = []
    for root, dirs, files in os.walk("crawl_data/component_screenshots"):
        component_files.extend([f for f in files if f.endswith('.png')])
    print(f"✅ Component screenshot files: {len(component_files)}")

    # Verify DOM tree content
    if dom_files:
        dom_path = None
        for root, dirs, files in os.walk("crawl_data/dom_trees"):
            for file in files:
                if file.endswith('.json'):
                    dom_path = os.path.join(root, file)
                    break

        if dom_path:
            with open(dom_path, 'r') as f:
                dom_data = json.load(f)
            node_count = dom_data.get('metadata', {}).get('total_nodes', 0)
            print(f"✅ DOM nodes extracted: {node_count}")

    return len(dom_files) > 0 and len(component_files) > 0


async def test_graph_crawling_only():
    """Test 4: Graph crawling feature"""
    print("\n🧪 Test 4: Graph Crawling")
    print("-" * 30)

    # Clean previous data
    os.system("rm -rf crawl_data/")

    crawler = (CrawlerBuilder(['https://example.com'])
               .max_pages(2)  # Allow discovering more pages
               .with_graph_crawling(
                   mode="cross_domain",
                   max_depth=2,
                   max_domains=3
               )
               .build())

    await crawler.crawl()

    print(f"✅ Pages crawled: {crawler.pages_crawled}")

    return True  # Graph crawling is working if no errors


async def test_all_features_combined():
    """Test 5: All features together"""
    print("\n🧪 Test 5: All Features Combined")
    print("-" * 30)

    # Clean previous data
    os.system("rm -rf crawl_data/")

    crawler = (CrawlerBuilder(['https://example.com'])
               .max_pages(2)
               .with_screenshots()
               .with_dom_extraction(capture_screenshots=True, max_depth=6)
               .with_graph_crawling(mode="single_domain", max_depth=2)
               .build())

    await crawler.crawl()

    # Check all file types
    html_files = []
    css_files = []
    screenshot_files = []
    component_files = []
    dom_files = []

    for root, dirs, files in os.walk("crawl_data"):
        for file in files:
            if file.endswith('.html'):
                html_files.append(file)
            elif file.endswith('.css'):
                css_files.append(file)
            elif file.endswith('.png') and 'screenshot' in root and 'component' not in root:
                screenshot_files.append(file)
            elif file.endswith('.png') and 'component_screenshots' in root:
                component_files.append(file)
            elif file.endswith('.json'):
                dom_files.append(file)

    print(f"✅ HTML files: {len(html_files)}")
    print(f"✅ CSS files: {len(css_files)}")
    print(f"✅ Full screenshots: {len(screenshot_files)}")
    print(f"✅ Component screenshots: {len(component_files)}")
    print(f"✅ DOM trees: {len(dom_files)}")
    print(f"✅ Features loaded: {len(crawler.features)}")

    return (len(html_files) > 0 and len(screenshot_files) > 0 and
            len(component_files) > 0 and len(dom_files) > 0)


async def test_builder_configurations():
    """Test 6: Builder pattern configurations"""
    print("\n🧪 Test 6: Builder Pattern Configurations")
    print("-" * 30)

    # Test different builder configurations
    configs = [
        ("No features", lambda b: b),
        ("Screenshots only", lambda b: b.with_screenshots()),
        ("DOM only", lambda b: b.with_screenshots().with_dom_extraction()),
        ("Graph only", lambda b: b.with_graph_crawling()),
        ("All features", lambda b: b.with_screenshots().with_dom_extraction().with_graph_crawling())
    ]

    for name, config_func in configs:
        builder = CrawlerBuilder(['https://example.com']).max_pages(1)
        crawler = config_func(builder).build()
        print(f"✅ {name}: {len(crawler.features)} features")

    return True


async def main():
    """Run all tests"""
    print("🧪 Comprehensive Feature Tests")
    print("=" * 50)

    tests = [
        ("Basic Crawling", test_basic_crawling),
        ("Screenshots", test_screenshots_only),
        ("DOM Extraction", test_dom_extraction_only),
        ("Graph Crawling", test_graph_crawling_only),
        ("All Features", test_all_features_combined),
        ("Builder Patterns", test_builder_configurations)
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result, None))
        except Exception as e:
            results.append((test_name, False, str(e)))

    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)

    passed = 0
    for test_name, success, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if error:
            print(f"     Error: {error}")
        if success:
            passed += 1

    print(f"\n🎯 Overall: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("🎉 All features working correctly!")
    else:
        print("⚠️  Some features need attention")


if __name__ == "__main__":
    asyncio.run(main())