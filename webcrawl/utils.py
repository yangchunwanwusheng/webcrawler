"""工具函数模块"""

import markdown


def get_empty_html(message: str = "等待爬取结果...", is_dark_mode: bool = False) -> str:
    """获取空HTML模板"""
    bg_color = "#1e1e1e" if is_dark_mode else "#ffffff"
    text_color = "#e0e0e0" if is_dark_mode else "#666"
    
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


def render_markdown(markdown_content: str, is_dark_mode: bool = False) -> str:
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
    if is_dark_mode:
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

