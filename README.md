# Canopy Web Crawler

A large-scale web crawler built in Python with a modular architecture for extracting HTML, CSS, screenshots, and DOM structures from websites.

## ✨ Features

### Core Capabilities
- **Asynchronous crawling** with aiohttp for high performance
- **Modular architecture** with composable features using builder pattern
- **HTML parsing** and intelligent link extraction
- **CSS discovery** and downloading (external + inline)
- **Screenshot capture** with Playwright browser automation
- **DOM tree extraction** with component-level screenshots
- **Graph-based crawling** with intelligent link prioritization

### Crawling Modes
- **Single Domain**: Crawl within starting domains only
- **Cross Domain**: Follow links across domains with limits
- **Whitelist**: Only crawl specified trusted domains
- **Graph Mode**: Intelligent crawling with link prioritization

### Architecture
- **Builder Pattern**: Fluent API for configuring crawler features
- **Feature Composition**: Mix and match screenshots, DOM extraction, graph crawling
- **Organized Storage**: Date-based file structure with domain organization
- **Error Handling**: Comprehensive error handling and rate limiting
- **Docker Support**: Containerized deployment for consistency

## 🚀 Quick Start

### Using the New Builder API

```python
from src.crawler import CrawlerBuilder

# Basic crawling
crawler = (CrawlerBuilder(['https://example.com'])
           .max_pages(10)
           .build())

# Advanced crawling with all features
crawler = (CrawlerBuilder(['https://example.com'])
           .max_pages(20)
           .with_screenshots()
           .with_dom_extraction(capture_screenshots=True)
           .with_graph_crawling(
               mode="cross_domain",
               max_depth=3,
               max_domains=5
           )
           .build())

await crawler.crawl()
```

### Docker (Recommended)

```bash
# Build and run with docker-compose
docker-compose up --build

# Or with plain Docker
docker build -t canopy-crawler .
docker run -v $(pwd)/crawl_data:/app/crawl_data canopy-crawler
```

### Local Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install browser dependencies (Linux/Ubuntu)
sudo ./setup_browser.sh
```

## 📖 Usage Examples

### Basic Crawling
```bash
# Run main crawler
python main.py
```

### Graph Crawling Examples
```bash
# Run all graph crawling examples
python examples/graph_crawling.py

# DOM component extraction
python examples/dom_components.py
```

### Builder Pattern Examples

```python
# Screenshots only
crawler = (CrawlerBuilder(['https://httpbin.org/links/3'])
           .max_pages(5)
           .with_screenshots()
           .build())

# DOM extraction with component screenshots
crawler = (CrawlerBuilder(['https://example.com'])
           .max_pages(10)
           .with_dom_extraction(
               max_depth=8,
               capture_screenshots=True
           )
           .build())

# Advanced graph crawling
crawler = (CrawlerBuilder(['https://httpbin.org/links/5'])
           .max_pages(15)
           .with_graph_crawling(
               mode="cross_domain",
               max_depth=2,
               max_domains=3,
               blocked_domains={'spam-domain.com'},
               priority_domains={'example.com'}
           )
           .build())
```

## 🏗️ Architecture

### Modular Directory Structure

```
src/
├── crawler/                    # Core crawler logic
│   ├── base.py                # BaseCrawler - core functionality
│   ├── builder.py             # CrawlerBuilder - fluent API
│   ├── result.py              # CrawlResult - data structures
│   └── __init__.py
├── features/                   # Composable feature modules
│   ├── base.py                # Base feature interface
│   ├── screenshot_feature.py  # Screenshot capture
│   ├── dom_extraction_feature.py  # DOM tree extraction
│   ├── graph_crawling_feature.py  # Graph-based crawling
│   └── __init__.py
├── utils/                      # Utility functions
│   ├── parser.py              # HTML parsing utilities
│   ├── graph_crawler.py       # Graph algorithms
│   ├── dom_tree.py            # DOM tree utilities
│   ├── rate_limiter.py        # Rate limiting
│   ├── error_handler.py       # Error handling
│   ├── deduplication.py       # Duplicate detection
│   └── __init__.py
├── storage/                    # Storage and persistence
│   ├── storage.py             # File storage management
│   └── __init__.py
├── monitoring/                 # Monitoring and observability
│   ├── monitoring.py          # Crawler monitoring
│   └── __init__.py
└── crawler.py                 # Main entry point
```

### Feature Composition

Features are composable modules that can be mixed and matched:

```python
# Any combination of features
crawler = (CrawlerBuilder(urls)
           .with_screenshots(headless=True)           # Optional
           .with_dom_extraction(max_depth=8)          # Optional
           .with_graph_crawling(mode="whitelist")     # Optional
           .build())
```

Each feature has standardized lifecycle hooks:
- `initialize()` - Setup feature
- `before_crawl()` - Pre-crawling setup
- `process_url()` - Process each URL
- `finalize()` - Cleanup resources

## 📁 Output Structure

Crawled data is organized by date and domain:

```
crawl_data/
├── html/2025/09/27/
│   └── example.com_[hash].html         # Full HTML content
├── css/2025/09/27/
│   └── example.com_[hash].css          # Extracted CSS
├── screenshot/2025/09/27/
│   └── example.com_[hash].png          # Full page screenshots
├── component_screenshots/2025/09/27/
│   ├── example.com_[hash]_header.png   # Component screenshots
│   ├── example.com_[hash]_nav.png
│   └── example.com_[hash]_main.png
└── dom_trees/2025/09/27/
    └── example.com_[hash]_dom_tree.json # DOM structure
```

## ⚙️ Configuration

### Builder Pattern Configuration

```python
# Configure individual features
crawler = (CrawlerBuilder(['https://example.com'])
           .max_pages(50)
           .with_screenshots(
               headless=True,
               viewport_width=1920,
               viewport_height=1080
           )
           .with_dom_extraction(
               max_depth=10,
               capture_screenshots=True
           )
           .with_graph_crawling(
               mode="cross_domain",
               max_depth=3,
               max_domains=10,
               allowed_domains={'example.com', 'trusted.com'},
               blocked_domains={'spam.com'},
               priority_domains={'example.com'}
           )
           .build())
```

### Graph Crawling Modes

1. **Single Domain**: `mode="single_domain"`
   - Only crawl within starting domains
   - Safest option for focused crawling

2. **Cross Domain**: `mode="cross_domain"`
   - Follow links across domains with limits
   - Intelligent domain scoring and prioritization

3. **Whitelist**: `mode="whitelist"`
   - Only crawl specified trusted domains
   - Requires `allowed_domains` parameter

## 🐳 Docker Benefits

- ✅ No browser dependency issues
- ✅ Consistent environment across platforms
- ✅ Easy deployment anywhere
- ✅ Resource management and isolation
- ✅ Ready for horizontal scaling

## 🔄 Migration from Old Architecture

If you have code using the old `BasicCrawler`, here's how to migrate:

```python
# Old way
crawler = BasicCrawler(urls, max_pages=10, enable_screenshots=True)
await crawler.crawl()

# New way
crawler = (CrawlerBuilder(urls)
           .max_pages(10)
           .with_screenshots()
           .build())
await crawler.crawl()
```

## 🛠️ Development

### Local Development
```bash
# Activate environment
source venv/bin/activate

# Run crawler
python main.py

# Run specific examples
python examples/graph_crawling.py
python examples/dom_components.py
```

### Docker Development
```bash
# Development with live reload
docker-compose up --build

# View logs
docker-compose logs -f

# Run specific example in container
docker run canopy-crawler python examples/graph_crawling.py
```

### Testing
```bash
# Run tests
python -m pytest tests/

# Test specific feature
python tests/test_graph_crawling.py
```

## 🗺️ Roadmap

### Completed ✅
- [x] Modular architecture with builder pattern
- [x] Feature composition system
- [x] Graph-based crawling with link prioritization
- [x] DOM tree extraction with component screenshots
- [x] Organized directory structure
- [x] Comprehensive error handling and rate limiting

### Planned 🚧
- [ ] Redis-based distributed queue system
- [ ] Web interface for monitoring and control
- [ ] Database integration for metadata storage
- [ ] REST API for programmatic control
- [ ] Multiple viewport screenshot capture
- [ ] Content analysis and classification
- [ ] Kubernetes deployment configs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the modular architecture
4. Add tests for new features
5. Test with Docker (`docker-compose up --build`)
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Playwright](https://playwright.dev/) for browser automation
- Uses [aiohttp](https://aiohttp.readthedocs.io/) for async HTTP requests
- Powered by [BeautifulSoup](https://beautiful-soup-4.readthedocs.io/) for HTML parsing