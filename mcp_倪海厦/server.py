# -*- coding: utf-8 -*-
r"""倪海厦知识库 · MCP Server

把 5 个知识库按 MCP 协议暴露成工具。

改之前：py41.py 第 495-518 行用 if/elif 把"工具名 → 函数"硬编码死，
        加一个新库要记得改那个分支，漏了运行时才炸。
改之后：每个库就是一个 @mcp.tool 函数。加新库 = 写一个函数，
        分发代码一行都不用动——客户端是用 list_tools() 拿清单的。

跑法：
  py mcp_倪海厦\server.py          # stdio（默认）
  py mcp_倪海厦\server.py --http   # HTTP 常驻

注意：下面每个函数的 docstring 就是"工具说明书"——
模型看到的工具描述就是从这儿生成的。别删，也别写废话。
函数体照搬 py41.py 第 341-395 行，行为保持一致。
"""

import os
import sys

_本目录 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # = 包根
if _本目录 not in sys.path:
    sys.path.insert(0, _本目录)

from fastmcp import FastMCP

from nihaixia_jingfang import 经方知识
from nihaixia_bencao import 本草知识
from nihaixia_yian import 医案知识
from nihaixia_zhenjiu import 针灸知识
from nihaixia_neijing import 内经知识

mcp = FastMCP("倪海厦知识库")


@mcp.tool
def cha_jingfang(fangming: str) -> str:
    """按方名查经方：组成、剂量、主治、禁忌。

    用在已经知道方名、要查它组成和剂量的时候。

    Args:
        fangming: 方剂名称，例如"桂枝汤"、"麻黄汤"、"小柴胡汤"
    """
    for 段 in 经方知识:
        if fangming in 段:
            return 段
    return "经方知识里没查到「" + fangming + "」"


@mcp.tool
def cha_bencao(yaoming: str) -> str:
    """按药名查单味药：性味、主治、用量、禁忌。

    用 startswith 精确匹配标题，避免"甘草"误命中"炙甘草"。

    Args:
        yaoming: 药材名，例如"桂枝"、"附子"、"甘草"
    """
    for 味 in 本草知识:
        if 味.startswith("【" + yaoming + "】"):
            return 味
    return "本草知识里没查到「" + yaoming + "」"


@mcp.tool
def cha_yian(guanjianci: str) -> str:
    """查类似医案：在 1257 例倪海厦医案里找含关键词的病例，最多 5 条。

    用在想看老师怎么治同样的病、同样的证的时候。

    Args:
        guanjianci: 病症或方剂关键词，例如"失眠"、"桂枝汤"
    """
    命中 = []
    for 条 in 医案知识:
        if guanjianci in 条:
            命中.append(条)
        if len(命中) >= 5:
            break
    if not 命中:
        return "医案库里没查到「" + guanjianci + "」"
    return "\n".join(命中)


@mcp.tool
def cha_zhenjiu(guanjianci: str) -> str:
    """查针灸取穴：按穴名、病症或经络查，最多返回 3 段。

    标题命中优先——这样问"头痛"会精准命中"头痛"那段取穴，而不是
    所有正文里顺带提过"头痛"的段落。

    Args:
        guanjianci: 穴名、病症或经络，例如"足三里"、"头痛"、"太阳经"
    """
    标题命中 = []
    内容命中 = []
    for 段 in 针灸知识:
        标题 = 段.split("\n")[0]
        if guanjianci in 标题:
            标题命中.append(段)
        elif guanjianci in 段:
            内容命中.append(段)
    结果 = 标题命中 + 内容命中
    if not 结果:
        return "针灸知识里没查到「" + guanjianci + "」"
    return "\n".join(结果[:3])


@mcp.tool
def cha_neijing(guanjianci: str) -> str:
    """查黄帝内经：按篇名或经文关键词查某篇讲解，只返回最相关的一篇。

    Args:
        guanjianci: 篇名或经文关键词，例如"上古天真论"、"阴阳"
    """
    标题命中 = []
    内容命中 = []
    for 段 in 内经知识:
        标题 = 段.split("\n")[0]
        if guanjianci in 标题:
            标题命中.append(段)
        elif guanjianci in 段:
            内容命中.append(段)
    结果 = 标题命中 + 内容命中
    if not 结果:
        return "内经知识里没查到「" + guanjianci + "」"
    return 结果[0]


if __name__ == "__main__":
    if "--http" in sys.argv:
        # 独立常驻模式，客户端用 URL 连
        mcp.run(transport="http", host="127.0.0.1", port=8901)
    else:
        # 默认 stdio：由客户端拉起子进程，走标准输入输出通信
        mcp.run()
