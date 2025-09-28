# Tarzan Web Crawler

A large-scale web crawler built in Python for extracting HTML, CSS, and screenshots from websites.

## Features

- Asynchronous crawling with aiohttp
- HTML parsing and link extraction
- CSS file discovery and downloading
- Organized file storage with date-based structure
- Basic politeness controls (delays, same-domain crawling)
- Extensible architecture for future enhancements

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Project Structure

```
tarzan/
├── src/
│   ├── __init__.py
│   ├── crawler.py      # Main crawler logic
│   ├── parser.py       # HTML parsing and data extraction
│   └── storage.py      # File storage management
├── crawl_data/
│   ├── html/           # Stored HTML files
│   ├── css/            # Downloaded CSS files
│   ├── screenshots/    # Page screenshots (future)
│   └── logs/           # Crawler logs
├── main.py             # Entry point
├── requirements.txt    # Python dependencies
└── README.md
```

## Configuration

Edit `main.py` to configure:
- Starting URLs
- Maximum pages to crawl
- Other crawler settings

## Roadmap

- [ ] Screenshot capture with Playwright
- [ ] Redis-based queue system
- [ ] Rate limiting and robots.txt compliance
- [ ] Distributed crawling capabilities
- [ ] Web interface for monitoring
- [ ] Database integration for metadata