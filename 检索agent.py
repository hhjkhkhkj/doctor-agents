# -*- coding: utf-8 -*-
"""② 检索 agent：从知识库里挑出最相关的几段。

职责：患者问题 → 同义词扩展 → 变向量 → 和库里每段比相似度 → 取 TopK。

为什么单独成一个 agent：
  检索质量直接决定回答质量。拆出来才能单独测——
  喂一批问题，看捞回来的段落对不对；
  以后换 embedding 模型、加 rerank，也只动这一个文件，不牵连别处。

比 py41.py 的原版多一件事：段落向量做了缓存。
  原版每次提问都把整库重算一遍向量（库是静态的，纯浪费）。
  缓存以段落文本为键，库里改了什么内容，键就变了，不会拿到旧向量。
"""

import os
import sys

_本目录 = os.path.dirname(os.path.abspath(__file__))
if _本目录 not in sys.path:
    sys.path.insert(0, _本目录)

from yiliao_tongyici import 展开同义词
from llm import 变向量, 相似度

# 段落文本 → 向量。模块级，进程内复用。
_段落向量缓存 = {}


def _段落向量(段):
    if 段 not in _段落向量缓存:
        _段落向量缓存[段] = 变向量(段)
    return _段落向量缓存[段]


def 检索(问题, 段落库, 取几段=3):
    """返回最相关的几段（字符串列表）。

    段落库：字符串列表。患者端传的是 SQLite 知识库，
            医生端传的是 nihaixia_*.py 里那些库。
    """
    if not 段落库:
        return []

    检索用问题 = 展开同义词(问题)     # 只给检索用；发给模型仍用患者原话
    问题向量 = 变向量(检索用问题)

    打分 = []
    for 段 in 段落库:
        打分.append((相似度(问题向量, _段落向量(段)), 段))
    打分.sort(key=lambda 对: 对[0], reverse=True)

    return [段 for 分, 段 in 打分[:取几段]]


def 检索带分数(问题, 段落库, 取几段=3):
    """同上，但连分数一起返回。调试检索质量时用。"""
    if not 段落库:
        return []

    检索用问题 = 展开同义词(问题)
    问题向量 = 变向量(检索用问题)

    打分 = sorted(
        ((相似度(问题向量, _段落向量(段)), 段) for 段 in 段落库),
        key=lambda 对: 对[0],
        reverse=True,
    )
    return 打分[:取几段]
