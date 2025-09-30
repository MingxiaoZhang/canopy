from dataclasses import dataclass


@dataclass
class CrawlMetrics:
    """Core crawling metrics"""
    pages_crawled: int = 0
    pages_per_second: float = 0.0
    queue_depth: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    bytes_downloaded: int = 0
    errors_count: int = 0
    duplicates_skipped: int = 0