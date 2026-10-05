# -*- coding: utf-8 -*-
"""医生端 agent：经方助手，工具走 MCP。

对比改动前（py41.py 第 467-569 行）：
  · 工具清单是写死的 24 行 dict
  · 分发是 24 行 if/elif（第 495-518 行）

现在：
  · 工具清单从 MCP server 的 list_tools() 拿
  · 分发就是协议本身——模型说要调哪个，就把名字和参数原样交给 client

  加一个新知识库 = 在 server.py 里写一个 @mcp.tool 函数。
  这个文件一个字都不用改。这就是"协议取代硬编码"的实际含义。

工具循环照搬 yaopin_agent.py 的写法（TOOL_FUNCS + 轮数上限），
只是把"名字→函数"的对照表换成了 MCP 调用。

有两件事这个 agent **刻意不做**，交给调用方（py41.py）：
  · 不落库 —— 记忆的读写是调用方的事，agent 只管算
  · 不截断历史 —— 历史多长由调用方定（py41.py 是每条截 300 字，
    防"查医案"那类长回答存进历史后累积撑爆上下文）

切回线上时别忘了这两件事，否则医生端会静默丢掉历史。
"""

import json

if __package__:
    import 提示词, mcp客户端
    from llm import 调AI
else:
    import os as _os
    import sys as _sys

    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    import 提示词, mcp客户端
    from llm import 调AI

# 最多来回几轮。防模型一直调工具不收敛——py41.py 原版也有同样的上限。
最多工具轮数 = 5


def 问经方(问题, 历史=None, 打印过程=False):
    """跑一轮医生端问答，返回 (最终回答, 本轮轨迹)。

    历史：[{"role": ..., "content": ...}, ...]，最近几轮对话（老的在前面）。
    """
    消息 = [{"role": "system", "content": 提示词.医生守则}]
    for 一轮 in (历史 or []):
        消息.append(一轮)
    消息.append({"role": "user", "content": 问题})

    工具清单 = mcp客户端.列工具()
    轨迹 = []

    for _ in range(最多工具轮数):
        第一条 = 调AI(消息, 工具=工具清单)

        # 没有 tool_calls = 模型觉得够了，这就是最终回答
        if not 第一条.get("tool_calls"):
            回答 = 第一条.get("content") or ""
            if not 回答.strip():
                # 模型没吐正文（只返回了空 content）——别把一片空白甩给医生。
                # py41.py 第 549-551 行原来就有这个兜底，新版第一稿漏了。
                回答 = "刚才没答上来，请把问题说得再具体一点，我重新查一次。"
            轨迹.append(("回答", "直接作答，没调工具"))
            return 回答, 轨迹

        # 模型要调工具：先把它的要求记进对话，再逐个执行、逐个回填
        消息.append({
            "role": "assistant",
            "content": None,
            "tool_calls": 第一条["tool_calls"],
        })

        for 调用 in 第一条["tool_calls"]:
            名字 = 调用["function"]["name"]
            try:
                参数 = json.loads(调用["function"]["arguments"])
            except Exception:
                # 模型偶尔给出空参数/乱参数——当作没参数，别让整个流程崩
                参数 = {}

            结果 = mcp客户端.调工具(名字, 参数)
            轨迹.append((名字, str(参数)))

            if 打印过程:
                print(f"  [工具] {名字}({参数}) → {结果[:60]}…")

            消息.append({
                "role": "tool",
                "tool_call_id": 调用["id"],
                "content": 结果,
            })
        # 回到循环开头，把工具结果交给模型，让它决定还要不要继续

    return "工具调了好几轮还没收敛，请把问题说得再具体一点。", 轨迹


# —————————— 自测 ——————————

if __name__ == "__main__":
    import sys as _s

    if "--dry" in _s.argv:
        # 只列工具，不问模型（不花钱）
        print("=" * 56)
        print("医生端工具清单（从 MCP server 实时拉取）")
        print("=" * 56)
        for 项 in mcp客户端.列工具(重新拉=True):
            函数 = 项["function"]
            print(f"\n· {函数['name']}")
            print(f"  {函数['description'].splitlines()[0]}")
            print(f"  参数：{list(函数['parameters'].get('properties', {}).keys())}")
    else:
        print("=" * 56)
        print("医生端问答（会真实调用模型，花几分钱）")
        print("=" * 56)
        问题 = "太阳中风，有汗恶风，用什么经方？组成是什么？"
        print("问：", 问题)
        print()
        回答, 轨迹 = 问经方(问题, 打印过程=True)
        print()
        print("答：", 回答)
        print()
        print("工具轨迹：", 轨迹)
