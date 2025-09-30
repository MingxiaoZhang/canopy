import time
import logging
from typing import Set, List, Dict, Tuple
from urllib.parse import urlparse, urljoin
from collections import defaultdict, deque
from .graph_crawl_config import GraphCrawlConfig
from .link_prioritizer import LinkPrioritizer
from .link_info import LinkInfo
from .crawl_mode import CrawlMode


class GraphCrawlManager:
    """Manages graph-based crawling with link discovery and prioritization"""

    def __init__(self, config: GraphCrawlConfig):
        self.config = config
        self.prioritizer = LinkPrioritizer(config)

        # Tracking data structures
        self.discovered_domains: Set[str] = set()
        self.domain_link_counts: Dict[str, int] = defaultdict(int)
        self.domain_scores: Dict[str, float] = defaultdict(float)
        self.depth_tracking: Dict[str, int] = {}
        self.seed_domains: Set[str] = set()

        # Link queue with priority
        self.prioritized_queue: deque = deque()

    def initialize_seeds(self, seed_urls: List[str]):
        """Initialize crawling with seed URLs"""
        for url in seed_urls:
            domain = urlparse(url).netloc.lower()
            self.seed_domains.add(domain)
            self.discovered_domains.add(domain)
            self.depth_tracking[url] = 0

    def should_crawl_domain(self, domain: str) -> Tuple[bool, str]:
        """Determine if a domain should be crawled"""
        domain_lower = domain.lower()

        # Check blocked domains
        if domain_lower in self.config.blocked_domains:
            return False, f"Domain {domain} is blocked"

        # Check mode-specific rules
        if self.config.mode == CrawlMode.SINGLE_DOMAIN:
            if domain_lower not in self.seed_domains:
                return False, f"Cross-domain crawling disabled"

        elif self.config.mode == CrawlMode.WHITELIST:
            if domain_lower not in self.config.allowed_domains:
                return False, f"Domain {domain} not in whitelist"

        elif self.config.mode == CrawlMode.CROSS_DOMAIN or self.config.mode == CrawlMode.GRAPH:
            # Check domain limits
            if len(self.discovered_domains) >= self.config.max_domains:
                if domain_lower not in self.discovered_domains:
                    return False, f"Maximum domains ({self.config.max_domains}) reached"

            # Check domain score
            if domain_lower not in self.seed_domains:
                score = self.domain_scores[domain_lower]
                if score < self.config.min_domain_score:
                    return False, f"Domain score {score:.2f} below threshold {self.config.min_domain_score}"

        return True, "OK"

    def extract_links_from_page(self, url: str, parsed_data: Dict, page_content: str = "") -> List[LinkInfo]:
        """Extract and prioritize links from a crawled page"""
        current_depth = self.depth_tracking.get(url, 0)
        current_domain = urlparse(url).netloc.lower()
        discovered_links = []

        # Check depth limit
        if current_depth >= self.config.max_depth:
            logging.info(f"Maximum depth {self.config.max_depth} reached for {url}")
            return discovered_links

        # Process all links found on the page
        for link_url in parsed_data.get('links', []):
            try:
                # Normalize URL
                absolute_url = urljoin(url, link_url)
                parsed_link = urlparse(absolute_url)

                if not parsed_link.scheme or not parsed_link.netloc:
                    continue

                target_domain = parsed_link.netloc.lower()

                # Check if we should crawl this domain
                should_crawl, reason = self.should_crawl_domain(target_domain)
                if not should_crawl:
                    logging.debug(f"Skipping link {absolute_url}: {reason}")
                    continue

                # Create link info
                link_info = LinkInfo(
                    url=absolute_url,
                    source_url=url,
                    domain=target_domain,
                    depth=current_depth + 1,
                    link_text="",  # Could extract from HTML if needed
                    discovered_at=time.time()
                )

                # Calculate priority
                priority = self.prioritizer.calculate_priority(link_info, page_content)

                if priority <= 0:
                    continue

                link_info.priority = priority
                discovered_links.append(link_info)

                # Update domain tracking
                if target_domain not in self.discovered_domains:
                    self.discovered_domains.add(target_domain)
                    logging.info(f"🌐 Discovered new domain: {target_domain}")

                self.domain_link_counts[target_domain] += 1

                # Update domain score based on how often it's referenced
                self._update_domain_score(target_domain, current_domain, priority)

                # Track depth
                self.depth_tracking[absolute_url] = current_depth + 1

            except Exception as e:
                logging.warning(f"Error processing link {link_url}: {e}")

        # Sort by priority (highest first)
        discovered_links.sort(key=lambda x: x.priority, reverse=True)

        logging.info(f"🔗 Discovered {len(discovered_links)} prioritized links from {url}")
        return discovered_links

    def _update_domain_score(self, target_domain: str, source_domain: str, link_priority: int):
        """Update domain score based on incoming links"""
        # Base score from link priority
        score_increment = link_priority / 1000.0

        # Bonus for links from high-quality domains
        if source_domain in self.seed_domains:
            score_increment *= 2.0
        elif source_domain in self.config.priority_domains:
            score_increment *= 1.5

        # Update score with decay
        current_score = self.domain_scores[target_domain]
        self.domain_scores[target_domain] = current_score * 0.9 + score_increment

    def get_next_urls(self, max_urls: int = 1) -> List[str]:
        """Get next URLs to crawl based on priority"""
        urls = []

        # Sort queue by priority if needed
        sorted_queue = sorted(self.prioritized_queue, key=lambda x: x.priority, reverse=True)
        self.prioritized_queue = deque(sorted_queue)

        for _ in range(max_urls):
            if not self.prioritized_queue:
                break

            link_info = self.prioritized_queue.popleft()
            urls.append(link_info.url)

        return urls

    def add_discovered_links(self, link_infos: List[LinkInfo]):
        """Add discovered links to the crawl queue"""
        for link_info in link_infos:
            self.prioritized_queue.append(link_info)

    def get_crawl_statistics(self) -> Dict:
        """Get statistics about the graph crawl"""
        return {
            'discovered_domains': len(self.discovered_domains),
            'domains_list': list(self.discovered_domains),
            'total_queued_links': len(self.prioritized_queue),
            'domain_link_counts': dict(self.domain_link_counts),
            'domain_scores': {k: round(v, 3) for k, v in self.domain_scores.items()},
            'max_depth_reached': max(self.depth_tracking.values()) if self.depth_tracking else 0,
            'seed_domains': list(self.seed_domains)
        }