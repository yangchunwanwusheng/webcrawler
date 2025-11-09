WebCrawler 使用指南

1. 运行环境与目录结构
- 系统要求：Windows 64 位。
- 可执行文件位置：dist/WebCrawler/WebCrawler.exe。
- 目录结构（onedir 模式，运行时必须保持该文件夹结构）：
  - dist/WebCrawler/
    - WebCrawler.exe
    - 依赖的动态库和资源文件（由打包工具自动生成）
    - README.md（随应用附带）
    - docs/（随应用附带，用于说明文档中的图片）

2. 启动应用
- 将 dist/WebCrawler 整个文件夹保留在同一位置。
- 双击 dist/WebCrawler/WebCrawler.exe 即可启动图形界面。
- 首次启动可能较慢，属于正常现象。

2.1 运行时环境变量（可选，提升稳定性）
- 在部分 Windows 环境下，QtWebEngine 子进程可能因沙盒限制无法启动；建议在运行前设置：
  - PowerShell：
    - $env:QTWEBENGINE_DISABLE_SANDBOX = '1'
- Playwright 浏览器路径（包内不包含浏览器二进制，需指向本机安装位置）：
  - PowerShell：
    - $env:PLAYWRIGHT_BROWSERS_PATH = "$env:LOCALAPPDATA\ms-playwright"
- 上述设置仅影响当前终端会话；若需永久生效，可在系统环境变量中配置。

3. 界面与主要功能
- 顶部导航：基础爬取、深度爬取、设置。
- 基础爬取：
  - 支持单页或批量（每行一个 URL）输入目标地址。
  - 可配置无头模式、详细输出、延迟时间、模拟用户行为、魔法模式、等待图片加载。
  - 结果预览区显示 Markdown 渲染后的页面内容。
  - 点击“保存结果”可保存为 Markdown、HTML 和控制台日志文本。
- 深度爬取：
  - 可选择爬取策略：BFS、DFS、BestFirst。
  - 支持最大深度、最大页面数、是否包含外部链接、流式输出等。
  - 支持 URL 过滤（模式匹配、允许域名、阻止域名）。
  - 支持关键词评分器（BestFirst 可按关键词相关性优先爬取）。
- 批量爬取：
  - 在输入框中每行一个 URL，应用将逐个爬取并显示进度。
  - 保存时会为每个 URL 生成单独文件夹与结果文件。
- 设置：
  - 主题切换：亮色与暗色。
  - 默认保存路径：在保存结果时自动使用该路径。

4. 关于浏览器安装（爬取功能依赖 Playwright 浏览器）
- 本应用使用 Crawl4AI 与 Playwright 进行页面访问。首次在未安装浏览器的环境下进行爬取时，可能提示需要安装浏览器（例如 Chromium）。
- 按需安装方式（二选一）：
  A. 在本项目虚拟环境中安装（推荐给开发者）：
     - 激活虚拟环境：\.\.venv\Scripts\Activate.ps1
     - 安装浏览器：uv run python -m playwright install chromium
  B. 在任意已有 Python 环境中安装：
     - pip install playwright
     - python -m playwright install chromium
- 该安装仅需执行一次。若后续爬取仍报错，请检查网络或防火墙设置。

5. 保存结果与文件位置
- 单页爬取默认保存 Markdown、HTML、控制台日志到你选择的目录。
- 深度爬取可保存多个页面的合并结果以及分页面结果文件。
- 可在“设置”页面配置默认保存路径，提高操作效率。

6. 常见问题与排查
- 启动缓慢或首次运行时间较长：属于正常情况，onedir 模式会加载多个依赖文件。
- 无法显示网页内容：确保 dist/WebCrawler 目录中的 QtWebEngine 相关文件未被移动或删除。
- 爬取报错提示未安装浏览器：按第 4 节说明安装 Playwright 浏览器。
- 批量爬取进度异常或中断：检查网络状况与目标站点的访问限制。

7. 开发者参考（如需再次打包）
前置要求：本项目依赖 Crawl4AI 与 Playwright。首次开发环境需安装浏览器（例如 Chromium）：
- 激活虚拟环境：.\.venv\Scripts\Activate.ps1
- 安装浏览器：uv run python -m playwright install chromium

打包步骤（使用 uv 和 PyInstaller）：
1) 创建并激活虚拟环境（如尚未创建）：
   - uv venv
   - .\.venv\Scripts\Activate.ps1
2) 安装项目依赖：
   - uv sync
3) 安装打包工具：
   - uv pip install pyinstaller
4) 生成发行版（onedir 模式）：
   - uv run pyinstaller --name=WebCrawler --windowed --onedir --noconfirm \
     --collect-all=PyQt6 --collect-all=crawl4ai --collect-all=patchright --collect-all=playwright --collect-all=fake_useragent \
     --hidden-import=PyQt6.QtWebEngineCore --hidden-import=PyQt6.QtWebEngineWidgets \
     --add-data "README.md;." --add-data "docs;docs" \
     main.py

说明：上述命令确保 PyQt6 WebEngine、crawl4ai、patchright、playwright 以及 fake_useragent 的数据资源被完整收集，避免运行时缺失导致的异常退出。
