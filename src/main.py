"""
手写数字视频识别 — 主入口
启动 GUI 应用，支持在界面中切换识别方法 (KNN / 模板匹配 / CNN)

用法:
    python main.py
    python main.py --model path/to/model  # 指定默认模型路径
"""

import sys
import os
import argparse
import tkinter as tk

_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from gui import App


def main():
    parser = argparse.ArgumentParser(description="手写数字视频识别")
    parser.add_argument(
        "--model", type=str, default=None,
        help="覆盖默认模型路径 (高级用法)"
    )
    args = parser.parse_args()

    root = tk.Tk()
    app = App(root, model_override=args.model)
    root.mainloop()


if __name__ == "__main__":
    main()
