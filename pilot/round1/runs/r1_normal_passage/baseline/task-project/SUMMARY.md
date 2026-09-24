# SUMMARY

## 任务
在 `greet.py` 中实现 `format_greeting(name)` 函数，返回 `'你好, {name}！'`。

## 实现过程
- 文件：`greet.py`
- 实现：单函数 `format_greeting(name)`，使用 f-string 格式化：`return f"你好, {name}！"`
- 无外部依赖，无副作用。

## 自测结果
调用两次：

```python
from greet import format_greeting
print(format_greeting('张三'))  # 你好, 张三！
print(format_greeting('李四'))  # 你好, 李四！
```

实际输出：

```
你好, 张三！
你好, 李四！
```

## 备注
- 首次运行输出乱码，为 Windows 控制台编码（GBK）问题，强制 UTF-8（`PYTHONIOENCODING=utf-8`）后输出正确，函数本身行为无误。
- 任务目标（实现 + 两次调用自测）已全部达成，收尾。
