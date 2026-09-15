# -*- coding: utf-8 -*-
"""位图转矢量 SVG 引擎 —— Potrace 描图式贝塞尔曲线。

- 线条模式：把墨迹(暗色)轮廓描成平滑闭合的贝塞尔路径，忠实还原原图。
- 实心模式：墨迹区域平滑填充。
- 彩色模式：颜色量化后逐色平滑描图。
- 锐化预处理：改善模糊/低对比图片。
"""
from __future__ import annotations

import numpy as np
import cv2
import potrace
from PIL import Image


MAX_DIM = 3200


def load_image(path: str, max_dim: int = MAX_DIM) -> np.ndarray:
    img = Image.open(path)
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    return np.array(img.convert("RGBA"))


def _unsharp(rgb: np.ndarray, amount: float) -> np.ndarray:
    if amount <= 0:
        return rgb
    blurred = cv2.GaussianBlur(rgb, (0, 0), 2.0)
    sharp = cv2.addWeighted(rgb, 1 + amount, blurred, -amount, 0)
    return np.clip(sharp, 0, 255).astype(np.uint8)


def _to_svg(width: int, height: int, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">{body}</svg>'
    )


def _ink_color(rgb: np.ndarray, mask: np.ndarray) -> str:
    rgb3 = rgb[..., :3] if rgb.ndim == 3 else np.stack([rgb] * 3, axis=-1)
    fg = rgb3[mask]
    if fg.size == 0:
        return "#171717"
    col = np.median(fg, axis=0).astype(int)
    return "#%02x%02x%02x" % tuple(col)


def _binarize_ink(gray: np.ndarray) -> np.ndarray:
    """返回黑色笔迹为 255 的二值图；若前景过大则反转，兼容亮底/暗底。"""
    _, b = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    if (b > 0).mean() > 0.55:
        b = 255 - b
    return b


def _potrace_d(
    mask: np.ndarray,
    alphamax: float = 1.0,
    opttolerance: float = 0.2,
    turdsize: int = 2,
) -> str:
    """把墨迹掩码(True=前景)描成平滑闭合的贝塞尔路径(自动处理孔洞)。"""
    bitmap = np.where(mask, 0, 255).astype(np.uint8)  # 前景给低值，potrace 描暗像素
    path = potrace.Bitmap(bitmap).trace(
        turdsize=turdsize,
        alphamax=alphamax,
        opttolerance=opttolerance,
    )
    parts = []
    for curve in path:
        segs = curve.segments
        if not segs:
            continue
        sp = curve.start_point
        d = f"M{sp.x:.2f} {sp.y:.2f}"
        for seg in segs:
            if seg.is_corner:
                d += (
                    f"L{seg.c.x:.2f} {seg.c.y:.2f}"
                    f"L{seg.end_point.x:.2f} {seg.end_point.y:.2f}"
                )
            else:
                d += (
                    f"C{seg.c1.x:.2f} {seg.c1.y:.2f} "
                    f"{seg.c2.x:.2f} {seg.c2.y:.2f} "
                    f"{seg.end_point.x:.2f} {seg.end_point.y:.2f}"
                )
        d += "Z"
        parts.append(d)
    return " ".join(parts)


def _fit_gradient(mask: np.ndarray, img: np.ndarray):
    """用“最亮与最暗像素”作为首尾，构造两色线性渐变。
    若区域亮度变化很小则视为纯色返回 None。"""
    ys, xs = np.nonzero(mask)
    n = len(xs)
    if n < 40:
        return None
    pts = np.stack([xs, ys], axis=1).astype(np.float32)
    cols = img[ys, xs].astype(np.float32)
    lum = cols @ np.array([0.299, 0.587, 0.114])
    lmin, lmax = float(lum.min()), float(lum.max())
    if lmax - lmin < 12:
        return None
    k = max(1, min(n // 40, 48))
    order = np.argsort(lum)
    lo_idx = order[:k]
    hi_idx = order[-k:]
    p_hi = pts[hi_idx].mean(axis=0)
    c_hi = np.median(cols[hi_idx], axis=0)
    p_lo = pts[lo_idx].mean(axis=0)
    c_lo = np.median(cols[lo_idx], axis=0)
    sat_hi = float(c_hi.max() - c_hi.min())
    sat_lo = float(c_lo.max() - c_lo.min())
    if abs(sat_hi - sat_lo) > 45:
        return None  # 亮/暗端色相差异过大 -> 不是同一渐变，视为纯色
    if float(np.linalg.norm(p_hi - p_lo)) < 3:
        return None
    return (p_hi[0], p_hi[1], p_lo[0], p_lo[1], c_hi, c_lo)


def vectorize_line(
    rgb: np.ndarray,
    sharpen: float = 0.0,
    stroke_width: float = 1.4,
    stroke_color: str | None = None,
    smooth: bool = True,
) -> str:
    rgb = _unsharp(rgb, sharpen)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    binm = _binarize_ink(gray)
    mask = binm > 0
    if stroke_color is None:
        stroke_color = _ink_color(rgb, mask)
    h, w = gray.shape
    if not mask.any():
        return _to_svg(w, h, "")
    d = _potrace_d(mask, alphamax=1.0)
    body = (
        f'<path d="{d}" fill="{stroke_color}" fill-rule="evenodd" '
        f'stroke="{stroke_color}" stroke-width="{stroke_width:.2f}" stroke-linejoin="round"/>'
    )
    return _to_svg(w, h, body)


def vectorize_solid(
    rgb: np.ndarray,
    sharpen: float = 0.0,
    fill_color: str | None = None,
    outline: bool = True,
    stroke_width: float = 1.0,
) -> str:
    rgb = _unsharp(rgb, sharpen)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    binm = _binarize_ink(gray)
    mask = binm > 0
    if fill_color is None:
        fill_color = _ink_color(rgb, mask)
    h, w = gray.shape
    if not mask.any():
        return _to_svg(w, h, "")
    d = _potrace_d(mask)
    attrs = f'fill-rule="evenodd" d="{d}" fill="{fill_color}"'
    if outline:
        attrs += f' stroke="{fill_color}" stroke-width="{stroke_width:.2f}" stroke-linejoin="round"'
    body = f"<path {attrs}/>"
    return _to_svg(w, h, body)


def vectorize_color(
    rgb: np.ndarray,
    sharpen: float = 0.0,
    ncolors: int = 16,
    outline: bool = False,
    stroke_width: float = 1.0,
) -> str:
    rgb = _unsharp(rgb, sharpen)
    rgb3 = rgb[..., :3].astype(np.uint8)
    h, w = rgb3.shape[:2]
    n_c = max(2, int(ncolors))
    qimg = Image.fromarray(rgb3).quantize(colors=n_c, method=Image.MEDIANCUT)
    q = np.array(qimg.convert("RGB"))
    flat = q.reshape(-1, 3)
    uniq, cnt = np.unique(flat, axis=0, return_counts=True)
    order = sorted(range(len(uniq)), key=lambda i: int(cnt[i]), reverse=True)
    bg = uniq[order[0]]
    bg_hex = "#%02x%02x%02x" % tuple(int(v) for v in bg)

    defs = []
    bodies = [f'<rect width="{w}" height="{h}" fill="{bg_hex}"/>']
    gidx = 0
    for i in order:
        col = uniq[i]
        if np.array_equal(col, bg):
            continue
        mask = np.all(q == col, axis=2)
        if mask.sum() < 6:
            continue
        d = _potrace_d(mask, alphamax=1.0)
        if not d:
            continue
        fill = None
        if mask.sum() >= 1500:
            grad = _fit_gradient(mask, rgb3)
            if grad is not None:
                x1, y1, x2, y2, c0, c1 = grad
                gid = f"g{gidx}"
                gidx += 1
                c0hex = "#%02x%02x%02x" % tuple(int(v) for v in np.clip(c0, 0, 255))
                c1hex = "#%02x%02x%02x" % tuple(int(v) for v in np.clip(c1, 0, 255))
                defs.append(
                    f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                    f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}">'
                    f'<stop offset="0" stop-color="{c0hex}"/>'
                    f'<stop offset="1" stop-color="{c1hex}"/></linearGradient>'
                )
                fill = f"url(#{gid})"
        if fill is None:
            fill = "#%02x%02x%02x" % tuple(int(v) for v in col)
        attrs = f'fill-rule="evenodd" d="{d}" fill="{fill}"'
        if outline:
            attrs += f' stroke="{fill}" stroke-width="{stroke_width:.2f}" stroke-linejoin="round"'
        bodies.append(f"<path {attrs}/>")

    body = ("<defs>" + "".join(defs) + "</defs>" + "".join(bodies)) if defs else "".join(bodies)
    return _to_svg(w, h, body)
