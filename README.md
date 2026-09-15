<h1 align="center">图片转矢量 SVG</h1>
<p align="center"><b>Image-To-SVG Vectorizer</b></p>
<p align="center">Windows 10/11 · Python + PySide6 · OpenCV / scikit-image / potracer</p>

> 把位图转成矢量 SVG 的本地桌面工具，提供单线描边、实心轮廓和彩色量化三种模式，全程本地处理，图片不上传。
>
> A local desktop tool that converts bitmaps into vector SVG files, with three modes: centreline stroke, solid outline plus fill, and colour-quantised fill. Everything runs offline.

> 关键词：图片转SVG、矢量化、描边、轮廓提取、Illustrator 路径 / Keywords: image to svg, vectorize, tracing, outline, potrace, Illustrator, PySide6

[简体中文](#功能) | [English](#english)

## 下载

免安装单文件版在 [Releases](https://github.com/xuanxuanjushi/Image-To-SVG/releases/latest) 页面：

| 文件 | 说明 |
| --- | --- |
| Image-To-SVG-1.0.0-windows.exe | 双击即用；如果 Windows 提示未知发布者，选择「更多信息 - 仍要运行」 |

## 功能

- **线条 · 可调粗细**：把线条和文字抽成连续单线，导出描边路径，可在 Illustrator 里继续调线宽
- **实心 · 轮廓+填充**：先描边再填充，能正确处理孔洞
- **彩色 / 彩色 · 精细**：颜色量化后逐色填充，适合图标和插画
- **锐化**：改善模糊图片的边缘质量
- 支持常见位图格式，导出标准 SVG，可直接导入 AI、Figma、CorelDRAW 等矢量软件

## 运行

推荐直接双击 `启动图片转矢量SVG.bat`；如果本机已装好依赖，也可以：

```bat
python run.py
```

手动安装依赖：

```bat
python -m pip install -r requirements.txt
```

## 项目结构

```
启动图片转矢量SVG.bat    启动脚本
image_to_svg_app.py      界面与交互
vectorizer.py            矢量化算法（骨架描边 + 轮廓填充）
run.py                   入口
ImageToSVG.spec          PyInstaller 打包配置
requirements.txt         依赖清单
```

## 说明

- 完全本地处理，图片不会上传到任何服务器
- 仓库里只保存源码；运行所需的依赖库（`libs`）、打包产物（`build` / `dist`）体积很大，没有放进仓库
- 打包好的免安装版本如果需要，可以另外生成

---

## English

**Image to SVG Vectorizer** turns bitmaps into clean vector SVG files, entirely offline.

### Modes

- **Line / adjustable width** — extracts continuous centrelines from line art and text, exports stroked paths you can restyle in Illustrator
- **Solid / outline + fill** — outlines first, then fills, so holes come out correctly
- **Colour / colour fine** — quantises colours and fills them layer by layer, good for icons and illustrations

Optional sharpening improves the edges of blurry source images. Output is standard SVG that opens in Illustrator, Figma, CorelDRAW and similar tools.

### Run

```bat
启动图片转矢量SVG.bat
```

or

```bat
python -m pip install -r requirements.txt
python run.py
```

### Notes

The repository contains source code only. Bundled runtimes (`libs`) and build output (`build`, `dist`) are large and intentionally excluded; a portable build can be produced on request.
