from enum import Enum


class CrawlMode(Enum):
    """Different crawling modes for link following"""
    SINGLE_DOMAIN = "single_domain"         # Only crawl within starting domains
    CROSS_DOMAIN = "cross_domain"           # Follow links across domains with limits
    WHITELIST = "whitelist"                 # Only crawl specified domains
    GRAPH = "graph"                         # Full graph crawling with intelligent filtering
    FOCUSED = "focused"                     # Topic-focused crawling with keyword filtering