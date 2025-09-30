import time
import psutil
import logging
import threading
from datetime import datetime
from dataclasses import asdict
from typing import Dict, Optional, Any
from collections import deque
from urllib.parse import urlparse
from .crawl_metrics import CrawlMetrics
from .system_metrics import SystemMetrics
from .domain_metrics import DomainMetrics


class MetricsCollector:
    """Collects and aggregates metrics from various sources"""

    def __init__(self, collection_interval: float = 5.0):
        self.collection_interval = collection_interval
        self.start_time = time.time()

        # Metrics storage
        self.crawl_metrics = CrawlMetrics()
        self.system_metrics = SystemMetrics()
        self.domain_metrics: Dict[str, DomainMetrics] = {}

        # Historical data (keep last 100 data points)
        self.metrics_history: deque = deque(maxlen=100)

        # Network tracking
        self.initial_network = psutil.net_io_counters()

        # Performance tracking
        self.response_times: deque = deque(maxlen=100)
        self.crawl_events: deque = deque(maxlen=1000)

        # Thread-safe locks
        self._lock = threading.Lock()

    def record_page_crawled(self, url: str, response_time: float, status_code: int, content_length: int = 0):
        """Record a successful page crawl"""
        with self._lock:
            domain = self._extract_domain(url)
            now = datetime.now()

            # Update crawl metrics
            self.crawl_metrics.pages_crawled += 1
            self.crawl_metrics.bytes_downloaded += content_length
            self.response_times.append(response_time)

            # Update domain metrics
            if domain not in self.domain_metrics:
                self.domain_metrics[domain] = DomainMetrics(domain=domain)

            domain_metric = self.domain_metrics[domain]
            domain_metric.pages_crawled += 1
            domain_metric.last_crawled = now

            # Record crawl event
            self.crawl_events.append({
                'timestamp': now,
                'url': url,
                'domain': domain,
                'response_time': response_time,
                'status_code': status_code,
                'content_length': content_length
            })

            # Update calculated metrics
            self._update_calculated_metrics()

    def record_error(self, url: str, error_type: str, status_code: Optional[int] = None):
        """Record a crawl error"""
        with self._lock:
            domain = self._extract_domain(url)

            self.crawl_metrics.errors_count += 1

            if domain in self.domain_metrics:
                self.domain_metrics[domain].errors += 1

            self._update_calculated_metrics()

    def record_duplicate_skipped(self, url: str):
        """Record a duplicate URL that was skipped"""
        with self._lock:
            self.crawl_metrics.duplicates_skipped += 1

    def update_queue_depth(self, depth: int):
        """Update current crawl queue depth"""
        with self._lock:
            self.crawl_metrics.queue_depth = depth

    def collect_system_metrics(self):
        """Collect current system resource metrics"""
        try:
            # CPU and Memory
            self.system_metrics.cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            self.system_metrics.memory_used_mb = memory.used / (1024 * 1024)
            self.system_metrics.memory_percent = memory.percent

            # Disk usage for current directory
            disk = psutil.disk_usage('.')
            self.system_metrics.disk_used_gb = disk.used / (1024**3)

            # Network I/O
            network = psutil.net_io_counters()
            self.system_metrics.network_sent_mb = (network.bytes_sent - self.initial_network.bytes_sent) / (1024 * 1024)
            self.system_metrics.network_recv_mb = (network.bytes_recv - self.initial_network.bytes_recv) / (1024 * 1024)

            # Open files
            try:
                process = psutil.Process()
                self.system_metrics.open_files = process.num_fds() if hasattr(process, 'num_fds') else len(process.open_files())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.system_metrics.open_files = 0

        except Exception as e:
            logging.warning(f"Failed to collect system metrics: {e}")

    def _update_calculated_metrics(self):
        """Update calculated metrics like rates and averages"""
        elapsed_time = time.time() - self.start_time

        # Pages per second
        if elapsed_time > 0:
            self.crawl_metrics.pages_per_second = self.crawl_metrics.pages_crawled / elapsed_time

        # Success rate
        total_attempts = self.crawl_metrics.pages_crawled + self.crawl_metrics.errors_count
        if total_attempts > 0:
            self.crawl_metrics.success_rate = (self.crawl_metrics.pages_crawled / total_attempts) * 100

        # Average response time
        if self.response_times:
            self.crawl_metrics.avg_response_time = sum(self.response_times) / len(self.response_times)

        # Update domain success rates
        for domain_metric in self.domain_metrics.values():
            total_domain_attempts = domain_metric.pages_crawled + domain_metric.errors
            if total_domain_attempts > 0:
                domain_metric.success_rate = (domain_metric.pages_crawled / total_domain_attempts) * 100

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            return urlparse(url).netloc.lower()
        except:
            return "unknown"

    def get_current_snapshot(self) -> Dict[str, Any]:
        """Get current metrics snapshot"""
        with self._lock:
            self.collect_system_metrics()

            return {
                'timestamp': datetime.now().isoformat(),
                'uptime_seconds': time.time() - self.start_time,
                'crawl_metrics': asdict(self.crawl_metrics),
                'system_metrics': asdict(self.system_metrics),
                'domain_metrics': {
                    domain: asdict(metrics) for domain, metrics in self.domain_metrics.items()
                }
            }

    def store_historical_snapshot(self):
        """Store current metrics in historical data"""
        snapshot = self.get_current_snapshot()
        self.metrics_history.append(snapshot)