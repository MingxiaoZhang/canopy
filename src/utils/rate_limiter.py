import asyncio
import time
import logging
from collections import defaultdict, deque
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import Dict, Optional
import aiohttp
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)

@dataclass
class DomainSettings:
    """Settings for a specific domain"""
    crawl_delay: float = 1.0  # seconds between requests
    max_concurrent: int = 1   # max concurrent requests
    last_request_time: float = 0.0
    blocked: bool = False
    robots_txt: Optional[str] = None
    user_agent_allowed: bool = True

class RateLimiter:
    def __init__(self, default_delay=1.0, max_concurrent_per_domain=1, user_agent="CanopyCrawler/1.0"):
        self.default_delay = default_delay
        self.max_concurrent_per_domain = max_concurrent_per_domain
        self.user_agent = user_agent

        # Per-domain settings and state
        self.domain_settings: Dict[str, DomainSettings] = defaultdict(
            lambda: DomainSettings(
                crawl_delay=self.default_delay,
                max_concurrent=self.max_concurrent_per_domain
            )
        )

        # Track concurrent requests per domain
        self.active_requests: Dict[str, int] = defaultdict(int)

        # Request history for adaptive rate limiting
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10))

        # Locks for thread safety
        self.domain_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        return urlparse(url).netloc.lower()

    async def can_crawl_url(self, url: str) -> tuple[bool, str]:
        """
        Check if URL can be crawled based on robots.txt

        Returns:
            (can_crawl: bool, reason: str)
        """
        domain = self.get_domain(url)
        settings = self.domain_settings[domain]

        if settings.blocked:
            return False, f"Domain {domain} is blocked"

        if not settings.user_agent_allowed:
            return False, f"User agent {self.user_agent} not allowed by robots.txt"

        # Check robots.txt if available
        if settings.robots_txt:
            try:
                rp = RobotFileParser()
                rp.set_url(f"http://{domain}/robots.txt")
                rp.read()

                if not rp.can_fetch(self.user_agent, url):
                    return False, f"URL blocked by robots.txt"

            except Exception as e:
                logger.warning(f"Could not parse robots.txt for {domain}: {e}")

        return True, "OK"

    async def fetch_robots_txt(self, session: aiohttp.ClientSession, domain: str) -> Optional[str]:
        """Fetch and parse robots.txt for a domain"""
        robots_url = f"https://{domain}/robots.txt"

        try:
            async with session.get(robots_url, timeout=10) as response:
                if response.status == 200:
                    robots_content = await response.text()
                    return robots_content
        except Exception as e:
            logger.warning(f"Could not fetch robots.txt for {domain}: {e}")

        return None

    def parse_robots_txt(self, domain: str, robots_content: str):
        """Parse robots.txt and update domain settings"""
        if not robots_content:
            return

        settings = self.domain_settings[domain]
        settings.robots_txt = robots_content

        try:
            # Parse crawl-delay
            lines = robots_content.lower().split('\n')
            current_user_agent = None

            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if line.startswith('user-agent:'):
                    current_user_agent = line.split(':', 1)[1].strip()

                elif line.startswith('crawl-delay:') and current_user_agent:
                    if current_user_agent == '*' or self.user_agent.lower() in current_user_agent:
                        try:
                            delay = float(line.split(':', 1)[1].strip())
                            settings.crawl_delay = max(delay, self.default_delay)
                            logger.info(f"Set crawl delay for {domain}: {settings.crawl_delay}s")
                        except ValueError:
                            pass

                elif line.startswith('disallow:') and current_user_agent:
                    if current_user_agent == '*' or self.user_agent.lower() in current_user_agent:
                        disallowed_path = line.split(':', 1)[1].strip()
                        if disallowed_path == '/':  # Completely blocked
                            settings.user_agent_allowed = False
                            logger.warning(f"Domain {domain} disallows crawling for {self.user_agent}")

        except Exception as e:
            logger.error(f"Error parsing robots.txt for {domain}: {e}")

    async def initialize_domain(self, session: aiohttp.ClientSession, domain: str):
        """Initialize domain settings by fetching robots.txt"""
        if domain in self.domain_settings and self.domain_settings[domain].robots_txt is not None:
            return  # Already initialized

        logger.debug(f"Initializing domain settings for {domain}")
        robots_content = await self.fetch_robots_txt(session, domain)

        if robots_content:
            self.parse_robots_txt(domain, robots_content)
        else:
            # Set default settings if no robots.txt
            self.domain_settings[domain].robots_txt = ""

    async def wait_for_rate_limit(self, url: str):
        """Wait for rate limit before making request"""
        domain = self.get_domain(url)
        settings = self.domain_settings[domain]

        async with self.domain_locks[domain]:
            # Wait for concurrent request limit
            while self.active_requests[domain] >= settings.max_concurrent:
                await asyncio.sleep(0.1)

            # Wait for time-based rate limit
            time_since_last = time.time() - settings.last_request_time
            if time_since_last < settings.crawl_delay:
                wait_time = settings.crawl_delay - time_since_last
                logger.debug(f"Rate limiting {domain}: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

            # Update tracking
            settings.last_request_time = time.time()
            self.active_requests[domain] += 1

    async def request_completed(self, url: str, response_time: float, status_code: int):
        """Called after request completion to update state"""
        domain = self.get_domain(url)
        settings = self.domain_settings[domain]

        # Update active request count
        self.active_requests[domain] = max(0, self.active_requests[domain] - 1)

        # Track request history for adaptive rate limiting
        self.request_history[domain].append({
            'timestamp': time.time(),
            'response_time': response_time,
            'status_code': status_code
        })

        # Adaptive rate limiting based on server response
        await self._adaptive_rate_adjustment(domain, status_code, response_time)

    async def _adaptive_rate_adjustment(self, domain: str, status_code: int, response_time: float):
        """Adjust rate limiting based on server response"""
        settings = self.domain_settings[domain]

        # Increase delay if server is slow or returning errors
        if status_code == 429:  # Too Many Requests
            settings.crawl_delay *= 2
            logger.info(f"Rate limit hit for {domain}, increasing delay to {settings.crawl_delay:.1f}s")

        elif status_code >= 500:  # Server errors
            settings.crawl_delay *= 1.5
            logger.info(f"Server error for {domain}, increasing delay to {settings.crawl_delay:.1f}s")

        elif response_time > 10:  # Very slow response
            settings.crawl_delay *= 1.2
            logger.info(f"Slow response from {domain}, increasing delay to {settings.crawl_delay:.1f}s")

        # Gradually reduce delay for fast, successful responses
        elif status_code == 200 and response_time < 2:
            settings.crawl_delay = max(
                self.default_delay,
                settings.crawl_delay * 0.95
            )

    def get_domain_stats(self) -> Dict:
        """Get statistics for all domains"""
        stats = {}
        for domain, settings in self.domain_settings.items():
            history = self.request_history[domain]
            recent_requests = [req for req in history if time.time() - req['timestamp'] < 300]  # Last 5 minutes

            stats[domain] = {
                'crawl_delay': settings.crawl_delay,
                'max_concurrent': settings.max_concurrent,
                'active_requests': self.active_requests[domain],
                'blocked': settings.blocked,
                'user_agent_allowed': settings.user_agent_allowed,
                'recent_requests': len(recent_requests),
                'avg_response_time': sum(req['response_time'] for req in recent_requests) / len(recent_requests) if recent_requests else 0
            }

        return stats