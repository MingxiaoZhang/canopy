# Tarzan Web Crawler

A large-scale web crawler built in Python for extracting HTML, CSS, and screenshots from websites.

## Features

- Asynchronous crawling with aiohttp
- HTML parsing and link extraction
- CSS file discovery and downloading (external + inline)
- Screenshot capture with Playwright
- Organized file storage with date-based structure
- Basic politeness controls (delays, same-domain crawling)
- Docker support for easy deployment
- Extensible architecture for future enhancements

## Quick Start with Docker (Recommended)

```bash
# Build and run with docker-compose
docker-compose up --build

# Or with plain Docker
docker build -t tarzan-crawler .
docker run -v $(pwd)/crawl_data:/app/crawl_data tarzan-crawler
```

## Local Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install browser dependencies (Linux/Ubuntu)
sudo ./setup_browser.sh
# OR manually:
sudo apt-get install libnspr4 libnss3 libasound2
```

## Usage

### Docker (Recommended)
```bash
# Run crawler with data persistence
docker-compose up

# Run single crawl
docker run -v $(pwd)/crawl_data:/app/crawl_data tarzan-crawler
```

### Local
```bash
# Activate environment
source venv/bin/activate

# Run crawler
python main.py
```

## Configuration

Edit `main.py` to configure:
- Starting URLs
- Maximum pages to crawl
- Enable/disable screenshots
- Other crawler settings

```python
start_urls = ['https://example.com']
crawler = BasicCrawler(start_urls, max_pages=10, enable_screenshots=True)
```

## Project Structure

```
tarzan/
├── src/
│   ├── crawler.py      # Main crawler logic
│   ├── parser.py       # HTML parsing and data extraction
│   ├── screenshot.py   # Screenshot capture with Playwright
│   └── storage.py      # File storage management
├── crawl_data/
│   ├── html/           # Stored HTML files
│   ├── css/            # Downloaded CSS files
│   ├── screenshots/    # Page screenshots
│   └── logs/           # Crawler logs
├── Dockerfile          # Docker container setup
├── docker-compose.yml  # Docker compose configuration
├── main.py             # Entry point
└── requirements.txt    # Python dependencies
```

## Output Structure

Crawled data is organized by date and domain:
```
crawl_data/
├── html/2025/09/27/example.com_[hash].html
├── css/2025/09/27/example.com_[hash].css
└── screenshots/2025/09/27/example.com_[hash].png
```

## Docker Benefits

- ✅ No browser dependency issues
- ✅ Consistent environment
- ✅ Easy deployment anywhere
- ✅ Resource management
- ✅ Ready for scaling

## Roadmap

- [ ] Rate limiting and robots.txt compliance
- [ ] Enhanced error handling and retry mechanisms
- [ ] Redis-based queue system for distributed crawling
- [ ] Web interface for monitoring
- [ ] Database integration for metadata
- [ ] Multiple viewport screenshot capture

## Development

```bash
# Local development
source venv/bin/activate
python main.py

# Docker development
docker-compose up --build

# View logs
docker-compose logs -f
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with Docker
5. Submit a pull request