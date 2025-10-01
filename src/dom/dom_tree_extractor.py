#!/usr/bin/env python3
"""
DOM Tree Extraction and Component Screenshot Module
Captures DOM structure and enables component-level screenshots
"""

import json
import hashlib
import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import asdict
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup, Tag, NavigableString
from playwright.async_api import Page
from ..storage import ContentType
from .dom_node import DOMNode

logger = logging.getLogger(__name__)


class DOMTreeExtractor:
    """Extracts DOM tree structure and captures component screenshots"""

    def __init__(self, base_output_dir: str = "crawl_data"):
        self.base_output_dir = base_output_dir

    async def extract_dom_tree(self, page: Page, url: str,
                             capture_screenshots: bool = True,
                             max_depth: int = 10,
                             screenshot_components: List[str] = None,
                             storage = None) -> DOMNode:
        """
        Extract complete DOM tree with optional component screenshots

        Args:
            page: Playwright page object
            url: URL being processed
            capture_screenshots: Whether to capture component screenshots
            max_depth: Maximum tree depth to process
            screenshot_components: List of CSS selectors to screenshot
            storage: Storage object (required for saving compressed screenshots)
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
                'h1', 'h2', 'h3', 'div', 'body', 'a', 'p', 'span', 'img'
            ]

        logger.info(f"Extracting DOM tree for: {url}")

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

        # Capture component screenshots and get path mapping
        screenshot_mapping = {}
        if capture_screenshots:
            screenshot_mapping = await self._capture_component_screenshots(
                page, url, screenshot_components, storage=storage
            )

        # Link screenshots to DOM nodes
        if screenshot_mapping:
            self._link_screenshots_to_nodes(root_node, screenshot_mapping)

        # Save DOM tree to JSON via storage
        await self._save_dom_tree(root_node, url, storage)

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
            # Skip empty text nodes (whitespace only)
            if not text_content:
                return None
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
                                           selectors: List[str], storage) -> Dict[str, str]:
        """Capture isolated screenshots of specific components"""
        # Parse URL for organization
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '').replace(':', '_')
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        logger.info("Capturing component screenshots")
        screenshot_count = 0
        screenshot_mapping = {}  # Maps position keys to file paths

        for selector in selectors:
            try:
                # Find ALL elements matching this selector
                locators = page.locator(selector)
                element_count = await locators.count()

                if element_count == 0:
                    continue

                logger.debug(f"Found {element_count} elements for {selector}")

                for i in range(element_count):
                    try:
                        element = locators.nth(i)
                        is_visible = await element.is_visible()

                        if not is_visible:
                            continue

                        bounding_box = await element.bounding_box()

                        if not bounding_box or bounding_box['width'] <= 0 or bounding_box['height'] <= 0:
                            continue

                        # Generate unique filename with element index and position
                        selector_safe = self._sanitize_filename(selector)
                        element_id = f"x{int(bounding_box['x'])}_y{int(bounding_box['y'])}"
                        filename = f"{selector_safe}_{i+1}_{element_id}"

                        # Capture screenshot to bytes
                        screenshot_bytes = await element.screenshot(type='png')

                        # Save using storage system (with compression)
                        # Use parent URL so component screenshots go in same page directory
                        filepath = await storage.save_content(url, screenshot_bytes, ContentType.COMPONENT_SCREENSHOT, filename_suffix=filename)

                        screenshot_count += 1
                        logger.debug(f"Captured {selector}[{i+1}] -> {filename}")

                        # Store mapping using position as key
                        position_key = f"x{int(bounding_box['x'])}_y{int(bounding_box['y'])}"
                        screenshot_mapping[position_key] = filepath

                    except Exception as e:
                        logger.debug(f"Failed to capture {selector}[{i+1}]: {str(e)[:30]}...")
                        continue

            except Exception as e:
                logger.warning(f"Failed to process {selector}: {str(e)[:50]}...")

        logger.info(f"Captured {screenshot_count} component screenshots")
        return screenshot_mapping

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

    def _link_screenshots_to_nodes(self, node: DOMNode, screenshot_mapping: Dict[str, str]):
        """Recursively link screenshots to DOM nodes based on position"""
        if node.bounding_box and screenshot_mapping:
            # Generate position key from bounding box
            x = int(node.bounding_box['x'])
            y = int(node.bounding_box['y'])
            position_key = f"x{x}_y{y}"

            # Check if we have a screenshot for this position
            if position_key in screenshot_mapping:
                node.screenshot_path = screenshot_mapping[position_key]
                logger.debug(f"Linked screenshot to {node.tag_name} at {position_key}")

        # Recursively process children
        for child in node.children:
            self._link_screenshots_to_nodes(child, screenshot_mapping)

    async def _save_dom_tree(self, dom_node: DOMNode, url: str, storage):
        """Save DOM tree structure to JSON file via storage class"""
        # Convert to dictionary for JSON serialization
        tree_data = {
            'url': url,
            'url_hash': hashlib.md5(url.encode()).hexdigest()[:12],
            'dom_tree': self._dom_node_to_dict(dom_node),
            'metadata': {
                'total_nodes': self._count_nodes(dom_node),
                'max_depth': self._get_max_depth(dom_node),
                'extraction_timestamp': datetime.now().isoformat()
            }
        }

        # Save via storage class
        tree_json = json.dumps(tree_data, indent=2, ensure_ascii=False)
        filepath = await storage.save_content(url, tree_json, ContentType.DOM_TREE)

        if filepath:
            logger.info(f"DOM tree saved for {url}")
        else:
            logger.error(f"Failed to save DOM tree for {url}")

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