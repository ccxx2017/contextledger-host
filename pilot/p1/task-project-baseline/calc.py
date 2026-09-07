"""calc.py — 阶乘计算（方案A：lru_cache 缓存递归）"""

from functools import lru_cache


@lru_cache(maxsize=None)
def factorial(n):
    if n < 2:
        return 1
    return n * factorial(n - 1)


if __name__ == "__main__":
    print(factorial(5))
