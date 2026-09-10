"""api_client.py — 数据拉取客户端（按规范 v1 实现重试逻辑：最多 3 次指数退避）"""

import socket
import time
import urllib.error
import urllib.request
from typing import Optional

MAX_ATTEMPTS = 3
BASE_DELAY_SECONDS = 1.0


def fetch(url: str, max_attempts: int = MAX_ATTEMPTS) -> str:
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, socket.timeout, ConnectionError) as exc:
            last_exc = exc
            if attempt < max_attempts:
                time.sleep(BASE_DELAY_SECONDS * 2 ** (attempt - 1))
    raise last_exc
