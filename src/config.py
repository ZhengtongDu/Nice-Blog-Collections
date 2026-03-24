"""翻译管线配置"""

# Ollama 配置
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen3.5:9b"

# 翻译配置
MAX_CHARS_PER_CHUNK = 2000  # 每次发送给模型的最大字符数
REQUEST_TIMEOUT = 300  # Ollama 单段翻译超时（秒）
POLISH_TIMEOUT = 600  # Ollama 润色超时（秒），润色内容更长需要更多时间

# Google Translate 重试配置
GOOGLE_TRANSLATE_MAX_RETRIES = 3  # 最大重试次数
GOOGLE_TRANSLATE_RETRY_DELAY = 2  # 重试间隔（秒），每次翻倍

# 爬取配置
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# GUI 配置
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700
LOG_MAX_LINES = 1000  # 日志框最大行数
AUTO_SCROLL = True    # 自动滚动到底部
