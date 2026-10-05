# -*- coding: utf-8 -*-
"""AI 医生助理的多 agent 流水线。

设计文档见同目录 README.md。

导入约定：
  包内模块之间一律用相对导入（from 状态 import ...）；
  外部入口（评测\跑评测.py 等）把本目录加进 sys.path 再直接 import。

这个 __init__ 干一件实事：把 python-study 加进 sys.path，
  好让本目录的模块能 import 到 密钥.py、nihaixia_*.py、
  yiliao_tongyici.py 这些放在上一层的文件。
  没有这三行，从任何地方 import 这个包都会报 ModuleNotFoundError: config。
"""

import os
import sys

_本目录 = os.path.dirname(os.path.abspath(__file__))
if _本目录 not in sys.path:
    sys.path.insert(0, _本目录)
