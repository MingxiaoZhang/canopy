import time
import psutil
import asyncio
import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from pathlib import Path
import threading

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

@dataclass
class SystemMetrics:
    """System resource metrics"""
    cpu_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_percent: float = 0.0
    disk_used_gb: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    open_files: int = 0

@dataclass
class DomainMetrics:
    """Per-domain metrics"""
    domain: str = ""
    pages_crawled: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    errors: int = 0
    last_crawled: Optional[datetime] = None

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
            from urllib.parse import urlparse
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

class ProgressReporter:
    """Reports crawl progress and statistics"""

    def __init__(self, metrics_collector: MetricsCollector, report_interval: float = 30.0):
        self.metrics = metrics_collector
        self.report_interval = report_interval
        self.last_report_time = time.time()
        self.reporting_task = None

    async def start_reporting(self):
        """Start periodic progress reporting"""
        self.reporting_task = asyncio.create_task(self._reporting_loop())

    async def stop_reporting(self):
        """Stop progress reporting"""
        if self.reporting_task:
            self.reporting_task.cancel()
            try:
                await self.reporting_task
            except asyncio.CancelledError:
                pass

    async def _reporting_loop(self):
        """Main reporting loop"""
        try:
            while True:
                await asyncio.sleep(self.report_interval)
                self.print_progress_report()
                self.metrics.store_historical_snapshot()
        except asyncio.CancelledError:
            pass

    def print_progress_report(self):
        """Print a comprehensive progress report"""
        snapshot = self.metrics.get_current_snapshot()
        crawl_metrics = snapshot['crawl_metrics']
        system_metrics = snapshot['system_metrics']

        print(f"\n{'='*60}")
        print(f"📊 CRAWL PROGRESS REPORT - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")

        # Crawl Performance
        print(f"🌐 Crawl Performance:")
        print(f"  Pages crawled: {crawl_metrics['pages_crawled']}")
        print(f"  Pages/second: {crawl_metrics['pages_per_second']:.2f}")
        print(f"  Queue depth: {crawl_metrics['queue_depth']}")
        print(f"  Success rate: {crawl_metrics['success_rate']:.1f}%")
        print(f"  Avg response time: {crawl_metrics['avg_response_time']:.2f}s")
        print(f"  Duplicates skipped: {crawl_metrics['duplicates_skipped']}")
        print(f"  Errors: {crawl_metrics['errors_count']}")

        # Data Volume
        bytes_mb = crawl_metrics['bytes_downloaded'] / (1024 * 1024)
        print(f"\n💾 Data Volume:")
        print(f"  Downloaded: {bytes_mb:.2f} MB")

        # System Resources
        print(f"\n💻 System Resources:")
        print(f"  CPU: {system_metrics['cpu_percent']:.1f}%")
        print(f"  Memory: {system_metrics['memory_used_mb']:.0f} MB ({system_metrics['memory_percent']:.1f}%)")
        print(f"  Network sent: {system_metrics['network_sent_mb']:.2f} MB")
        print(f"  Network recv: {system_metrics['network_recv_mb']:.2f} MB")
        print(f"  Open files: {system_metrics['open_files']}")

        # Domain Breakdown
        domain_metrics = snapshot['domain_metrics']
        if domain_metrics:
            print(f"\n🌍 Domain Breakdown:")
            for domain, metrics in domain_metrics.items():
                print(f"  {domain}: {metrics['pages_crawled']} pages, "
                      f"{metrics['success_rate']:.1f}% success, "
                      f"{metrics['avg_response_time']:.2f}s avg")

    def get_final_report(self) -> Dict[str, Any]:
        """Generate final crawl report"""
        snapshot = self.metrics.get_current_snapshot()

        return {
            'final_snapshot': snapshot,
            'performance_summary': self._generate_performance_summary(),
            'domain_summary': self._generate_domain_summary(),
            'efficiency_metrics': self._generate_efficiency_metrics()
        }

    def _generate_performance_summary(self) -> Dict[str, Any]:
        """Generate performance summary"""
        crawl_metrics = self.metrics.crawl_metrics
        elapsed_time = time.time() - self.metrics.start_time

        return {
            'total_runtime_minutes': elapsed_time / 60,
            'pages_per_minute': (crawl_metrics.pages_crawled / elapsed_time) * 60 if elapsed_time > 0 else 0,
            'efficiency_score': crawl_metrics.success_rate,
            'data_throughput_mbps': (crawl_metrics.bytes_downloaded / elapsed_time / 1024 / 1024) if elapsed_time > 0 else 0
        }

    def _generate_domain_summary(self) -> List[Dict[str, Any]]:
        """Generate per-domain summary"""
        return [
            {
                'domain': domain,
                'pages_crawled': metrics.pages_crawled,
                'success_rate': metrics.success_rate,
                'avg_response_time': metrics.avg_response_time,
                'total_errors': metrics.errors
            }
            for domain, metrics in self.metrics.domain_metrics.items()
        ]

    def _generate_efficiency_metrics(self) -> Dict[str, Any]:
        """Generate efficiency metrics"""
        crawl_metrics = self.metrics.crawl_metrics

        total_urls_processed = crawl_metrics.pages_crawled + crawl_metrics.duplicates_skipped
        duplication_rate = (crawl_metrics.duplicates_skipped / total_urls_processed * 100) if total_urls_processed > 0 else 0

        return {
            'duplication_rate': duplication_rate,
            'error_rate': (crawl_metrics.errors_count / (crawl_metrics.pages_crawled + crawl_metrics.errors_count) * 100) if (crawl_metrics.pages_crawled + crawl_metrics.errors_count) > 0 else 0,
            'average_page_size_kb': (crawl_metrics.bytes_downloaded / crawl_metrics.pages_crawled / 1024) if crawl_metrics.pages_crawled > 0 else 0
        }

class LogManager:
    """Advanced logging management with structured output"""

    def __init__(self, log_dir: str = "crawl_data/logs", log_level: str = "INFO"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.setup_logging(log_level)

    def setup_logging(self, log_level: str):
        """Set up structured logging with multiple handlers"""
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )

        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))

        # Clear existing handlers
        root_logger.handlers.clear()

        # Console handler (simple format)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)

        # File handler for all logs (detailed format)
        all_logs_file = self.log_dir / f"crawler_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(all_logs_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)

        # Error file handler
        error_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(error_file)
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)

        # Performance file handler
        perf_file = self.log_dir / f"performance_{datetime.now().strftime('%Y%m%d')}.log"
        self.perf_handler = logging.FileHandler(perf_file)
        self.perf_logger = logging.getLogger('performance')
        self.perf_logger.setLevel(logging.INFO)
        self.perf_logger.addHandler(self.perf_handler)
        self.perf_logger.propagate = False

    def log_performance_event(self, event_type: str, **kwargs):
        """Log performance-related events"""
        event_data = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            **kwargs
        }
        self.perf_logger.info(json.dumps(event_data))

    def export_metrics_json(self, metrics_data: Dict[str, Any], filename: str = None):
        """Export metrics to JSON file"""
        if filename is None:
            filename = f"metrics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        export_path = self.log_dir / filename
        with open(export_path, 'w') as f:
            json.dump(metrics_data, f, indent=2, default=str)

        logging.info(f"Metrics exported to {export_path}")
        return export_path