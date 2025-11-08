"""应用程序启动入口"""

import sys

from PyQt6.QtWidgets import QApplication

from webcrawl.main_window import WebCrawlerGUI


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用Fusion样式，更现代
    
    window = WebCrawlerGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
