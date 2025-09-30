import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


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