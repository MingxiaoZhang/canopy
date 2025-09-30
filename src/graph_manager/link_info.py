from dataclasses import dataclass


@dataclass
class LinkInfo:
    """Information about a discovered link"""
    url: str
    source_url: str
    domain: str
    depth: int = 0
    priority: int = 0
    link_text: str = ""
    discovered_at: float = 0.0