"""打包脚本

使用 py2app 将应用打包为 macOS .app 文件。

用法:
    python build_app.py py2app
"""

from setuptools import setup

APP = ['src/gui/app.py']
DATA_FILES = [
    ('prompts', ['src/prompts/polish_prompt.md']),
]
OPTIONS = {
    'argv_emulation': True,
    'packages': [
        'tkinter',
        'requests',
        'bs4',
        'yaml',
        'PIL',
        'html2text',
        'googletrans',
    ],
    'plist': {
        'CFBundleName': '博文翻译助手',
        'CFBundleDisplayName': '博文翻译助手',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSMinimumSystemVersion': '10.15',
    },
    'iconfile': None,  # 可选：添加 .icns 图标文件
}

setup(
    name='博文翻译助手',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
