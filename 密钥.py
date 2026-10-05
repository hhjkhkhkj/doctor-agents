# -*- coding: utf-8 -*-
r"""读 API 密钥 —— 优先环境变量，其次同目录的 config.py。

【为什么不直接写在代码里】
    密钥写进代码 = 一旦传上 GitHub 就等于公开了。
    爬虫会扫 GitHub 上的 sk- 开头字符串，几分钟内就会被盗刷。

【两种设置办法，选一个】

    办法一（推荐）：设环境变量

        Windows PowerShell（当前窗口有效）：
            $env:SILICONFLOW_API_KEY = "sk-你的硅基流动密钥"
            $env:DEEPSEEK_API_KEY     = "sk-你的deepseek密钥"

        Mac / Linux：
            export SILICONFLOW_API_KEY=sk-你的密钥
            export DEEPSEEK_API_KEY=sk-你的密钥

    办法二：在本文件旁边建一个 config.py，写：

        # config.py  —— 这个文件不要传上 GitHub！
        硅基密钥 = "sk-你的硅基流动密钥"
        API_KEY  = "sk-你的deepseek密钥"

    （目录里有个 config.example.py，照着改名就行）
"""

import os


def _取(环境变量名, config里的名字, 服务名):
    值 = os.environ.get(环境变量名, "").strip()
    if 值:
        return 值
    try:
        import config
        值 = getattr(config, config里的名字, "")
        if 值:
            return 值
    except ImportError:
        pass
    raise SystemExit(
        f"\n❌ 没找到{服务名}的密钥。两种设置办法（选一个）：\n"
        f"   1) 设环境变量 {环境变量名}=sk-xxxx\n"
        f"      Windows PowerShell：$env:{环境变量名} = \"sk-xxxx\"\n"
        f"   2) 在本文件旁边建一个 config.py，写上：{config里的名字} = \"sk-xxxx\"\n"
        f"      （参考同目录的 config.example.py）\n"
    )


def 取硅基密钥():
    """硅基流动的密钥。语音识别和语音合成都用它。"""
    return _取("SILICONFLOW_API_KEY", "硅基密钥", "硅基流动")


def 取deepseek密钥():
    """DeepSeek 的密钥。客服大脑回答问题时用。"""
    return _取("DEEPSEEK_API_KEY", "API_KEY", "DeepSeek")
