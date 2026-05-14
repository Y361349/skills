import logging
import re
from datetime import datetime
from pathlib import Path
from .config import config

LOG_DIR = config.log_dir
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"grok_search_{datetime.now().strftime('%Y%m%d')}.log"

logger = logging.getLogger("grok_search")
logger.setLevel(getattr(logging, config.log_level))

file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setLevel(getattr(logging, config.log_level))

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

_SECRET_PATTERNS = [
    # 常见 API Key 形态：sk-...
    (re.compile(r"\bsk-[A-Za-z0-9_-]{10,}\b"), "sk-*****"),
    # 环境变量/文本里可能出现的 GROK_API_KEY=...
    (re.compile(r"(GROK_API_KEY\s*=\s*)([^\s\r\n]+)", re.IGNORECASE), r"\1*****"),
    # HTTP Header: Authorization: Bearer ...
    (re.compile(r"(Authorization:\s*Bearer\s+)([^\s\r\n]+)", re.IGNORECASE), r"\1*****"),
    (re.compile(r"(Bearer\s+)(sk-[A-Za-z0-9_-]{10,})", re.IGNORECASE), r"\1sk-*****"),
]


def _redact_secrets(message: str) -> str:
    if not message:
        return message
    text = str(message)
    for pattern, repl in _SECRET_PATTERNS:
        text = pattern.sub(repl, text)
    return text


async def log_info(ctx, message: str, is_debug: bool = False):
    safe_message = _redact_secrets(message)
    if is_debug:
        logger.info(safe_message)
        
    if ctx:
        await ctx.info(safe_message)
