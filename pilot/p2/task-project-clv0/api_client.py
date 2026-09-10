"""api_client.py — 数据拉取客户端（规范 v1：最多 3 次，指数退避）"""

import time
import urllib.error
import urllib.request

RETRYABLE_ERRORS = (
    urllib.error.URLError,
    urllib.error.HTTPError,
    TimeoutError,
    ConnectionError,
)


def fetch(url: str, retries: int = 3, backoff: float = 1.0) -> str:
    if retries < 1:
        raise ValueError("retries must be >= 1")
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                return resp.read().decode("utf-8")
        except RETRYABLE_ERRORS as exc:
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(backoff * (2**attempt))
    raise last_exc
