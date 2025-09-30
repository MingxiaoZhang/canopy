import time
import asyncio
from datetime import datetime
from typing import Dict, List, Any
from .metrics_collector import MetricsCollector


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