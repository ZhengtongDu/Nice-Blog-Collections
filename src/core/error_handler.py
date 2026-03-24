"""错误处理模块

统一错误日志格式，生成详细报告供调试和分析。
"""

import json
import traceback
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import OLLAMA_BASE_URL, OLLAMA_MODEL


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ERRORS_DIR = PROJECT_ROOT / "logs" / "errors"


class ErrorHandler:
    """错误处理器"""

    @staticmethod
    def log_error(
        error: Exception,
        context: dict,
        stage: str = "unknown"
    ) -> Path:
        """
        记录错误并返回日志文件路径

        Args:
            error: 异常对象
            context: 上下文信息（url, article_dir 等）
            stage: 失败阶段（crawl/translate/polish）

        Returns:
            日志文件路径
        """
        ERRORS_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = ERRORS_DIR / f"{timestamp}.log"

        # 生成文本报告
        report = ErrorHandler._generate_text_report(error, context, stage)
        log_path.write_text(report, encoding="utf-8")

        # 生成 JSON 报告（供 Claude Code 分析）
        json_path = ERRORS_DIR / f"{timestamp}.json"
        json_report = ErrorHandler._generate_json_report(error, context, stage)
        json_path.write_text(
            json.dumps(json_report, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        return log_path

    @staticmethod
    def _generate_text_report(
        error: Exception,
        context: dict,
        stage: str
    ) -> str:
        """生成文本格式的错误报告"""
        url = context.get('url', 'N/A')
        article_dir = context.get('article_dir', 'N/A')

        report = f"""=== 翻译失败报告 ===
时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
URL: {url}
失败阶段: {stage}
错误类型: {type(error).__name__}

--- 错误详情 ---
{str(error)}

--- 堆栈跟踪 ---
{traceback.format_exc()}

--- 环境信息 ---
Python: {platform.python_version()}
系统: {platform.system()} {platform.release()}
Ollama: {OLLAMA_BASE_URL}
模型: {OLLAMA_MODEL}

--- 中间产物 ---
文章目录: {article_dir}
"""

        # 检查中间文件是否存在
        if article_dir != 'N/A':
            article_path = Path(article_dir)
            if article_path.exists():
                original = article_path / "original.md"
                raw_translated = article_path / "raw_translated.md"
                translated = article_path / "translated.md"

                report += f"原文: {'已保存' if original.exists() else '未生成'}\n"
                report += f"机翻: {'已保存' if raw_translated.exists() else '未生成'}\n"
                report += f"润色: {'已保存' if translated.exists() else '未生成'}\n"

        # 建议操作
        report += "\n--- 建议操作 ---\n"
        if stage == "crawl":
            report += "1. 检查网络连接\n"
            report += "2. 确认 URL 可访问\n"
            report += "3. 检查是否需要登录或有反爬虫限制\n"
        elif stage == "translate":
            report += "1. 检查网络连接（Google Translate）\n"
            report += "2. 确认 Ollama 服务运行中\n"
            report += "3. 查看完整日志\n"
        elif stage == "polish":
            report += "1. 确认 Ollama 服务运行中\n"
            report += f"2. 检查模型 {OLLAMA_MODEL} 是否已加载\n"
            report += "3. 考虑增加 POLISH_TIMEOUT 配置\n"
            report += "4. 如已生成机翻版本，可手动润色\n"

        return report

    @staticmethod
    def _generate_json_report(
        error: Exception,
        context: dict,
        stage: str
    ) -> dict:
        """生成 JSON 格式的错误报告（供 Claude Code 分析）"""
        url = context.get('url', 'N/A')
        article_dir = context.get('article_dir', 'N/A')

        artifacts = {}
        if article_dir != 'N/A':
            article_path = Path(article_dir)
            if article_path.exists():
                artifacts = {
                    "original_md": str(article_path / "original.md"),
                    "raw_translated_md": str(article_path / "raw_translated.md"),
                    "translated_md": str(article_path / "translated.md"),
                }

        return {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "stage": stage,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "environment": {
                "python_version": platform.python_version(),
                "os": f"{platform.system()} {platform.release()}",
                "ollama_url": OLLAMA_BASE_URL,
                "ollama_model": OLLAMA_MODEL,
            },
            "artifacts": artifacts,
            "suggestions": ErrorHandler._get_suggestions(stage),
        }

    @staticmethod
    def _get_suggestions(stage: str) -> list[str]:
        """根据失败阶段返回建议"""
        if stage == "crawl":
            return [
                "检查网络连接",
                "确认 URL 可访问",
                "检查是否需要登录或有反爬虫限制",
            ]
        elif stage == "translate":
            return [
                "检查网络连接（Google Translate）",
                "确认 Ollama 服务运行中",
                "查看完整日志",
            ]
        elif stage == "polish":
            return [
                "确认 Ollama 服务运行中",
                f"检查模型 {OLLAMA_MODEL} 是否已加载",
                "考虑增加 POLISH_TIMEOUT 配置",
                "如已生成机翻版本，可手动润色",
            ]
        return ["查看详细日志"]
