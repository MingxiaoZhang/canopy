"""
Crawl Result - Data structure for crawling results
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class CrawlResult:
    """Result of crawling a single URL"""
    url: str
    content: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    response_time: float = 0.0
    status_code: Optional[int] = None