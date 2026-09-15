# -*- coding: utf-8 -*-
"""启动入口：优先使用本项目 libs 文件夹里的依赖，再运行主界面。"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIBS = os.path.join(_HERE, "libs")

# 把本项目目录和本地依赖放到搜索路径最前面，确保用的是 libs 里的包。
if _LIBS not in sys.path:
    sys.path.insert(0, _LIBS)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

try:
    import image_to_svg_app
except Exception as exc:  # noqa: BLE001
    print("启动失败，依赖可能未安装完整：")
    print(f"  {type(exc).__name__}: {exc}")
    print("请检查本文件夹下是否存在 libs 目录。")
    raise SystemExit(1)


if __name__ == "__main__":
    raise SystemExit(image_to_svg_app.main())
