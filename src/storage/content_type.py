from enum import Enum


class ContentType(Enum):
    """Enum for different content types that can be stored"""
    HTML = 'html'
    CSS = 'css'
    JSON = 'json'
    SCREENSHOT = 'screenshot'
    COMPONENT_SCREENSHOT = 'component_screenshots'
    DOM_TREE = 'dom_trees'