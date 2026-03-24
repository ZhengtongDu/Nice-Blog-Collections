#!/usr/bin/env python3
"""
启动脚本

解决 Python 3.13 兼容性问题
"""

import sys

# Python 3.13 移除了 cgi 模块，需要添加兼容性补丁
if sys.version_info >= (3, 13):
    import html

    cgi_module = sys.modules.get('cgi')
    if cgi_module is None:
        cgi_module = type(sys)('cgi')
        sys.modules['cgi'] = cgi_module

    def _parse_header(line: str):
        parts = [part.strip() for part in line.split(';')]
        main_value = parts[0].lower() if parts else ''
        params = {}

        for part in parts[1:]:
            if '=' not in part:
                continue
            key, value = part.split('=', 1)
            params[key.lower().strip()] = value.strip().strip('"')

        return main_value, params

    cgi_module.escape = html.escape
    cgi_module.parse_header = _parse_header

# 启动应用
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from gui.app import main

if __name__ == "__main__":
    main()
