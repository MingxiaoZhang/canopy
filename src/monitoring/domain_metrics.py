from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class DomainMetrics:
    """Per-domain metrics"""
    domain: str = ""
    pages_crawled: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    errors: int = 0
    last_crawled: Optional[datetime] = None