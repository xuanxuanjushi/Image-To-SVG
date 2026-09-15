# -*- coding: utf-8 -*-
"""图片转矢量 SVG —— 桌面版（支持线条、实心填充、彩色；可调线宽；暗色主题）。"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

# 让本脚本无论从哪个目录运行都能找到同目录下的 vectorizer.py
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import vectorizer


PREVIEW_MAX = 760

PRESETS = [
    ("线条 · 可调粗细", "line"),
    ("实心 · 轮廓+填充", "solid"),
]


DARK_QSS = """
QWidget { background-color: #1c2028; color: #e6e8ec; font-family: 'Microsoft YaHei','Segoe UI',sans-serif; }
QGroupBox { background-color: #232833; border: 1px solid #333a46; border-radius: 10px; margin-top: 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; color: #9aa3b2; padding: 0 4px; }
QPushButton { background-color: #2f6fed; color: #ffffff; border: 0; border-radius: 6px; padding: 7px 16px; }
QPushButton:hover { background-color: #3f7fff; }
QPushButton:disabled { background-color: #333a46; color: #6b7280; }
QComboBox { background-color: #14161c; border: 1px solid #333a46; border-radius: 6px; padding: 5px 8px; color: #e6e8ec; }
QComboBox QAbstractItemView { background-color: #232833; color: #e6e8ec; selection-background-color: #2f6fed; }
QSlider::groove:horizontal { height: 6px; background: #2a2f3a; border-radius: 3px; }
QSlider::handle:horizontal { background: #6fb7ff; width: 16px; margin: -5px 0; border-radius: 8px; }
QSlider::sub-page:horizontal { background: #2f6fed; border-radius: 3px; }
QLabel { background: transparent; }
"""


class ConverterWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.src_path: str | None = None
        self.svg_text = ""
        self.setAcceptDrops(True)
        self.setWindowTitle("图片转矢量 SVG · 线条/实心/彩色")
        self.resize(1220, 760)
        self._build_ui()

    def _mode(self) -> str:
        return PRESETS[self.preset.currentIndex()][1]

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        self.status = QLabel("请选择或拖入一张图片。支持线条、文字、Logo、截图；完全本地转换，不上传。")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        options = QGroupBox("转换设置")
        form = QFormLayout(options)
        form.setSpacing(8)

        self.preset = QComboBox()
        for name, _ in PRESETS:
            self.preset.addItem(name)
        self.preset.currentIndexChanged.connect(self._sync_controls)
        form.addRow("模式", self.preset)

        self.stroke = QSlider(Qt.Orientation.Horizontal)
        self.stroke.setRange(3, 80)
        self.stroke.setValue(14)
        self.stroke.setFixedWidth(220)
        self.stroke.valueChanged.connect(lambda v: self.stroke_val.setText(f"{v / 10:.1f}"))
        self.stroke_val = QLabel("1.4")
        stroke_row = QHBoxLayout()
        stroke_row.addWidget(self.stroke)
        stroke_row.addWidget(self.stroke_val)
        form.addRow("线宽(粗细)", stroke_row)

        self.sharpen = QSlider(Qt.Orientation.Horizontal)
        self.sharpen.setRange(0, 100)
        self.sharpen.setValue(0)
        self.sharpen.setFixedWidth(220)
        self.sharpen.valueChanged.connect(lambda v: self.sharpen_val.setText(str(v)))
        self.sharpen_val = QLabel("0")
        sharpen_row = QHBoxLayout()
        sharpen_row.addWidget(self.sharpen)
        sharpen_row.addWidget(self.sharpen_val)
        form.addRow("锐化(改善模糊)", sharpen_row)

        self.pick_btn = QPushButton("选择图片")
        self.pick_btn.clicked.connect(self.pick_image)
        self.convert_btn = QPushButton("转换")
        self.convert_btn.clicked.connect(self.convert)
        self.convert_btn.setEnabled(False)
        self.save_btn = QPushButton("导出 SVG")
        self.save_btn.clicked.connect(self.save_svg)
        self.save_btn.setEnabled(False)
        buttons = QHBoxLayout()
        buttons.addWidget(self.pick_btn)
        buttons.addWidget(self.convert_btn)
        buttons.addWidget(self.save_btn)
        buttons.addStretch(1)
        form.addRow("操作", buttons)
        root.addWidget(options)

        preview = QHBoxLayout()
        left = QGroupBox("原图")
        ll = QVBoxLayout(left)
        self.orig_label = QLabel("尚未选择图片")
        self.orig_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.orig_label.setMinimumSize(360, 380)
        ll.addWidget(self.orig_label)
        preview.addWidget(left)

        right = QGroupBox("矢量结果")
        rl = QVBoxLayout(right)
        self.result_label = QLabel("转换后显示在这里")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setMinimumSize(360, 380)
        self.result_label.setStyleSheet("color:#6b7280;")
        rl.addWidget(self.result_label)
        preview.addWidget(right)
        root.addLayout(preview, 1)

        footer = QLabel(
            "说明：线条模式把笔画抽成连续单线、可在 AI 里调粗细；实心模式先描边再填充；"
            "模糊图片可调高“锐化”。"
        )
        footer.setWordWrap(True)
        footer.setStyleSheet("color:#6b7280; font-size:12px;")
        root.addWidget(footer)

        self._sync_controls()

    def _sync_controls(self) -> None:
        mode = self._mode()
        self.stroke.setEnabled(mode in ("line", "solid"))
        self.stroke_val.setEnabled(self.stroke.isEnabled())

    def pick_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp *.gif *.tif *.tiff)"
        )
        if path:
            self._load_image(path)

    def _load_image(self, path: str) -> None:
        self.src_path = path
        pix = QPixmap(path)
        if not pix.isNull():
            self.orig_label.setPixmap(self._fit_pixmap(pix, PREVIEW_MAX))
        self.convert_btn.setEnabled(True)
        self.status.setText(f"已选择图片：{path}  （点击“转换”生成矢量）")

    @staticmethod
    def _fit_pixmap(pix: QPixmap, box: int) -> QPixmap:
        if pix.width() <= box and pix.height() <= box:
            return pix
        return pix.scaled(box, box, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def convert(self) -> None:
        if not self.src_path:
            return
        try:
            rgb = vectorizer.load_image(self.src_path)
            sharpen = self.sharpen.value() / 100.0 * 1.5
            mode = self._mode()
            if mode == "line":
                stroke_w = self.stroke.value() / 10.0
                svg = vectorizer.vectorize_line(rgb, sharpen=sharpen, stroke_width=stroke_w, smooth=True)
            elif mode == "solid":
                stroke_w = max(0.2, self.stroke.value() / 10.0 * 0.6)
                svg = vectorizer.vectorize_solid(rgb, sharpen=sharpen, outline=True, stroke_width=stroke_w)
            self.svg_text = svg
            pm = self._render_svg(svg)
            if pm is not None:
                self.result_label.setStyleSheet("")
                self.result_label.setPixmap(pm)
            else:
                self.result_label.setText("SVG 已生成，预览渲染失败；仍可导出。")
            self.save_btn.setEnabled(True)
            self.status.setText("转换完成。点击“导出 SVG”保存文件。")
        except Exception as exc:
            QMessageBox.critical(self, "转换失败", str(exc))

    @staticmethod
    def _render_svg(svg_text: str) -> QPixmap | None:
        renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
        if not renderer.isValid():
            return None
        vb = renderer.viewBoxF()
        if vb.width() <= 0 or vb.height() <= 0:
            vb = QRectF(0, 0, 640, 640)
        scale = min(PREVIEW_MAX / vb.width(), PREVIEW_MAX / vb.height())
        w = max(1, round(vb.width() * scale))
        h = max(1, round(vb.height() * scale))
        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        renderer.render(painter)
        painter.end()
        return QPixmap.fromImage(img)

    def save_svg(self) -> None:
        if not self.svg_text:
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存 SVG", "image.svg", "矢量图 (*.svg)")
        if not path:
            return
        try:
            Path(path).write_text(self.svg_text, encoding="utf-8")
            self.status.setText(f"已保存：{path}")
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self._load_image(path)


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_QSS)
    window = ConverterWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
