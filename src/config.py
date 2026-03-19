"""翻译管线配置"""

# Ollama 配置
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen3.5:9b"

# 翻译配置
MAX_CHARS_PER_CHUNK = 2000  # 每次发送给模型的最大字符数
REQUEST_TIMEOUT = 120  # Ollama 请求超时（秒）

# 爬取配置
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
