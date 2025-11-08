import asyncio
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

import markdown

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QGroupBox,
    QCheckBox,
    QDoubleSpinBox,
    QTabWidget,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QSpinBox,
    QComboBox,
    QScrollArea,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    UndetectedAdapter,
)
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy

# 深度爬取相关导入
try:
    from crawl4ai.deep_crawling import (
        BFSDeepCrawlStrategy,
        DFSDeepCrawlStrategy,
        BestFirstCrawlingStrategy,
    )
    from crawl4ai.deep_crawling.filters import (
        FilterChain,
        URLPatternFilter,
        DomainFilter,
        ContentTypeFilter,
    )
    from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
    DEEP_CRAWL_AVAILABLE = True
except ImportError:
    DEEP_CRAWL_AVAILABLE = False


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


class WebCrawlerGUI(QMainWindow):
    """网络爬虫GUI主窗口"""

    def __init__(self):
        super().__init__()
        self.worker: Optional[CrawlerWorker] = None
        self.current_result = None
        self.is_dark_mode = False  # 默认亮色模式
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("网络爬虫工具 - Web Crawler")
        self.setGeometry(100, 100, 1200, 800)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # URL输入区域
        url_group = QGroupBox("目标URL")
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("网址:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.example.com/")
        self.url_input.setText("https://www.osredm.com/")
        url_layout.addWidget(self.url_input)
        main_layout.addWidget(url_group)
        url_group.setLayout(url_layout)

        # 配置选项区域
        config_group = QGroupBox("爬虫配置")
        config_layout = QVBoxLayout()

        # 浏览器配置
        browser_layout = QHBoxLayout()
        self.headless_checkbox = QCheckBox("无头模式 (Headless)")
        self.headless_checkbox.setChecked(False)
        browser_layout.addWidget(self.headless_checkbox)
        
        self.verbose_checkbox = QCheckBox("详细输出 (Verbose)")
        self.verbose_checkbox.setChecked(True)
        browser_layout.addWidget(self.verbose_checkbox)
        
        browser_layout.addStretch()
        config_layout.addLayout(browser_layout)

        # 爬虫运行配置
        crawler_layout = QHBoxLayout()
        crawler_layout.addWidget(QLabel("延迟时间 (秒):"))
        self.delay_spinbox = QDoubleSpinBox()
        self.delay_spinbox.setRange(0.0, 60.0)
        self.delay_spinbox.setValue(5.0)
        self.delay_spinbox.setSingleStep(0.5)
        crawler_layout.addWidget(self.delay_spinbox)

        self.simulate_user_checkbox = QCheckBox("模拟用户行为")
        self.simulate_user_checkbox.setChecked(True)
        crawler_layout.addWidget(self.simulate_user_checkbox)

        self.magic_checkbox = QCheckBox("魔法模式")
        self.magic_checkbox.setChecked(True)
        crawler_layout.addWidget(self.magic_checkbox)

        self.wait_images_checkbox = QCheckBox("等待图片加载")
        self.wait_images_checkbox.setChecked(True)
        crawler_layout.addWidget(self.wait_images_checkbox)

        crawler_layout.addStretch()
        config_layout.addLayout(crawler_layout)

        # 深度爬取配置
        deep_crawl_layout = QVBoxLayout()
        self.enable_deep_crawl_checkbox = QCheckBox("启用深度爬取")
        self.enable_deep_crawl_checkbox.setChecked(False)
        self.enable_deep_crawl_checkbox.toggled.connect(self._on_deep_crawl_toggled)
        deep_crawl_layout.addWidget(self.enable_deep_crawl_checkbox)

        # 深度爬取选项容器（默认隐藏）
        self.deep_crawl_options = QWidget()
        deep_crawl_options_layout = QVBoxLayout(self.deep_crawl_options)
        deep_crawl_options_layout.setContentsMargins(20, 10, 10, 10)

        # 策略选择
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(QLabel("爬取策略:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["BFS (广度优先)", "DFS (深度优先)", "BestFirst (最佳优先)"])
        strategy_layout.addWidget(self.strategy_combo)
        strategy_layout.addStretch()
        deep_crawl_options_layout.addLayout(strategy_layout)

        # 深度和页面限制
        limits_layout = QHBoxLayout()
        limits_layout.addWidget(QLabel("最大深度:"))
        self.max_depth_spinbox = QSpinBox()
        self.max_depth_spinbox.setRange(1, 10)
        self.max_depth_spinbox.setValue(2)
        limits_layout.addWidget(self.max_depth_spinbox)

        limits_layout.addWidget(QLabel("最大页面数:"))
        self.max_pages_spinbox = QSpinBox()
        self.max_pages_spinbox.setRange(1, 1000)
        self.max_pages_spinbox.setValue(50)
        self.max_pages_spinbox.setSpecialValueText("无限制")
        limits_layout.addWidget(self.max_pages_spinbox)

        limits_layout.addStretch()
        deep_crawl_options_layout.addLayout(limits_layout)

        # 其他选项
        options_layout = QHBoxLayout()
        self.include_external_checkbox = QCheckBox("包含外部链接")
        self.include_external_checkbox.setChecked(False)
        options_layout.addWidget(self.include_external_checkbox)

        self.stream_results_checkbox = QCheckBox("流式输出")
        self.stream_results_checkbox.setChecked(True)
        self.stream_results_checkbox.setToolTip("实时显示爬取结果，而不是等待所有页面完成")
        options_layout.addWidget(self.stream_results_checkbox)

        options_layout.addStretch()
        deep_crawl_options_layout.addLayout(options_layout)

        # URL过滤器
        filter_group = QGroupBox("URL过滤器")
        filter_layout = QVBoxLayout()

        # URL模式
        url_pattern_layout = QHBoxLayout()
        url_pattern_layout.addWidget(QLabel("URL模式 (用逗号分隔):"))
        self.url_pattern_input = QLineEdit()
        self.url_pattern_input.setPlaceholderText("例如: *blog*, *docs*, *guide*")
        url_pattern_layout.addWidget(self.url_pattern_input)
        filter_layout.addLayout(url_pattern_layout)

        # 允许的域名
        allowed_domain_layout = QHBoxLayout()
        allowed_domain_layout.addWidget(QLabel("允许的域名 (用逗号分隔):"))
        self.allowed_domains_input = QLineEdit()
        self.allowed_domains_input.setPlaceholderText("例如: example.com, docs.example.com")
        allowed_domain_layout.addWidget(self.allowed_domains_input)
        filter_layout.addLayout(allowed_domain_layout)

        # 阻止的域名
        blocked_domain_layout = QHBoxLayout()
        blocked_domain_layout.addWidget(QLabel("阻止的域名 (用逗号分隔):"))
        self.blocked_domains_input = QLineEdit()
        self.blocked_domains_input.setPlaceholderText("例如: old.example.com")
        blocked_domain_layout.addWidget(self.blocked_domains_input)
        filter_layout.addLayout(blocked_domain_layout)

        filter_group.setLayout(filter_layout)
        deep_crawl_options_layout.addWidget(filter_group)

        # 关键词评分器（用于BestFirst策略）
        scorer_group = QGroupBox("关键词评分器 (BestFirst策略)")
        scorer_layout = QVBoxLayout()

        keyword_layout = QHBoxLayout()
        keyword_layout.addWidget(QLabel("关键词 (用逗号分隔):"))
        self.keywords_input = QLineEdit()
        self.keywords_input.setPlaceholderText("例如: crawl, example, async, configuration")
        keyword_layout.addWidget(self.keywords_input)
        scorer_layout.addLayout(keyword_layout)

        weight_layout = QHBoxLayout()
        weight_layout.addWidget(QLabel("权重:"))
        self.scorer_weight_spinbox = QDoubleSpinBox()
        self.scorer_weight_spinbox.setRange(0.0, 1.0)
        self.scorer_weight_spinbox.setValue(0.7)
        self.scorer_weight_spinbox.setSingleStep(0.1)
        weight_layout.addWidget(self.scorer_weight_spinbox)
        weight_layout.addStretch()
        scorer_layout.addLayout(weight_layout)

        scorer_group.setLayout(scorer_layout)
        deep_crawl_options_layout.addWidget(scorer_group)

        # 评分阈值（用于BFS/DFS策略）
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("评分阈值 (BFS/DFS策略):"))
        self.score_threshold_spinbox = QDoubleSpinBox()
        self.score_threshold_spinbox.setRange(-1.0, 1.0)
        self.score_threshold_spinbox.setValue(0.0)
        self.score_threshold_spinbox.setSingleStep(0.1)
        self.score_threshold_spinbox.setSpecialValueText("无限制")
        threshold_layout.addWidget(self.score_threshold_spinbox)
        threshold_layout.addStretch()
        deep_crawl_options_layout.addLayout(threshold_layout)

        deep_crawl_layout.addWidget(self.deep_crawl_options)
        self.deep_crawl_options.setVisible(False)

        config_layout.addLayout(deep_crawl_layout)

        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        # 控制按钮
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("开始爬取")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.start_button.clicked.connect(self.start_crawling)
        button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("停止")
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_button.clicked.connect(self.stop_crawling)
        button_layout.addWidget(self.stop_button)

        self.save_button = QPushButton("保存结果")
        self.save_button.setEnabled(False)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888;
            }
        """)
        self.save_button.clicked.connect(self.save_results)
        button_layout.addWidget(self.save_button)

        # 主题切换按钮
        self.theme_button = QPushButton("🌙 暗色模式")
        self.theme_button.setToolTip("切换亮色/暗色主题")
        self.theme_button.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #546e7a;
            }
        """)
        self.theme_button.clicked.connect(self.toggle_theme)
        button_layout.addWidget(self.theme_button)

        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("就绪")
        main_layout.addWidget(self.status_label)

        # 结果区域 - 使用标签页
        results_group = QGroupBox("爬取结果")
        results_layout = QVBoxLayout()
        
        # 结果摘要
        summary_layout = QHBoxLayout()
        summary_layout.addWidget(QLabel("状态码:"))
        self.status_code_label = QLabel("-")
        summary_layout.addWidget(self.status_code_label)
        
        summary_layout.addWidget(QLabel("成功:"))
        self.success_label = QLabel("-")
        summary_layout.addWidget(self.success_label)
        
        summary_layout.addWidget(QLabel("控制台消息:"))
        self.console_count_label = QLabel("-")
        summary_layout.addWidget(self.console_count_label)
        
        summary_layout.addStretch()
        results_layout.addLayout(summary_layout)

        # 标签页显示不同内容
        self.tab_widget = QTabWidget()
        
        # Markdown渲染标签页（第一个，作为默认显示）
        self.markdown_preview = QWebEngineView()
        self.markdown_preview.setHtml(self._get_empty_html())
        self.tab_widget.addTab(self.markdown_preview, "预览")

        # Markdown源码标签页
        self.markdown_text = QTextEdit()
        self.markdown_text.setReadOnly(True)
        self.markdown_text.setFont(QFont("Consolas", 10))
        self.tab_widget.addTab(self.markdown_text, "Markdown源码")

        # HTML标签页
        self.html_text = QTextEdit()
        self.html_text.setReadOnly(True)
        self.html_text.setFont(QFont("Consolas", 10))
        self.tab_widget.addTab(self.html_text, "HTML")

        # 控制台消息标签页
        self.console_text = QTextEdit()
        self.console_text.setReadOnly(True)
        self.console_text.setFont(QFont("Consolas", 10))
        self.tab_widget.addTab(self.console_text, "控制台消息")

        results_layout.addWidget(self.tab_widget)
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)

        # 应用初始主题
        self.apply_theme()

    def apply_theme(self):
        """应用当前主题样式"""
        if self.is_dark_mode:
            self._apply_dark_theme()
        else:
            self._apply_light_theme()

    def _apply_light_theme(self):
        """应用亮色主题"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #fafafa;
                color: #333;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #555;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 4px;
                font-size: 13px;
                background-color: #ffffff;
                color: #333;
            }
            QLineEdit:focus {
                border-color: #4CAF50;
            }
            QLabel {
                color: #333;
            }
            QCheckBox {
                spacing: 6px;
                color: #555;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #ddd;
                border-radius: 3px;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border-color: #4CAF50;
            }
            QDoubleSpinBox {
                padding: 6px;
                border: 2px solid #ddd;
                border-radius: 4px;
                min-width: 80px;
                background-color: #ffffff;
                color: #333;
            }
            QDoubleSpinBox:focus {
                border-color: #4CAF50;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f5f5f5;
                color: #666;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #4CAF50;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #e8f5e9;
            }
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #fafafa;
                color: #333;
            }
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 4px;
                text-align: center;
                height: 24px;
                background-color: #f5f5f5;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
        
        # 更新主题按钮文本
        self.theme_button.setText("🌙 暗色模式")
        
        # 更新状态标签颜色
        if hasattr(self, 'status_label'):
            current_text = self.status_label.text()
            if "错误" in current_text or "✗" in current_text:
                self.status_label.setStyleSheet("color: #f44336; padding: 4px;")
            elif "完成" in current_text or "✓" in current_text:
                self.status_label.setStyleSheet("color: #4CAF50; padding: 4px;")
            elif "正在" in current_text or "⏳" in current_text:
                self.status_label.setStyleSheet("color: #2196F3; padding: 4px;")
            else:
                self.status_label.setStyleSheet("color: #666; padding: 4px;")

    def _apply_dark_theme(self):
        """应用暗色主题"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #404040;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #b0b0b0;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #404040;
                border-radius: 4px;
                font-size: 13px;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QLineEdit:focus {
                border-color: #66bb6a;
            }
            QLabel {
                color: #e0e0e0;
            }
            QCheckBox {
                spacing: 6px;
                color: #b0b0b0;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #404040;
                border-radius: 3px;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background-color: #66bb6a;
                border-color: #66bb6a;
            }
            QDoubleSpinBox {
                padding: 6px;
                border: 2px solid #404040;
                border-radius: 4px;
                min-width: 80px;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QDoubleSpinBox:focus {
                border-color: #66bb6a;
            }
            QTabWidget::pane {
                border: 1px solid #404040;
                border-radius: 4px;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #b0b0b0;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #66bb6a;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #3d3d3d;
            }
            QTextEdit {
                border: 1px solid #404040;
                border-radius: 4px;
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QProgressBar {
                border: 2px solid #404040;
                border-radius: 4px;
                text-align: center;
                height: 24px;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #66bb6a;
                border-radius: 2px;
            }
        """)
        
        # 更新主题按钮文本
        self.theme_button.setText("☀️ 亮色模式")
        
        # 更新状态标签颜色
        if hasattr(self, 'status_label'):
            current_text = self.status_label.text()
            if "错误" in current_text or "✗" in current_text:
                self.status_label.setStyleSheet("color: #ef5350; padding: 4px;")
            elif "完成" in current_text or "✓" in current_text:
                self.status_label.setStyleSheet("color: #66bb6a; padding: 4px;")
            elif "正在" in current_text or "⏳" in current_text:
                self.status_label.setStyleSheet("color: #42a5f5; padding: 4px;")
            else:
                self.status_label.setStyleSheet("color: #b0b0b0; padding: 4px;")

    def toggle_theme(self):
        """切换主题"""
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()
        
        # 更新Markdown预览以应用新主题
        if self.current_result and self.current_result.markdown and self.current_result.markdown.raw_markdown:
            # 如果有当前结果，重新渲染Markdown
            try:
                html_content = self._render_markdown(self.current_result.markdown.raw_markdown)
                self.markdown_preview.setHtml(html_content)
            except Exception:
                # 如果渲染失败，使用空HTML模板
                self.markdown_preview.setHtml(self._get_empty_html("渲染失败，请查看Markdown源码"))
        elif hasattr(self, 'markdown_preview'):
            # 如果没有结果，更新空HTML模板
            self.markdown_preview.setHtml(self._get_empty_html())

    def _get_empty_html(self, message: str = "等待爬取结果...") -> str:
        """获取空HTML模板"""
        bg_color = "#1e1e1e" if self.is_dark_mode else "#ffffff"
        text_color = "#e0e0e0" if self.is_dark_mode else "#666"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif;
                    padding: 40px;
                    color: {text_color};
                    background-color: {bg_color};
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <p>{message}</p>
        </body>
        </html>
        """

    def _render_markdown(self, markdown_content: str) -> str:
        """将Markdown内容渲染为HTML"""
        # 配置Markdown扩展
        extensions = [
            'codehilite',  # 代码高亮
            'tables',      # 表格支持
            'fenced_code', # 代码块支持
            'nl2br',       # 换行支持
            'sane_lists',  # 列表支持
        ]
        
        # 转换Markdown为HTML
        html_body = markdown.markdown(
            markdown_content,
            extensions=extensions,
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'use_pygments': False,  # 不使用Pygments，使用简单样式
                }
            }
        )
        
        # 根据主题模式选择样式
        if self.is_dark_mode:
            # 暗色主题样式
            bg_color = "#1e1e1e"
            text_color = "#e0e0e0"
            heading_color = "#ffffff"
            border_color = "#404040"
            code_bg = "rgba(255, 255, 255, 0.1)"
            pre_bg = "#2d2d2d"
            table_bg = "#2d2d2d"
            table_border = "#404040"
            link_color = "#66bb6a"
            blockquote_color = "#b0b0b0"
            blockquote_border = "#404040"
            hr_color = "#404040"
        else:
            # 亮色主题样式
            bg_color = "#ffffff"
            text_color = "#333"
            heading_color = "#24292e"
            border_color = "#eaecef"
            code_bg = "rgba(27, 31, 35, 0.05)"
            pre_bg = "#f6f8fa"
            table_bg = "#f6f8fa"
            table_border = "#dfe2e5"
            link_color = "#0366d6"
            blockquote_color = "#6a737d"
            blockquote_border = "#dfe2e5"
            hr_color = "#e1e4e8"
        
        # 创建完整的HTML文档，包含现代化样式
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', Arial, sans-serif;
                    line-height: 1.6;
                    color: {text_color};
                    background-color: {bg_color};
                    padding: 40px;
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                
                h1, h2, h3, h4, h5, h6 {{
                    margin-top: 24px;
                    margin-bottom: 16px;
                    font-weight: 600;
                    line-height: 1.25;
                    color: {heading_color};
                }}
                
                h1 {{
                    font-size: 2em;
                    border-bottom: 1px solid {border_color};
                    padding-bottom: 0.3em;
                }}
                
                h2 {{
                    font-size: 1.5em;
                    border-bottom: 1px solid {border_color};
                    padding-bottom: 0.3em;
                }}
                
                h3 {{
                    font-size: 1.25em;
                }}
                
                p {{
                    margin-bottom: 16px;
                }}
                
                a {{
                    color: {link_color};
                    text-decoration: none;
                }}
                
                a:hover {{
                    text-decoration: underline;
                }}
                
                ul, ol {{
                    margin-bottom: 16px;
                    padding-left: 2em;
                }}
                
                li {{
                    margin-bottom: 4px;
                }}
                
                code {{
                    padding: 0.2em 0.4em;
                    margin: 0;
                    font-size: 85%;
                    background-color: {code_bg};
                    border-radius: 3px;
                    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
                    color: {text_color};
                }}
                
                pre {{
                    padding: 16px;
                    overflow: auto;
                    font-size: 85%;
                    line-height: 1.45;
                    background-color: {pre_bg};
                    border-radius: 6px;
                    margin-bottom: 16px;
                }}
                
                pre code {{
                    display: inline;
                    padding: 0;
                    margin: 0;
                    overflow: visible;
                    line-height: inherit;
                    word-wrap: normal;
                    background-color: transparent;
                    border: 0;
                }}
                
                blockquote {{
                    padding: 0 1em;
                    color: {blockquote_color};
                    border-left: 0.25em solid {blockquote_border};
                    margin-bottom: 16px;
                }}
                
                table {{
                    border-spacing: 0;
                    border-collapse: collapse;
                    margin-bottom: 16px;
                    width: 100%;
                }}
                
                table th, table td {{
                    padding: 6px 13px;
                    border: 1px solid {table_border};
                }}
                
                table th {{
                    font-weight: 600;
                    background-color: {table_bg};
                }}
                
                table tr:nth-child(2n) {{
                    background-color: {table_bg};
                }}
                
                img {{
                    max-width: 100%;
                    height: auto;
                    border-radius: 4px;
                    margin: 16px 0;
                }}
                
                hr {{
                    height: 0.25em;
                    padding: 0;
                    margin: 24px 0;
                    background-color: {hr_color};
                    border: 0;
                }}
                
                .highlight {{
                    background-color: {pre_bg};
                    border-radius: 6px;
                    padding: 16px;
                    margin-bottom: 16px;
                    overflow-x: auto;
                }}
            </style>
        </head>
        <body>
            {html_body}
        </body>
        </html>
        """
        
        return html_template

    def _on_deep_crawl_toggled(self, checked):
        """深度爬取选项切换"""
        self.deep_crawl_options.setVisible(checked)
        if not DEEP_CRAWL_AVAILABLE and checked:
            QMessageBox.warning(
                self,
                "功能不可用",
                "深度爬取功能需要安装crawl4ai的深度爬取模块。\n"
                "请确保您的crawl4ai版本支持深度爬取功能。"
            )
            self.enable_deep_crawl_checkbox.setChecked(False)
            self.deep_crawl_options.setVisible(False)

    def _build_deep_crawl_strategy(self):
        """构建深度爬取策略"""
        if not DEEP_CRAWL_AVAILABLE or not self.enable_deep_crawl_checkbox.isChecked():
            return None

        max_depth = self.max_depth_spinbox.value()
        include_external = self.include_external_checkbox.isChecked()
        max_pages = self.max_pages_spinbox.value() if self.max_pages_spinbox.value() < 1000 else None

        # 构建过滤器链
        filters = []
        
        # URL模式过滤器
        url_patterns = [p.strip() for p in self.url_pattern_input.text().split(",") if p.strip()]
        if url_patterns:
            filters.append(URLPatternFilter(patterns=url_patterns))

        # 域名过滤器
        allowed_domains = [d.strip() for d in self.allowed_domains_input.text().split(",") if d.strip()]
        blocked_domains = [d.strip() for d in self.blocked_domains_input.text().split(",") if d.strip()]
        if allowed_domains or blocked_domains:
            filters.append(DomainFilter(
                allowed_domains=allowed_domains if allowed_domains else None,
                blocked_domains=blocked_domains if blocked_domains else None
            ))

        filter_chain = FilterChain(filters) if filters else None

        # 构建评分器
        url_scorer = None
        keywords = [k.strip() for k in self.keywords_input.text().split(",") if k.strip()]
        if keywords:
            url_scorer = KeywordRelevanceScorer(
                keywords=keywords,
                weight=self.scorer_weight_spinbox.value()
            )

        # 根据策略类型创建策略
        strategy_type = self.strategy_combo.currentText()
        score_threshold = self.score_threshold_spinbox.value() if self.score_threshold_spinbox.value() > -1.0 else float('-inf')

        if "BFS" in strategy_type:
            return BFSDeepCrawlStrategy(
                max_depth=max_depth,
                include_external=include_external,
                max_pages=max_pages,
                filter_chain=filter_chain,
                url_scorer=url_scorer,
                score_threshold=score_threshold if url_scorer else None
            )
        elif "DFS" in strategy_type:
            return DFSDeepCrawlStrategy(
                max_depth=max_depth,
                include_external=include_external,
                max_pages=max_pages,
                filter_chain=filter_chain,
                url_scorer=url_scorer,
                score_threshold=score_threshold if url_scorer else None
            )
        else:  # BestFirst
            return BestFirstCrawlingStrategy(
                max_depth=max_depth,
                include_external=include_external,
                max_pages=max_pages,
                filter_chain=filter_chain,
                url_scorer=url_scorer
            )

    def start_crawling(self):
        """开始爬取"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请输入有效的URL")
            return

        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            self.url_input.setText(url)

        # 更新UI状态
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.save_button.setEnabled(False)
        self.status_label.setText("正在爬取...")
        self.status_label.setStyleSheet("color: #2196F3; padding: 4px;")

        # 清空之前的结果
        self.markdown_text.clear()
        self.html_text.clear()
        self.console_text.clear()
        self.markdown_preview.setHtml(self._get_empty_html())

        # 创建浏览器配置
        browser_config = BrowserConfig(
            headless=self.headless_checkbox.isChecked(),
            verbose=self.verbose_checkbox.isChecked(),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
        )

        # JavaScript绕过代码
        js_bypass = """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en'],
        });
        delete navigator.__proto__.webdriver;
        await new Promise(resolve => setTimeout(resolve, 3000));
        console.log('浏览器检测绕过尝试完成');
        """

        # 构建深度爬取策略
        deep_crawl_strategy = self._build_deep_crawl_strategy()
        stream_mode = self.stream_results_checkbox.isChecked() if deep_crawl_strategy else False

        # 创建爬虫配置
        crawler_config = CrawlerRunConfig(
            js_code=[js_bypass],
            simulate_user=self.simulate_user_checkbox.isChecked(),
            magic=self.magic_checkbox.isChecked(),
            delay_before_return_html=self.delay_spinbox.value(),
            capture_console_messages=True,
            wait_for_images=self.wait_images_checkbox.isChecked(),
            deep_crawl_strategy=deep_crawl_strategy,
            stream=stream_mode
        )

        # 创建工作线程
        self.worker = CrawlerWorker(url, browser_config, crawler_config)
        self.worker.finished.connect(self.on_crawl_finished)
        self.worker.error.connect(self.on_crawl_error)
        self.worker.status_update.connect(self.update_status)
        self.worker.start()

    def stop_crawling(self):
        """停止爬取"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.status_label.setText("已停止")
            self.status_label.setStyleSheet("color: #f44336; padding: 4px;")
            self.reset_ui()

    def on_crawl_finished(self, result):
        """爬取完成回调"""
        # 检查是否是深度爬取结果（列表）
        if isinstance(result, list):
            # 深度爬取模式：处理多个结果
            if not result:
                QMessageBox.warning(self, "警告", "深度爬取未获取到任何结果")
                self.reset_ui()
                return

            # 合并所有结果
            all_markdown = []
            all_html = []
            all_console = []
            total_pages = len(result)
            successful_pages = sum(1 for r in result if r.success)
            
            # 更新摘要信息
            self.status_code_label.setText(f"{total_pages} 页")
            self.success_label.setText(f"{successful_pages}/{total_pages}")
            
            console_count = sum(len(r.console_messages or []) for r in result)
            self.console_count_label.setText(str(console_count))

            # 合并所有页面的内容
            for i, res in enumerate(result):
                depth = res.metadata.get('depth', 0) if hasattr(res, 'metadata') else 0
                score = res.metadata.get('score', 0) if hasattr(res, 'metadata') else 0
                url = res.url if hasattr(res, 'url') else f"页面 {i+1}"
                
                # 添加页面分隔符
                separator = f"\n\n{'='*80}\n页面 {i+1}: {url}\n深度: {depth}"
                if score > 0:
                    separator += f" | 评分: {score:.2f}"
                separator += f"\n{'='*80}\n\n"
                
                if res.markdown and res.markdown.raw_markdown:
                    all_markdown.append(separator + res.markdown.raw_markdown)
                
                if res.html:
                    all_html.append(f"<!-- {separator} -->\n{res.html}")
                
                if res.console_messages:
                    for msg in res.console_messages:
                        all_console.append(f"[页面 {i+1}] {msg}")

            # 显示合并后的结果
            if all_markdown:
                combined_markdown = "\n".join(all_markdown)
                self.markdown_text.setPlainText(combined_markdown)
                try:
                    html_content = self._render_markdown(combined_markdown)
                    self.markdown_preview.setHtml(html_content)
                except Exception as e:
                    error_html = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; padding: 20px;">
                        <h2 style="color: #f44336;">Markdown渲染错误</h2>
                        <p>{str(e)}</p>
                    </body>
                    </html>
                    """
                    self.markdown_preview.setHtml(error_html)
            else:
                self.markdown_text.setPlainText("未获取到Markdown内容")
                self.markdown_preview.setHtml(self._get_empty_html("未获取到Markdown内容"))

            if all_html:
                self.html_text.setPlainText("\n\n".join(all_html))
            else:
                self.html_text.setPlainText("未获取到HTML内容")

            if all_console:
                self.console_text.setPlainText("\n".join(all_console))
            else:
                self.console_text.setPlainText("未捕获到控制台消息")

            self.current_result = result
            self.status_label.setText(f"爬取完成 - 共 {total_pages} 个页面")
            self.status_label.setStyleSheet("color: #4CAF50; padding: 4px;")
            self.reset_ui()
            self.save_button.setEnabled(True)
        else:
            # 单页爬取模式：原有逻辑
            self.current_result = result
            
            # 更新摘要信息
            self.status_code_label.setText(str(result.status_code))
            self.success_label.setText("是" if result.success else "否")
            console_count = len(result.console_messages or [])
            self.console_count_label.setText(str(console_count))

            # 显示结果
            if result.markdown and result.markdown.raw_markdown:
                markdown_content = result.markdown.raw_markdown
                self.markdown_text.setPlainText(markdown_content)
                # 渲染Markdown为HTML
                try:
                    html_content = self._render_markdown(markdown_content)
                    self.markdown_preview.setHtml(html_content)
                except Exception as e:
                    error_html = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; padding: 20px;">
                        <h2 style="color: #f44336;">Markdown渲染错误</h2>
                        <p>{str(e)}</p>
                        <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{markdown_content[:500]}...</pre>
                    </body>
                    </html>
                    """
                    self.markdown_preview.setHtml(error_html)
            else:
                self.markdown_text.setPlainText("未获取到Markdown内容")
                self.markdown_preview.setHtml(self._get_empty_html("未获取到Markdown内容"))

            if result.html:
                self.html_text.setPlainText(result.html)
            else:
                self.html_text.setPlainText("未获取到HTML内容")

            # 显示控制台消息
            if result.console_messages:
                console_output = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(result.console_messages)])
                self.console_text.setPlainText(console_output)
            else:
                self.console_text.setPlainText("未捕获到控制台消息")

            # 检查浏览器检测错误
            has_browser_error = result.html and "不支持当前浏览器" in result.html
            if has_browser_error:
                QMessageBox.warning(self, "警告", "检测到浏览器检测错误，可能需要调整配置")

            self.status_label.setText("爬取完成")
            self.status_label.setStyleSheet("color: #4CAF50; padding: 4px;")
            self.reset_ui()
            self.save_button.setEnabled(True)

    def on_crawl_error(self, error_msg):
        """爬取错误回调"""
        QMessageBox.critical(self, "错误", f"爬取过程中发生错误:\n{error_msg}")
        self.status_label.setText(f"错误: {error_msg}")
        self.status_label.setStyleSheet("color: #f44336; padding: 4px;")
        self.reset_ui()

    def update_status(self, message):
        """更新状态消息"""
        self.status_label.setText(message)

    def reset_ui(self):
        """重置UI状态"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)

    def save_results(self):
        """保存结果到文件"""
        if not self.current_result:
            QMessageBox.warning(self, "警告", "没有可保存的结果")
            return

        # 选择保存目录
        save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if not save_dir:
            return

        save_path = Path(save_dir)
        timestamp = int(datetime.now().timestamp())

        try:
            # 检查是否是深度爬取结果（列表）
            if isinstance(self.current_result, list):
                # 深度爬取模式：保存多个页面
                saved_files = []
                
                # 合并所有页面的Markdown
                all_markdown = []
                all_html = []
                all_console = []
                
                for i, result in enumerate(self.current_result):
                    depth = result.metadata.get('depth', 0) if hasattr(result, 'metadata') else 0
                    score = result.metadata.get('score', 0) if hasattr(result, 'metadata') else 0
                    url = result.url if hasattr(result, 'url') else f"页面 {i+1}"
                    
                    separator = f"\n\n{'='*80}\n页面 {i+1}: {url}\n深度: {depth}"
                    if score > 0:
                        separator += f" | 评分: {score:.2f}"
                    separator += f"\n{'='*80}\n\n"
                    
                    if result.markdown and result.markdown.raw_markdown:
                        all_markdown.append(separator + result.markdown.raw_markdown)
                    
                    if result.html:
                        all_html.append(f"<!-- {separator} -->\n{result.html}")
                    
                    if result.console_messages:
                        for msg in result.console_messages:
                            all_console.append(f"[页面 {i+1}] {msg}")
                    
                    # 保存单个页面的结果（可选）
                    page_dir = save_path / f"page_{i+1}"
                    page_dir.mkdir(exist_ok=True)
                    
                    if result.markdown and result.markdown.raw_markdown:
                        page_md = page_dir / f"page_{i+1}.md"
                        page_md.write_text(result.markdown.raw_markdown, encoding="utf-8")
                        saved_files.append(str(page_md))
                    
                    if result.html:
                        page_html = page_dir / f"page_{i+1}.html"
                        page_html.write_text(result.html, encoding="utf-8")
                        saved_files.append(str(page_html))

                # 保存合并后的结果
                if all_markdown:
                    combined_md = save_path / f"combined_result_{timestamp}.md"
                    combined_md.write_text("\n".join(all_markdown), encoding="utf-8")
                    saved_files.append(str(combined_md))

                if all_html:
                    combined_html = save_path / f"combined_result_{timestamp}.html"
                    combined_html.write_text("\n\n".join(all_html), encoding="utf-8")
                    saved_files.append(str(combined_html))

                if all_console:
                    console_file = save_path / f"combined_console_{timestamp}.txt"
                    console_file.write_text("\n".join(all_console), encoding="utf-8")
                    saved_files.append(str(console_file))

                QMessageBox.information(
                    self,
                    "成功",
                    f"已保存 {len(self.current_result)} 个页面的结果到:\n{save_dir}\n\n"
                    f"共保存 {len(saved_files)} 个文件"
                )
            else:
                # 单页爬取模式：原有逻辑
                if self.current_result.markdown and self.current_result.markdown.raw_markdown:
                    md_file = save_path / f"result_{timestamp}.md"
                    md_file.write_text(self.current_result.markdown.raw_markdown, encoding="utf-8")

                # 保存HTML
                if self.current_result.html:
                    html_file = save_path / f"result_{timestamp}.html"
                    html_file.write_text(self.current_result.html, encoding="utf-8")

                # 保存控制台消息
                if self.current_result.console_messages:
                    console_file = save_path / f"console_{timestamp}.txt"
                    console_output = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(self.current_result.console_messages)])
                    console_file.write_text(console_output, encoding="utf-8")

                QMessageBox.information(self, "成功", f"结果已保存到:\n{save_dir}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存文件时发生错误:\n{str(e)}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用Fusion样式，更现代
    
    window = WebCrawlerGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

