#!/usr/bin/env python3
"""
DOM Tree Extraction and Component Screenshot Module
Captures DOM structure and enables component-level screenshots
"""

import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup, Tag, NavigableString
from playwright.async_api import Page, ElementHandle
import asyncio
import os
from datetime import datetime

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

class DOMTreeExtractor:
    """Extracts DOM tree structure and captures component screenshots"""

    def __init__(self, base_output_dir: str = "crawl_data"):
        self.base_output_dir = base_output_dir
        self.dom_output_dir = os.path.join(base_output_dir, "dom_trees")
        self.component_screenshot_dir = os.path.join(base_output_dir, "component_screenshots")

        # Create output directories with date structure
        today = datetime.now()
        date_path = f"{today.year:04d}/{today.month:02d}/{today.day:02d}"

        self.dom_output_dir = os.path.join(self.dom_output_dir, date_path)
        self.component_screenshot_dir = os.path.join(self.component_screenshot_dir, date_path)

        os.makedirs(self.dom_output_dir, exist_ok=True)
        os.makedirs(self.component_screenshot_dir, exist_ok=True)

    async def extract_dom_tree(self, page: Page, url: str,
                             capture_screenshots: bool = True,
                             max_depth: int = 10,
                             screenshot_components: List[str] = None) -> DOMNode:
        """
        Extract complete DOM tree with optional component screenshots

        Args:
            page: Playwright page object
            url: URL being processed
            capture_screenshots: Whether to capture component screenshots
            max_depth: Maximum tree depth to process
            screenshot_components: List of CSS selectors to screenshot
        """
        if screenshot_components is None:
            screenshot_components = [
                # Semantic HTML5 elements
                'header', 'nav', 'main', 'article', 'section',
                'aside', 'footer',
                # Common class-based components
                '.container', '.content', '.card', '.navbar', '.hero', '.banner',
                # Common ID-based components
                '#header', '#navigation', '#main', '#sidebar', '#footer',
                # Basic HTML elements that usually contain meaningful content
                'h1', 'h2', 'h3', 'div', 'body'
            ]

        print(f"🌳 Extracting DOM tree for: {url}")

        # Get page content and create BeautifulSoup tree
        html_content = await page.content()
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract DOM tree starting from html element
        html_element = soup.find('html')
        if not html_element:
            html_element = soup

        # Build DOM tree
        root_node = await self._build_dom_node(
            page, html_element, url, depth=0, max_depth=max_depth
        )

        # Capture component screenshots if enabled
        if capture_screenshots:
            await self._capture_component_screenshots(
                page, url, screenshot_components
            )

        # Save DOM tree to JSON
        await self._save_dom_tree(root_node, url)

        return root_node

    async def _build_dom_node(self, page: Page, element: Tag, url: str,
                            depth: int = 0, max_depth: int = 10,
                            parent_xpath: str = "") -> DOMNode:
        """Recursively build DOM node from BeautifulSoup element"""

        if depth > max_depth:
            return None

        # Extract basic element information
        tag_name = element.name if hasattr(element, 'name') else 'text'
        element_id = element.get('id') if hasattr(element, 'get') else None
        class_names = element.get('class', []) if hasattr(element, 'get') else []

        # Get all attributes
        attributes = {}
        if hasattr(element, 'attrs'):
            attributes = {k: v if isinstance(v, str) else ' '.join(v)
                         for k, v in element.attrs.items()}

        # Extract text content (only direct text, not from children)
        text_content = None
        if isinstance(element, NavigableString):
            text_content = str(element).strip()
        elif hasattr(element, 'get_text'):
            # Get only direct text content
            direct_text = ''.join([str(child) for child in element.children
                                 if isinstance(child, NavigableString)])
            text_content = direct_text.strip() if direct_text.strip() else None

        # Generate CSS selector and XPath
        css_selector = self._generate_css_selector(element)
        xpath = self._generate_xpath(element, parent_xpath)

        # Try to get bounding box from browser
        bounding_box = None
        try:
            if css_selector and hasattr(page, 'locator'):
                locator = page.locator(css_selector).first
                if await locator.count() > 0:
                    box = await locator.bounding_box()
                    if box:
                        bounding_box = {
                            'x': box['x'],
                            'y': box['y'],
                            'width': box['width'],
                            'height': box['height']
                        }
        except Exception:
            pass  # Bounding box extraction failed, continue without it

        # Generate node hash
        node_data = f"{tag_name}_{element_id}_{class_names}_{text_content}"
        node_hash = hashlib.md5(node_data.encode()).hexdigest()[:12]

        # Create DOM node
        dom_node = DOMNode(
            tag_name=tag_name,
            element_id=element_id,
            class_names=class_names,
            attributes=attributes,
            text_content=text_content,
            xpath=xpath,
            css_selector=css_selector,
            bounding_box=bounding_box,
            node_hash=node_hash,
            depth=depth
        )

        # Process children recursively
        if hasattr(element, 'children'):
            for child in element.children:
                if hasattr(child, 'name') or isinstance(child, NavigableString):
                    child_node = await self._build_dom_node(
                        page, child, url, depth + 1, max_depth, xpath
                    )
                    if child_node:
                        dom_node.children.append(child_node)

        return dom_node

    def _generate_css_selector(self, element: Tag) -> str:
        """Generate CSS selector for element"""
        if not hasattr(element, 'name') or not element.name:
            return None

        selector_parts = [element.name]

        # Add ID if present (most specific)
        if element.get('id'):
            return f"#{element.get('id')}"

        # Add classes if present
        classes = element.get('class', [])
        if classes:
            class_selector = '.' + '.'.join(classes)
            selector_parts.append(class_selector)

        return ''.join(selector_parts)

    def _generate_xpath(self, element: Tag, parent_xpath: str = "") -> str:
        """Generate XPath for element"""
        if not hasattr(element, 'name') or not element.name:
            return parent_xpath

        # Count siblings with same tag name
        siblings = [s for s in element.parent.children
                   if hasattr(s, 'name') and s.name == element.name] if element.parent else []

        if len(siblings) > 1:
            # Find position among siblings
            position = siblings.index(element) + 1
            xpath_part = f"{element.name}[{position}]"
        else:
            xpath_part = element.name

        # Combine with parent xpath
        if parent_xpath:
            return f"{parent_xpath}/{xpath_part}"
        else:
            return f"/{xpath_part}"

    async def _capture_component_screenshots(self, page: Page, url: str,
                                           selectors: List[str]):
        """Capture isolated screenshots of specific components"""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        domain = url.split('/')[2] if '//' in url else 'unknown'

        print(f"📸 Capturing component screenshots...")

        for selector in selectors:
            try:
                # Check if element exists and is visible
                locator = page.locator(selector).first
                element_count = await locator.count()

                if element_count > 0:
                    # Check if element is visible
                    is_visible = await locator.is_visible()

                    if is_visible:
                        # Get element info for filename
                        bounding_box = await locator.bounding_box()

                        if bounding_box and bounding_box['width'] > 0 and bounding_box['height'] > 0:
                            # Generate safe filename
                            selector_safe = self._sanitize_filename(selector)
                            filename = f"{domain}_{url_hash}_{selector_safe}.png"
                            filepath = os.path.join(self.component_screenshot_dir, filename)

                            # Capture isolated screenshot of the element
                            await locator.screenshot(path=filepath)
                            print(f"  ✅ {selector} -> {filename}")
                        else:
                            print(f"  ⚠️ {selector} has zero dimensions, skipping")
                    else:
                        print(f"  ⚠️ {selector} not visible, skipping")

            except Exception as e:
                print(f"  ❌ Failed to capture {selector}: {str(e)[:50]}...")

    def _sanitize_filename(self, selector: str) -> str:
        """Convert CSS selector to safe filename"""
        safe_name = selector.replace('#', 'id_').replace('.', 'class_').replace(' ', '_')
        safe_name = safe_name.replace('>', '_gt_').replace('+', '_plus_').replace('~', '_tilde_')
        safe_name = safe_name.replace('[', '_').replace(']', '_').replace('=', '_eq_')
        safe_name = safe_name.replace('"', '').replace("'", '').replace(':', '_')

        # Remove consecutive underscores and trim
        while '__' in safe_name:
            safe_name = safe_name.replace('__', '_')

        return safe_name.strip('_')

    async def _save_dom_tree(self, dom_node: DOMNode, url: str):
        """Save DOM tree structure to JSON file"""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        domain = url.split('/')[2] if '//' in url else 'unknown'
        filename = f"{domain}_{url_hash}_dom_tree.json"
        filepath = os.path.join(self.dom_output_dir, filename)

        # Convert to dictionary for JSON serialization
        tree_data = {
            'url': url,
            'domain': domain,
            'dom_tree': self._dom_node_to_dict(dom_node),
            'metadata': {
                'total_nodes': self._count_nodes(dom_node),
                'max_depth': self._get_max_depth(dom_node),
                'extraction_timestamp': datetime.now().isoformat(),
                'screenshot_dir': self.component_screenshot_dir
            }
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(tree_data, f, indent=2, ensure_ascii=False)
            print(f"🌳 DOM tree saved: {filename}")
        except Exception as e:
            print(f"⚠️ Failed to save DOM tree: {e}")

    def _dom_node_to_dict(self, node: DOMNode) -> Dict[str, Any]:
        """Convert DOMNode to dictionary for JSON serialization"""
        node_dict = asdict(node)

        # Recursively convert children
        if node.children:
            node_dict['children'] = [self._dom_node_to_dict(child) for child in node.children]

        return node_dict

    def _count_nodes(self, node: DOMNode) -> int:
        """Count total nodes in DOM tree"""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count

    def _get_max_depth(self, node: DOMNode, current_depth: int = 0) -> int:
        """Get maximum depth of DOM tree"""
        max_depth = current_depth
        for child in node.children:
            child_depth = self._get_max_depth(child, current_depth + 1)
            max_depth = max(max_depth, child_depth)
        return max_depth