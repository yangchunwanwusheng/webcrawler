"""爬虫工作线程模块"""

import asyncio
from typing import Union, List

from PyQt6.QtCore import QThread, pyqtSignal

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, UndetectedAdapter
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy


class CrawlerWorker(QThread):
    """爬虫工作线程"""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, url: str, browser_config: BrowserConfig, crawler_config: CrawlerRunConfig):
        super().__init__()
        self.url = url
        self.browser_config = browser_config
        self.crawler_config = crawler_config

    def run(self):
        """执行爬虫任务"""
        try:
            self.status_update.emit("正在初始化爬虫...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def crawl():
                strategy = AsyncPlaywrightCrawlerStrategy(
                    browser_config=self.browser_config,
                    browser_adapter=UndetectedAdapter()
                )
                
                async with AsyncWebCrawler(
                    crawler_strategy=strategy,
                    config=self.browser_config
                ) as crawler:
                    self.status_update.emit(f"正在访问 {self.url}...")
                    
                    # 检查是否是深度爬取
                    if self.crawler_config.deep_crawl_strategy:
                        # 深度爬取模式
                        if self.crawler_config.stream:
                            # 流式模式
                            results = []
                            async for result in await crawler.arun(self.url, config=self.crawler_config):
                                results.append(result)
                                self.status_update.emit(f"已爬取 {len(results)} 个页面...")
                            return results
                        else:
                            # 非流式模式
                            results = await crawler.arun(self.url, config=self.crawler_config)
                            self.status_update.emit(f"爬取完成，共 {len(results)} 个页面")
                            return results
                    else:
                        # 单页爬取模式
                        result = await crawler.arun(self.url, config=self.crawler_config)
                        return result
            
            result = loop.run_until_complete(crawl())
            loop.close()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

