"""Web Crawler GUI Application Package"""

__version__ = "0.1.0"

from webcrawl.main_window import WebCrawlerGUI
from webcrawl.worker import CrawlerWorker
from webcrawl.utils import get_empty_html, render_markdown
from webcrawl.config import build_deep_crawl_strategy, DEEP_CRAWL_AVAILABLE

__all__ = [
    "WebCrawlerGUI",
    "CrawlerWorker",
    "get_empty_html",
    "render_markdown",
    "build_deep_crawl_strategy",
    "DEEP_CRAWL_AVAILABLE",
]

