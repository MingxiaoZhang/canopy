from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class DOMNode:
    """Represents a single DOM node with metadata"""
    tag_name: str
    element_id: Optional[str] = None
    class_names: List[str] = None
    attributes: Dict[str, str] = None
    text_content: Optional[str] = None
    children: List['DOMNode'] = None
    xpath: Optional[str] = None
    css_selector: Optional[str] = None
    bounding_box: Optional[Dict[str, float]] = None
    screenshot_path: Optional[str] = None
    node_hash: Optional[str] = None
    depth: int = 0

    def __post_init__(self):
        if self.class_names is None:
            self.class_names = []
        if self.attributes is None:
            self.attributes = {}
        if self.children is None:
            self.children = []