# -*- coding: utf-8 -*-
"""模型调用的唯一出口。

改之前：py41.py 里"变向量/相似度"和两处 requests.post 是散的，
        换个模型得改好几处、还容易漏一处。
改之后：全项目只有这一个文件碰网络。换模型、加重试、记成本，都只改这里。

密钥从 config.py 读。新代码不再硬编码任何密钥。
（py41.py 第 49-52 行、_test_redline.py 第 10-11 行都是明文写死的，
  那是历史包袱，往后不跟。）
"""

import os
import sys

_本目录 = os.path.dirname(os.path.abspath(__file__))
if _本目录 not in sys.path:
    sys.path.insert(0, _本目录)

import json
import requests

from 密钥 import 取硅基密钥, 取deepseek密钥

API_KEY = 取deepseek密钥()
硅基密钥 = 取硅基密钥()

# 对话模型：和 py41.py 保持一致。
# 注意别跟 config.MODEL 走——那个值是 "deepseek-flash"，给别的项目用的。
对话模型 = "deepseek-v4-pro"

对话接口 = "https://api.deepseek.com/chat/completions"
向量接口 = "https://api.siliconflow.cn/v1/embeddings"
向量模型 = "BAAI/bge-m3"


def _对话头():
    return {"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}


# 单价表：元 / 百万 tokens。来源：DeepSeek 官方价格页（2026-10-05 查）。
# 这里按【空闲时段】价算；高峰时段（工作日 9-12 点、14-18 点）输入输出都翻倍。
# 加新模型就往这张表里加一行，别的地方不用改。
单价表 = {
    "deepseek-v4-pro": {"命中": 0.15, "未命中": 4.5, "输出": 13.5},
    "deepseek-flash": {"命中": 0.02, "未命中": 1.0, "输出": 4.0},
}


def 算钱(usage, 模型=None):
    """按 usage 算这一次调用花了多少钱（元）。

    钱 = 缓存命中的输入 × 命中价
       + 缓存未命中的输入 × 未命中价
       + 输出 × 输出价
    注意：输入的"命中/未命中"是两个价，差 30 倍——
          命中的意思是"这段内容上次已经算过，服务端有缓存"，所以便宜。
    """
    模型 = 模型 or 对话模型
    价 = 单价表.get(模型)
    if not 价:
        return 0.0

    命中 = usage.get("prompt_cache_hit_tokens", 0) or 0
    未命中 = usage.get("prompt_cache_miss_tokens")
    if 未命中 is None:
        未命中 = max((usage.get("prompt_tokens", 0) or 0) - 命中, 0)

    元 = (
        命中 * 价["命中"]
        + 未命中 * 价["未命中"]
        + (usage.get("completion_tokens", 0) or 0) * 价["输出"]
    ) / 1_000_000
    return 元


def 调AI(消息, 工具=None, 超时=120, 模型=None):
    """问一次模型，返回 message 对象。

    可能是纯文本（message["content"]），也可能带工具调用（message["tool_calls"]）。

    模型=None 就用默认的 pro；传 "deepseek-flash" 就走便宜那条。
    这就是【路由】的入口——由调用方决定这次用哪个模型（见 审核agent.py）。

    这里不做流式：流水线里每一步都要拿到**完整**结果才能决定下一步，
    流式只在最后"审核通过、吐给用户"那一层用（见 编排.py）。
    """
    用哪个模型 = 模型 or 对话模型
    数据 = {"model": 用哪个模型, "messages": 消息}
    if 工具:
        数据["tools"] = 工具
    响应 = requests.post(对话接口, json=数据, headers=_对话头(), timeout=超时)
    响应.raise_for_status()
    结果 = 响应.json()
    usage = 结果.get("usage", {})
    print(
        f"[钱] {算钱(usage, 用哪个模型):.4f} 元"
        f"　(输入 {usage.get('prompt_tokens')}　输出 {usage.get('completion_tokens')}"
        f"　模型 {用哪个模型})"
    )
    return 结果["choices"][0]["message"]


def 调AI流式(消息, 超时=120):
    """流式问一次模型，逐块 yield 文本。照搬 py41.py 第 209-222 行的解析写法。"""
    数据 = {"model": 对话模型, "messages": 消息, "stream": True}
    响应 = requests.post(对话接口, json=数据, headers=_对话头(), timeout=超时, stream=True)
    响应.raise_for_status()
    for 行 in 响应.iter_lines():
        if not 行:
            continue
        行 = 行.decode("utf-8")
        if not 行.startswith("data: "):
            continue
        内容块 = 行[6:]
        if 内容块 == "[DONE]":
            break
        块 = json.loads(内容块)
        内容 = 块["choices"][0]["delta"].get("content")
        if 内容:
            yield 内容


def 变向量(文字):
    """把一段文字变成向量（硅基流动 BAAI/bge-m3）。"""
    头 = {"Authorization": "Bearer " + 硅基密钥, "Content-Type": "application/json"}
    数据 = {"model": 向量模型, "input": 文字}
    响应 = requests.post(向量接口, json=数据, headers=头, timeout=60)
    响应.raise_for_status()
    return 响应.json()["data"][0]["embedding"]


def 相似度(a, b):
    """余弦相似度。照搬 py41.py 第 59 行的算法（不引 numpy，保持轻量）。

    比原版多一句除零保护：库里有空段落时原版会 ZeroDivisionError 崩掉。
    """
    点积 = sum(a[i] * b[i] for i in range(len(a)))
    长度a = sum(x * x for x in a) ** 0.5
    长度b = sum(x * x for x in b) ** 0.5
    if 长度a == 0 or 长度b == 0:
        return 0.0
    return 点积 / (长度a * 长度b)
