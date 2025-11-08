"""主窗口模块"""

from pathlib import Path
from typing import Optional
from datetime import datetime

from PyQt6.QtWidgets import (
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
    QStackedWidget,
    QFrame,
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView

from crawl4ai import BrowserConfig, CrawlerRunConfig

from webcrawl.worker import CrawlerWorker
from webcrawl.utils import get_empty_html, render_markdown
from webcrawl.config import build_deep_crawl_strategy, DEEP_CRAWL_AVAILABLE


class WebCrawlerGUI(QMainWindow):
    """网络爬虫GUI主窗口"""

    def __init__(self):
        super().__init__()
        self.worker: Optional[CrawlerWorker] = None
        self.current_result = None
        self.is_dark_mode = False  # 默认亮色模式
        
        # 加载设置
        self.settings = QSettings("WebCrawler", "WebCrawlerApp")
        self.default_save_path = self.settings.value("default_save_path", "", type=str)
        
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("网络爬虫工具 - Web Crawler")
        self.setGeometry(100, 100, 1400, 900)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建顶部导航栏
        self.create_top_bar(main_layout)

        # 创建页面堆栈
        self.pages_stack = QStackedWidget()
        main_layout.addWidget(self.pages_stack)

        # 创建各个页面
        self.create_basic_crawl_page()
        self.create_deep_crawl_page()
        self.create_settings_page()

        # 应用初始主题
        self.apply_theme()

    def create_top_bar(self, parent_layout):
        """创建顶部导航栏"""
        top_bar = QFrame()
        top_bar.setFixedHeight(60)
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-bottom: 2px solid #e0e0e0;
            }
        """)
        
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 10, 20, 10)
        top_layout.setSpacing(10)

        # 应用标题
        title_label = QLabel("🕷️ 网络爬虫工具")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333;
            }
        """)
        top_layout.addWidget(title_label)

        top_layout.addSpacing(30)

        # 导航按钮
        self.nav_buttons = {}
        
        nav_items = [
            ("基础爬取", "basic"),
            ("深度爬取", "deep"),
            ("设置", "settings"),
        ]

        for text, page_id in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setMinimumHeight(40)
            btn.setMinimumWidth(120)
            btn.clicked.connect(lambda checked, pid=page_id: self.switch_page(pid))
            self.nav_buttons[page_id] = btn
            top_layout.addWidget(btn)

        top_layout.addStretch()

        # 全局控制按钮（始终显示）
        self.global_start_button = QPushButton("开始爬取")
        self.global_start_button.setMinimumHeight(40)
        self.global_start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.global_start_button.clicked.connect(self.start_crawling)
        top_layout.addWidget(self.global_start_button)

        self.global_stop_button = QPushButton("停止")
        self.global_stop_button.setEnabled(False)
        self.global_stop_button.setMinimumHeight(40)
        self.global_stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.global_stop_button.clicked.connect(self.stop_crawling)
        top_layout.addWidget(self.global_stop_button)

        # 保存结果按钮
        self.save_button = QPushButton("保存结果")
        self.save_button.setEnabled(False)
        self.save_button.setMinimumHeight(40)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
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
        top_layout.addWidget(self.save_button)

        # 状态标签
        top_layout.addSpacing(10)
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 8px 16px;
                border-radius: 4px;
                background-color: #e8f5e9;
                color: #2e7d32;
                font-weight: bold;
                min-width: 80px;
            }
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(self.status_label)
        
        # 初始化状态样式
        self.update_status_style("就绪")

        parent_layout.addWidget(top_bar)

    def update_status_style(self, status_text: str):
        """更新状态标签样式"""
        if not hasattr(self, 'status_label'):
            return
        
        # 根据状态文本设置不同的样式
        if "错误" in status_text or "✗" in status_text or "失败" in status_text:
            # 错误状态 - 红色
            bg_color = "#ffebee" if not self.is_dark_mode else "#3d2729"
            text_color = "#c62828" if not self.is_dark_mode else "#ef5350"
        elif "完成" in status_text or "✓" in status_text or "成功" in status_text:
            # 完成状态 - 绿色
            bg_color = "#e8f5e9" if not self.is_dark_mode else "#1b5e20"
            text_color = "#2e7d32" if not self.is_dark_mode else "#66bb6a"
        elif "正在" in status_text or "⏳" in status_text or "爬取" in status_text:
            # 进行中状态 - 蓝色
            bg_color = "#e3f2fd" if not self.is_dark_mode else "#0d47a1"
            text_color = "#1565c0" if not self.is_dark_mode else "#42a5f5"
        elif "停止" in status_text or "已停止" in status_text:
            # 停止状态 - 橙色
            bg_color = "#fff3e0" if not self.is_dark_mode else "#e65100"
            text_color = "#e65100" if not self.is_dark_mode else "#ff9800"
        else:
            # 默认状态（就绪）- 灰色
            bg_color = "#f5f5f5" if not self.is_dark_mode else "#424242"
            text_color = "#616161" if not self.is_dark_mode else "#b0b0b0"
        
        self.status_label.setStyleSheet(f"""
            QLabel {{
                padding: 8px 16px;
                border-radius: 4px;
                background-color: {bg_color};
                color: {text_color};
                font-weight: bold;
                min-width: 80px;
            }}
        """)
        self.status_label.setText(status_text)

    def switch_page(self, page_id: str):
        """切换页面"""
        # 更新按钮状态
        for pid, btn in self.nav_buttons.items():
            btn.setChecked(pid == page_id)
        
        # 切换页面
        page_index_map = {
            "basic": 0,
            "deep": 1,
            "settings": 2,
        }
        
        if page_id in page_index_map:
            self.pages_stack.setCurrentIndex(page_index_map[page_id])

    def create_basic_crawl_page(self):
        """创建基础爬取页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # URL输入区域
        url_group = QGroupBox("目标URL")
        url_layout = QVBoxLayout()
        url_layout.addWidget(QLabel("网址（每行一个URL，支持批量爬取）:"))
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("https://www.example.com/\nhttps://www.example2.com/\nhttps://www.example3.com/")
        self.url_input.setText("https://www.osredm.com/")
        self.url_input.setMaximumHeight(120)
        self.url_input.setMinimumHeight(80)
        url_layout.addWidget(self.url_input)
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)

        # 基础配置选项区域
        config_group = QGroupBox("基础配置")
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

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # 结果区域
        self.create_results_section(layout)

        layout.addStretch()
        self.pages_stack.addWidget(page)

    def create_deep_crawl_page(self):
        """创建深度爬取页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # URL输入区域（共享）
        url_group = QGroupBox("目标URL")
        url_layout = QVBoxLayout()
        url_layout.addWidget(QLabel("网址（每行一个URL，支持批量爬取）:"))
        self.deep_url_input = QTextEdit()
        self.deep_url_input.setPlaceholderText("https://www.example.com/\nhttps://www.example2.com/\nhttps://www.example3.com/")
        self.deep_url_input.setText("https://www.osredm.com/")
        self.deep_url_input.setMaximumHeight(120)
        self.deep_url_input.setMinimumHeight(80)
        url_layout.addWidget(self.deep_url_input)
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)

        # 深度爬取配置
        deep_config_group = QGroupBox("深度爬取配置")
        deep_config_layout = QVBoxLayout()

        # 启用深度爬取
        enable_layout = QHBoxLayout()
        self.enable_deep_crawl_checkbox = QCheckBox("启用深度爬取")
        self.enable_deep_crawl_checkbox.setChecked(False)
        self.enable_deep_crawl_checkbox.toggled.connect(self._on_deep_crawl_toggled)
        enable_layout.addWidget(self.enable_deep_crawl_checkbox)
        enable_layout.addStretch()
        deep_config_layout.addLayout(enable_layout)

        # 深度爬取选项容器
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

        # 关键词评分器
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

        # 评分阈值
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

        deep_crawl_layout = QVBoxLayout()
        deep_crawl_layout.addWidget(self.deep_crawl_options)
        self.deep_crawl_options.setVisible(False)

        deep_config_layout.addLayout(deep_crawl_layout)
        deep_config_group.setLayout(deep_config_layout)
        layout.addWidget(deep_config_group)

        # 基础配置（在深度爬取页面也显示）
        basic_config_group = QGroupBox("基础配置")
        basic_config_layout = QVBoxLayout()

        browser_layout = QHBoxLayout()
        self.deep_headless_checkbox = QCheckBox("无头模式 (Headless)")
        self.deep_headless_checkbox.setChecked(False)
        browser_layout.addWidget(self.deep_headless_checkbox)
        
        self.deep_verbose_checkbox = QCheckBox("详细输出 (Verbose)")
        self.deep_verbose_checkbox.setChecked(True)
        browser_layout.addWidget(self.deep_verbose_checkbox)
        
        browser_layout.addStretch()
        basic_config_layout.addLayout(browser_layout)

        crawler_layout = QHBoxLayout()
        crawler_layout.addWidget(QLabel("延迟时间 (秒):"))
        self.deep_delay_spinbox = QDoubleSpinBox()
        self.deep_delay_spinbox.setRange(0.0, 60.0)
        self.deep_delay_spinbox.setValue(5.0)
        self.deep_delay_spinbox.setSingleStep(0.5)
        crawler_layout.addWidget(self.deep_delay_spinbox)

        self.deep_simulate_user_checkbox = QCheckBox("模拟用户行为")
        self.deep_simulate_user_checkbox.setChecked(True)
        crawler_layout.addWidget(self.deep_simulate_user_checkbox)

        self.deep_magic_checkbox = QCheckBox("魔法模式")
        self.deep_magic_checkbox.setChecked(True)
        crawler_layout.addWidget(self.deep_magic_checkbox)

        self.deep_wait_images_checkbox = QCheckBox("等待图片加载")
        self.deep_wait_images_checkbox.setChecked(True)
        crawler_layout.addWidget(self.deep_wait_images_checkbox)

        crawler_layout.addStretch()
        basic_config_layout.addLayout(crawler_layout)

        basic_config_group.setLayout(basic_config_layout)
        layout.addWidget(basic_config_group)

        layout.addStretch()
        self.pages_stack.addWidget(page)

    def create_settings_page(self):
        """创建设置页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 主题设置
        theme_group = QGroupBox("主题设置")
        theme_layout = QVBoxLayout()

        theme_info = QLabel("选择应用程序的主题模式")
        theme_info.setStyleSheet("color: #666; margin-bottom: 10px;")
        theme_layout.addWidget(theme_info)

        theme_button_layout = QHBoxLayout()
        self.theme_button = QPushButton("🌙 切换到暗色模式")
        self.theme_button.setMinimumHeight(50)
        self.theme_button.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #546e7a;
            }
        """)
        self.theme_button.clicked.connect(self.toggle_theme)
        theme_button_layout.addWidget(self.theme_button)
        theme_button_layout.addStretch()
        theme_layout.addLayout(theme_button_layout)

        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # 默认保存路径设置
        save_path_group = QGroupBox("默认保存路径")
        save_path_layout = QVBoxLayout()

        save_path_info = QLabel("设置爬取结果的默认保存位置")
        save_path_info.setStyleSheet("color: #666; margin-bottom: 10px;")
        save_path_layout.addWidget(save_path_info)

        path_input_layout = QHBoxLayout()
        self.default_save_path_input = QLineEdit()
        self.default_save_path_input.setPlaceholderText("未设置默认路径，保存时将弹出选择对话框")
        if self.default_save_path:
            self.default_save_path_input.setText(self.default_save_path)
        self.default_save_path_input.setReadOnly(True)
        path_input_layout.addWidget(self.default_save_path_input)

        browse_path_button = QPushButton("浏览...")
        browse_path_button.setMinimumHeight(40)
        browse_path_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        browse_path_button.clicked.connect(self.browse_default_save_path)
        path_input_layout.addWidget(browse_path_button)

        clear_path_button = QPushButton("清除")
        clear_path_button.setMinimumHeight(40)
        clear_path_button.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        clear_path_button.clicked.connect(self.clear_default_save_path)
        path_input_layout.addWidget(clear_path_button)

        save_path_layout.addLayout(path_input_layout)
        save_path_group.setLayout(save_path_layout)
        layout.addWidget(save_path_group)

        # 关于信息
        about_group = QGroupBox("关于")
        about_layout = QVBoxLayout()

        about_text = QLabel(
            "网络爬虫工具 v0.1.0\n\n"
            "基于 Crawl4AI 和 PyQt6 开发的图形化网络爬虫工具。\n"
            "支持单页爬取和深度爬取功能。"
        )
        about_text.setStyleSheet("color: #666; line-height: 1.6;")
        about_text.setWordWrap(True)
        about_layout.addWidget(about_text)

        about_group.setLayout(about_layout)
        layout.addWidget(about_group)

        layout.addStretch()
        self.pages_stack.addWidget(page)

    def create_results_section(self, parent_layout):
        """创建结果显示区域（共享）"""
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.progress_bar.setVisible(False)
        parent_layout.addWidget(self.progress_bar)

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
        self.markdown_preview.setHtml(get_empty_html(is_dark_mode=self.is_dark_mode))
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
        parent_layout.addWidget(results_group)

        # 默认显示基础爬取页面
        self.nav_buttons["basic"].setChecked(True)

    def apply_theme(self):
        """应用当前主题样式"""
        if self.is_dark_mode:
            self._apply_dark_theme()
        else:
            self._apply_light_theme()

    def _apply_light_theme(self):
        """应用亮色主题"""
        # 更新导航栏样式
        nav_bar_style = """
            QFrame {
                background-color: #f5f5f5;
                border-bottom: 2px solid #e0e0e0;
            }
            QPushButton:checked {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QPushButton:!checked {
                background-color: #e0e0e0;
                color: #333;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """
        if hasattr(self, 'nav_buttons'):
            for btn in self.nav_buttons.values():
                btn.setStyleSheet(nav_bar_style)
        
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
                width: 14px;
                height: 14px;
                border: 1.5px solid #ddd;
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
        
        # 更新状态标签样式
        if hasattr(self, 'status_label'):
            current_text = self.status_label.text()
            self.update_status_style(current_text)

    def _apply_dark_theme(self):
        """应用暗色主题"""
        # 更新导航栏样式
        nav_bar_style = """
            QFrame {
                background-color: #2d2d2d;
                border-bottom: 2px solid #404040;
            }
            QPushButton:checked {
                background-color: #66bb6a;
                color: white;
                font-weight: bold;
            }
            QPushButton:!checked {
                background-color: #404040;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """
        if hasattr(self, 'nav_buttons'):
            for btn in self.nav_buttons.values():
                btn.setStyleSheet(nav_bar_style)
        
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
                width: 14px;
                height: 14px;
                border: 1.5px solid #404040;
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
        
        # 更新状态标签样式
        if hasattr(self, 'status_label'):
            current_text = self.status_label.text()
            self.update_status_style(current_text)

    def toggle_theme(self):
        """切换主题"""
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()
        
        # 更新Markdown预览以应用新主题
        if self.current_result:
            if isinstance(self.current_result, list):
                # 深度爬取结果
                if self.current_result and hasattr(self.current_result[0], 'markdown'):
                    try:
                        all_markdown = []
                        for res in self.current_result:
                            if res.markdown and res.markdown.raw_markdown:
                                all_markdown.append(res.markdown.raw_markdown)
                        if all_markdown:
                            combined_markdown = "\n".join(all_markdown)
                            html_content = render_markdown(combined_markdown, self.is_dark_mode)
                            self.markdown_preview.setHtml(html_content)
                    except Exception:
                        self.markdown_preview.setHtml(get_empty_html("渲染失败，请查看Markdown源码", self.is_dark_mode))
            else:
                # 单页结果
                if self.current_result.markdown and self.current_result.markdown.raw_markdown:
                    try:
                        html_content = render_markdown(self.current_result.markdown.raw_markdown, self.is_dark_mode)
                        self.markdown_preview.setHtml(html_content)
                    except Exception:
                        self.markdown_preview.setHtml(get_empty_html("渲染失败，请查看Markdown源码", self.is_dark_mode))
        elif hasattr(self, 'markdown_preview'):
            # 如果没有结果，更新空HTML模板
            self.markdown_preview.setHtml(get_empty_html(is_dark_mode=self.is_dark_mode))

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
        return build_deep_crawl_strategy(
            enabled=self.enable_deep_crawl_checkbox.isChecked(),
            strategy_type=self.strategy_combo.currentText(),
            max_depth=self.max_depth_spinbox.value(),
            include_external=self.include_external_checkbox.isChecked(),
            max_pages=self.max_pages_spinbox.value(),
            url_patterns=self.url_pattern_input.text(),
            allowed_domains=self.allowed_domains_input.text(),
            blocked_domains=self.blocked_domains_input.text(),
            keywords=self.keywords_input.text(),
            scorer_weight=self.scorer_weight_spinbox.value(),
            score_threshold=self.score_threshold_spinbox.value(),
        )

    def start_crawling(self):
        """开始爬取"""
        # 根据当前页面获取URL和配置
        current_page_index = self.pages_stack.currentIndex()
        
        if current_page_index == 0:  # 基础爬取页面
            urls_text = self.url_input.toPlainText().strip()
            headless = self.headless_checkbox.isChecked()
            verbose = self.verbose_checkbox.isChecked()
            delay = self.delay_spinbox.value()
            simulate_user = self.simulate_user_checkbox.isChecked()
            magic = self.magic_checkbox.isChecked()
            wait_images = self.wait_images_checkbox.isChecked()
            enable_deep = False
            stream_mode = False
        elif current_page_index == 1:  # 深度爬取页面
            urls_text = self.deep_url_input.toPlainText().strip()
            headless = self.deep_headless_checkbox.isChecked()
            verbose = self.deep_verbose_checkbox.isChecked()
            delay = self.deep_delay_spinbox.value()
            simulate_user = self.deep_simulate_user_checkbox.isChecked()
            magic = self.deep_magic_checkbox.isChecked()
            wait_images = self.deep_wait_images_checkbox.isChecked()
            enable_deep = self.enable_deep_crawl_checkbox.isChecked()
            stream_mode = self.stream_results_checkbox.isChecked() if enable_deep else False
        else:  # 设置页面或其他
            QMessageBox.warning(self, "警告", "请在基础爬取或深度爬取页面开始爬取")
            return

        if not urls_text:
            QMessageBox.warning(self, "警告", "请输入有效的URL")
            return

        # 解析多行URL
        urls = []
        for line in urls_text.split('\n'):
            url = line.strip()
            if url:
                # 如果没有协议，添加https://
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                urls.append(url)
        
        if not urls:
            QMessageBox.warning(self, "警告", "请输入有效的URL")
            return
        
        # 更新URL输入框（规范化后的URL）
        normalized_urls = '\n'.join(urls)
        if current_page_index == 0:
            self.url_input.setPlainText(normalized_urls)
        else:
            self.deep_url_input.setPlainText(normalized_urls)
        
        # 如果只有一个URL，使用原来的逻辑
        if len(urls) == 1:
            url = urls[0]
        else:
            # 批量爬取模式
            self.start_batch_crawling(urls, current_page_index, headless, verbose, delay, 
                                     simulate_user, magic, wait_images, enable_deep, stream_mode)
            return

        # 更新UI状态
        self.global_start_button.setEnabled(False)
        self.global_stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.save_button.setEnabled(False)
        self.update_status_style("正在爬取...")

        # 清空之前的结果
        self.markdown_text.clear()
        self.html_text.clear()
        self.console_text.clear()
        self.markdown_preview.setHtml(get_empty_html(is_dark_mode=self.is_dark_mode))

        # 创建浏览器配置
        browser_config = BrowserConfig(
            headless=headless,
            verbose=verbose,
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
        deep_crawl_strategy = None
        if enable_deep:
            deep_crawl_strategy = build_deep_crawl_strategy(
                enabled=True,
                strategy_type=self.strategy_combo.currentText(),
                max_depth=self.max_depth_spinbox.value(),
                include_external=self.include_external_checkbox.isChecked(),
                max_pages=self.max_pages_spinbox.value(),
                url_patterns=self.url_pattern_input.text(),
                allowed_domains=self.allowed_domains_input.text(),
                blocked_domains=self.blocked_domains_input.text(),
                keywords=self.keywords_input.text(),
                scorer_weight=self.scorer_weight_spinbox.value(),
                score_threshold=self.score_threshold_spinbox.value(),
            )

        # 创建爬虫配置
        crawler_config = CrawlerRunConfig(
            js_code=[js_bypass],
            simulate_user=simulate_user,
            magic=magic,
            delay_before_return_html=delay,
            capture_console_messages=True,
            wait_for_images=wait_images,
            deep_crawl_strategy=deep_crawl_strategy,
            stream=stream_mode
        )

        # 创建工作线程
        self.worker = CrawlerWorker(url, browser_config, crawler_config)
        self.worker.finished.connect(self.on_crawl_finished)
        self.worker.error.connect(self.on_crawl_error)
        self.worker.status_update.connect(self.update_status)
        self.worker.start()

    def start_batch_crawling(self, urls, current_page_index, headless, verbose, delay,
                            simulate_user, magic, wait_images, enable_deep, stream_mode):
        """批量爬取多个URL"""
        self.batch_urls = urls
        self.batch_results = []
        self.batch_current_index = 0
        self.batch_is_stopped = False
        
        # 保存配置参数，以便错误时也能继续
        self.batch_config = {
            'current_page_index': current_page_index,
            'headless': headless,
            'verbose': verbose,
            'delay': delay,
            'simulate_user': simulate_user,
            'magic': magic,
            'wait_images': wait_images,
            'enable_deep': enable_deep,
            'stream_mode': stream_mode
        }
        
        # 更新UI状态
        self.global_start_button.setEnabled(False)
        self.global_stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(urls))
        self.progress_bar.setValue(0)
        self.save_button.setEnabled(False)
        self.update_status_style(f"批量爬取中 (0/{len(urls)})...")
        
        # 清空之前的结果
        self.markdown_text.clear()
        self.html_text.clear()
        self.console_text.clear()
        self.markdown_preview.setHtml(get_empty_html(is_dark_mode=self.is_dark_mode))
        
        # 开始爬取第一个URL
        self.crawl_next_url_in_batch(current_page_index, headless, verbose, delay,
                                    simulate_user, magic, wait_images, enable_deep, stream_mode)

    def crawl_next_url_in_batch(self, current_page_index, headless, verbose, delay,
                               simulate_user, magic, wait_images, enable_deep, stream_mode):
        """爬取批量列表中的下一个URL"""
        if self.batch_is_stopped or self.batch_current_index >= len(self.batch_urls):
            # 批量爬取完成或已停止
            self.on_batch_crawl_finished()
            return
        
        url = self.batch_urls[self.batch_current_index]
        self.update_status_style(f"批量爬取中 ({self.batch_current_index + 1}/{len(self.batch_urls)}): {url[:50]}...")
        self.progress_bar.setValue(self.batch_current_index)
        
        # 创建浏览器配置
        browser_config = BrowserConfig(
            headless=headless,
            verbose=verbose,
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
        deep_crawl_strategy = None
        if enable_deep:
            deep_crawl_strategy = build_deep_crawl_strategy(
                enabled=True,
                strategy_type=self.strategy_combo.currentText(),
                max_depth=self.max_depth_spinbox.value(),
                include_external=self.include_external_checkbox.isChecked(),
                max_pages=self.max_pages_spinbox.value(),
                url_patterns=self.url_pattern_input.text(),
                allowed_domains=self.allowed_domains_input.text(),
                blocked_domains=self.blocked_domains_input.text(),
                keywords=self.keywords_input.text(),
                scorer_weight=self.scorer_weight_spinbox.value(),
                score_threshold=self.score_threshold_spinbox.value(),
            )
        
        # 创建爬虫配置
        crawler_config = CrawlerRunConfig(
            js_code=[js_bypass],
            simulate_user=simulate_user,
            magic=magic,
            delay_before_return_html=delay,
            capture_console_messages=True,
            wait_for_images=wait_images,
            deep_crawl_strategy=deep_crawl_strategy,
            stream=stream_mode
        )
        
        # 创建工作线程
        self.worker = CrawlerWorker(url, browser_config, crawler_config)
        self.worker.finished.connect(lambda result: self.on_batch_url_finished(
            result, current_page_index, headless, verbose, delay,
            simulate_user, magic, wait_images, enable_deep, stream_mode))
        self.worker.error.connect(self.on_batch_url_error)
        self.worker.status_update.connect(lambda msg: self.update_status(
            f"批量爬取中 ({self.batch_current_index + 1}/{len(self.batch_urls)}): {msg}"))
        self.worker.start()

    def on_batch_url_finished(self, result, current_page_index, headless, verbose, delay,
                             simulate_user, magic, wait_images, enable_deep, stream_mode):
        """批量爬取中单个URL完成"""
        if not self.batch_is_stopped:
            # 保存结果
            if isinstance(result, list):
                # 深度爬取结果（列表）
                self.batch_results.extend(result)
            else:
                # 单页结果
                self.batch_results.append(result)
            
            self.batch_current_index += 1
            self.progress_bar.setValue(self.batch_current_index)
            
            # 继续爬取下一个URL
            self.crawl_next_url_in_batch(current_page_index, headless, verbose, delay,
                                        simulate_user, magic, wait_images, enable_deep, stream_mode)

    def on_batch_url_error(self, error_msg):
        """批量爬取中单个URL错误"""
        if not self.batch_is_stopped:
            # 记录错误，继续下一个
            self.batch_current_index += 1
            self.progress_bar.setValue(self.batch_current_index)
            if hasattr(self, 'batch_urls') and hasattr(self, 'batch_config'):
                if self.batch_current_index < len(self.batch_urls):
                    # 继续爬取下一个
                    self.update_status_style(f"批量爬取中 ({self.batch_current_index + 1}/{len(self.batch_urls)}): 上一个URL失败，继续...")
                    # 使用保存的配置继续爬取下一个URL
                    config = self.batch_config
                    self.crawl_next_url_in_batch(
                        config['current_page_index'],
                        config['headless'],
                        config['verbose'],
                        config['delay'],
                        config['simulate_user'],
                        config['magic'],
                        config['wait_images'],
                        config['enable_deep'],
                        config['stream_mode']
                    )
                else:
                    # 所有URL都处理完了
                    self.on_batch_crawl_finished()

    def on_batch_crawl_finished(self):
        """批量爬取完成"""
        # 更新进度条到100%
        if hasattr(self, 'batch_urls'):
            self.progress_bar.setValue(len(self.batch_urls))
        
        if not self.batch_results:
            QMessageBox.warning(self, "警告", "批量爬取未获取到任何结果")
            self.reset_ui()
            self.update_status_style("批量爬取完成（无结果）")
            return
        
        # 合并所有结果并显示
        self.on_crawl_finished(self.batch_results)
        self.update_status_style(f"批量爬取完成 ({len(self.batch_results)} 个结果)")

    def stop_crawling(self):
        """停止爬取"""
        # 检查是否是批量爬取模式
        if hasattr(self, 'batch_urls') and self.batch_urls:
            self.batch_is_stopped = True
            if self.worker and self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait()
            self.update_status_style(f"已停止 (已完成 {self.batch_current_index}/{len(self.batch_urls)})")
            # 如果有部分结果，显示它们
            if self.batch_results:
                self.on_crawl_finished(self.batch_results)
            else:
                self.reset_ui()
        else:
            # 单URL爬取模式
            if self.worker and self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait()
                self.update_status_style("已停止")
                self.reset_ui()

    def reset_ui(self):
        """重置UI状态"""
        self.global_start_button.setEnabled(True)
        self.global_stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)

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
                    html_content = render_markdown(combined_markdown, self.is_dark_mode)
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
                self.markdown_preview.setHtml(get_empty_html("未获取到Markdown内容", self.is_dark_mode))

            if all_html:
                self.html_text.setPlainText("\n\n".join(all_html))
            else:
                self.html_text.setPlainText("未获取到HTML内容")

            if all_console:
                self.console_text.setPlainText("\n".join(all_console))
            else:
                self.console_text.setPlainText("未捕获到控制台消息")

            self.current_result = result
            self.update_status_style(f"爬取完成 - 共 {total_pages} 个页面")
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
                    html_content = render_markdown(markdown_content, self.is_dark_mode)
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
                self.markdown_preview.setHtml(get_empty_html("未获取到Markdown内容", self.is_dark_mode))

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

            self.update_status_style("爬取完成")
            self.reset_ui()
            self.save_button.setEnabled(True)

    def on_crawl_error(self, error_msg):
        """爬取错误回调"""
        QMessageBox.critical(self, "错误", f"爬取过程中发生错误:\n{error_msg}")
        self.update_status_style(f"错误: {error_msg}")
        self.reset_ui()

    def update_status(self, message):
        """更新状态消息"""
        self.update_status_style(message)

    def reset_ui(self):
        """重置UI状态"""
        self.global_start_button.setEnabled(True)
        self.global_stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)

    def browse_default_save_path(self):
        """浏览并设置默认保存路径"""
        current_path = self.default_save_path_input.text() if self.default_save_path_input.text() else ""
        save_dir = QFileDialog.getExistingDirectory(self, "选择默认保存目录", current_path)
        if save_dir:
            self.default_save_path = save_dir
            self.default_save_path_input.setText(save_dir)
            self.settings.setValue("default_save_path", save_dir)
            QMessageBox.information(self, "成功", f"默认保存路径已设置为:\n{save_dir}")

    def clear_default_save_path(self):
        """清除默认保存路径"""
        self.default_save_path = ""
        self.default_save_path_input.clear()
        self.default_save_path_input.setPlaceholderText("未设置默认路径，保存时将弹出选择对话框")
        self.settings.setValue("default_save_path", "")
        QMessageBox.information(self, "成功", "默认保存路径已清除")

    def _sanitize_filename(self, filename: str) -> str:
        """将URL转换为安全的文件名"""
        # 移除协议
        filename = filename.replace("https://", "").replace("http://", "")
        # 替换不安全的字符
        unsafe_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
        # 限制长度
        if len(filename) > 50:
            filename = filename[:50]
        return filename

    def _save_single_url_result(self, result, url_dir: Path, url_index: int, url: str):
        """保存单个URL的单页结果"""
        timestamp = int(datetime.now().timestamp())
        
        # 保存Markdown
        if result.markdown and result.markdown.raw_markdown:
            md_file = url_dir / f"result_{timestamp}.md"
            md_file.write_text(result.markdown.raw_markdown, encoding="utf-8")
        
        # 保存HTML
        if result.html:
            html_file = url_dir / f"result_{timestamp}.html"
            html_file.write_text(result.html, encoding="utf-8")
        
        # 保存控制台消息
        if result.console_messages:
            console_file = url_dir / f"console_{timestamp}.txt"
            console_output = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(result.console_messages)])
            console_file.write_text(console_output, encoding="utf-8")
        
        # 保存URL信息
        info_file = url_dir / "url_info.txt"
        info_content = f"URL: {url}\n"
        info_content += f"状态码: {result.status_code}\n"
        info_content += f"成功: {'是' if result.success else '否'}\n"
        info_content += f"爬取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        info_file.write_text(info_content, encoding="utf-8")

    def _save_single_url_deep_result(self, results: list, url_dir: Path, url_index: int, url: str):
        """保存单个URL的深度爬取结果"""
        timestamp = int(datetime.now().timestamp())
        
        # 为每个页面创建子文件夹
        all_markdown = []
        all_html = []
        all_console = []
        
        for i, result in enumerate(results):
            page_dir = url_dir / f"page_{i+1}"
            page_dir.mkdir(exist_ok=True)
            
            depth = result.metadata.get('depth', 0) if hasattr(result, 'metadata') else 0
            score = result.metadata.get('score', 0) if hasattr(result, 'metadata') else 0
            page_url = result.url if hasattr(result, 'url') else f"页面 {i+1}"
            
            # 保存单个页面的结果
            if result.markdown and result.markdown.raw_markdown:
                page_md = page_dir / f"page_{i+1}.md"
                page_md.write_text(result.markdown.raw_markdown, encoding="utf-8")
                all_markdown.append(result.markdown.raw_markdown)
            
            if result.html:
                page_html = page_dir / f"page_{i+1}.html"
                page_html.write_text(result.html, encoding="utf-8")
                all_html.append(result.html)
            
            if result.console_messages:
                for msg in result.console_messages:
                    all_console.append(f"[页面 {i+1}] {msg}")
            
            # 保存页面信息
            page_info = page_dir / "page_info.txt"
            page_info_content = f"页面URL: {page_url}\n"
            page_info_content += f"深度: {depth}\n"
            if score > 0:
                page_info_content += f"评分: {score:.2f}\n"
            page_info_content += f"状态码: {result.status_code}\n"
            page_info_content += f"成功: {'是' if result.success else '否'}\n"
            page_info.write_text(page_info_content, encoding="utf-8")
        
        # 保存合并后的结果
        if all_markdown:
            combined_md = url_dir / f"combined_{timestamp}.md"
            combined_md.write_text("\n\n".join(all_markdown), encoding="utf-8")
        
        if all_html:
            combined_html = url_dir / f"combined_{timestamp}.html"
            combined_html.write_text("\n\n".join(all_html), encoding="utf-8")
        
        if all_console:
            console_file = url_dir / f"combined_console_{timestamp}.txt"
            console_file.write_text("\n".join(all_console), encoding="utf-8")
        
        # 保存URL信息
        info_file = url_dir / "url_info.txt"
        info_content = f"URL: {url}\n"
        info_content += f"总页面数: {len(results)}\n"
        info_content += f"成功页面数: {sum(1 for r in results if r.success)}\n"
        info_content += f"爬取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        info_file.write_text(info_content, encoding="utf-8")

    def save_results(self):
        """保存结果到文件"""
        if not self.current_result:
            QMessageBox.warning(self, "警告", "没有可保存的结果")
            return

        # 使用默认保存路径，如果没有则弹出选择对话框
        if self.default_save_path and Path(self.default_save_path).exists():
            save_dir = self.default_save_path
        else:
            current_path = self.default_save_path if self.default_save_path else ""
            save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录", current_path)
            if not save_dir:
                return

        save_path = Path(save_dir)
        timestamp = int(datetime.now().timestamp())

        try:
            # 检查是否是批量爬取结果
            if hasattr(self, 'batch_urls') and self.batch_urls and isinstance(self.current_result, list):
                # 批量爬取模式：每个URL单独存储
                saved_files = []
                batch_dir = save_path / f"batch_crawl_{timestamp}"
                batch_dir.mkdir(exist_ok=True)
                
                # 为每个URL创建单独的文件夹
                url_index = 0
                for url in self.batch_urls:
                    # 创建URL文件夹（使用安全的文件名）
                    url_safe_name = self._sanitize_filename(url)
                    url_dir = batch_dir / f"url_{url_index + 1}_{url_safe_name}"
                    url_dir.mkdir(exist_ok=True)
                    
                    # 找到对应的结果（可能是单个结果或深度爬取的多个结果）
                    result_for_url = None
                    if url_index < len(self.current_result):
                        result_for_url = self.current_result[url_index]
                    
                    if result_for_url:
                        # 保存单个URL的结果
                        if isinstance(result_for_url, list):
                            # 深度爬取结果（列表）
                            self._save_single_url_deep_result(result_for_url, url_dir, url_index + 1, url)
                        else:
                            # 单页结果
                            self._save_single_url_result(result_for_url, url_dir, url_index + 1, url)
                    
                    url_index += 1
                
                # 保存批量爬取的汇总信息
                summary_file = batch_dir / "batch_summary.txt"
                summary_content = f"批量爬取汇总\n"
                summary_content += f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                summary_content += f"总URL数: {len(self.batch_urls)}\n"
                summary_content += f"成功结果数: {len(self.current_result)}\n\n"
                summary_content += "URL列表:\n"
                for i, url in enumerate(self.batch_urls):
                    status = "✓" if i < len(self.current_result) else "✗"
                    summary_content += f"{i+1}. {status} {url}\n"
                summary_file.write_text(summary_content, encoding="utf-8")
                saved_files.append(str(summary_file))
                
                QMessageBox.information(
                    self,
                    "成功",
                    f"已保存批量爬取结果到:\n{batch_dir}\n\n"
                    f"共 {len(self.batch_urls)} 个URL，每个URL的结果已单独存储"
                )
                return
            
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

