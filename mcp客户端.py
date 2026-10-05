# -*- coding: utf-8 -*-
"""MCP 客户端封装：把异步的 FastMCP Client 包成同步函数。

为什么需要这一层：
  FastMCP 4.x 的 Client 只有异步接口（必须 async with + await），
  而 py41.py 的路由是同步的 def。

  同步路由是由 FastAPI 丢到线程池里跑的，那个线程上没有正在运行的事件循环，
  所以可以安全地用 asyncio.run() 把异步调用跑完再返回。

  开销：每次调用起一个事件循环，几十毫秒。医生端一次问答本来就要几秒，
  这点开销可以忽略——换来的是 py41.py 一行都不用改成 async。

对外只暴露两个同步函数：
  列工具()        工具清单，已经转成 DeepSeek function calling 要的格式
  调工具(名, 参数) 执行结果，字符串

对比改动前（py41.py 第 495-518 行）：
  那 24 行 if/elif 把"工具名 → 函数"硬编码死，加一个库就要改分支。
  现在加库 = 在 server.py 里写一个 @mcp.tool 函数，这里一行都不用动。
"""

import asyncio
import json
import os
import sys

_本目录 = os.path.dirname(os.path.abspath(__file__))
if _本目录 not in sys.path:
    sys.path.insert(0, _本目录)

from fastmcp import Client

if __package__:
    from mcp_倪海厦.server import mcp as 倪海厦server
else:
    # 直接跑这个文件时（py mcp客户端.py）没有包上下文
    from mcp_倪海厦.server import mcp as 倪海厦server

# 进程内缓存工具清单。工具是静态的，收一次就够。
_工具清单缓存 = None


def _跑(协程):
    """在同步代码里跑一个异步调用。"""
    return asyncio.run(协程)


def _转格式(工具):
    """MCP 的 Tool 对象 → DeepSeek function calling 的 tools 格式。"""
    # MCP SDK 里字段是 camelCase（inputSchema），但不同版本也可能给 snake_case，
    # 两种都兜一下，免得升个版本就炸。
    模式 = getattr(工具, "input_schema", None) or getattr(工具, "inputSchema", None)
    return {
        "type": "function",
        "function": {
            "name": 工具.name,
            "description": 工具.description or "",
            "parameters": 模式 or {"type": "object", "properties": {}},
        },
    }


def _取文本(结果):
    """把 call_tool 的返回对象取成字符串。"""
    数据 = getattr(结果, "data", None)
    if isinstance(数据, str):
        return 数据
    if 数据 is not None:
        return json.dumps(数据, ensure_ascii=False)

    # 没有 data 就退回拼 content 块
    块列表 = getattr(结果, "content", None) or []
    return "\n".join(getattr(块, "text", "") for 块 in 块列表)


def 列工具(重新拉=False):
    """列出 server 上的所有工具，返回 DeepSeek 要的 tools 格式。

    结果缓存住：工具是静态的，不用每次问都拉一遍。
    """
    global _工具清单缓存
    if _工具清单缓存 is not None and not 重新拉:
        return _工具清单缓存

    async def _列():
        async with Client(倪海厦server) as 客户端:
            return await 客户端.list_tools()

    原始 = _跑(_列())
    _工具清单缓存 = [_转格式(工具) for 工具 in 原始]
    return _工具清单缓存


def 调工具(名字, 参数):
    """调一个工具，返回文本结果。参数是 dict。"""

    async def _调():
        async with Client(倪海厦server) as 客户端:
            return await 客户端.call_tool(名字, 参数 or {})

    return _取文本(_跑(_调()))


# —————————— 自测 ——————————

if __name__ == "__main__":
    print("=" * 56)
    print("MCP 客户端自测（内存直连，不启子进程）")
    print("=" * 56)

    清单 = 列工具(重新拉=True)
    print(f"\n列到 {len(清单)} 个工具：")
    for 项 in 清单:
        print(f"  · {项['function']['name']} — {项['function']['description'].splitlines()[0]}")

    print("\n调一个试试：cha_jingfang(fangming='桂枝汤')")
    结果 = 调工具("cha_jingfang", {"fangming": "桂枝汤"})
    print("  " + 结果[:200] + ("……" if len(结果) > 200 else ""))
