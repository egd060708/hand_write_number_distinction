"""
工具函数：图像格式转换、绘制等
"""

import cv2
import numpy as np
from PIL import Image, ImageTk


def cv2_to_image_tk(frame: np.ndarray, target_width: int = None,
                    target_height: int = None) -> ImageTk.PhotoImage:
    """
    将 OpenCV BGR 图像转换为 tkinter 可显示的 PhotoImage

    Args:
        frame: BGR 格式的 numpy 图像数组
        target_width: 目标显示宽度 (None 表示保持比例)
        target_height: 目标显示高度 (None 表示保持比例)

    Returns:
        ImageTk.PhotoImage 对象
    """
    # BGR → RGB
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 转 PIL Image
    img = Image.fromarray(rgb)

    # 缩放
    if target_width is not None or target_height is not None:
        orig_w, orig_h = img.size
        if target_width is None:
            target_width = int(orig_w * target_height / orig_h)
        if target_height is None:
            target_height = int(orig_h * target_width / orig_w)
        img = img.resize((target_width, target_height), Image.LANCZOS)

    return ImageTk.PhotoImage(img)


def resize_frame_to_display(frame: np.ndarray,
                            max_width: int = 800,
                            max_height: int = 600) -> np.ndarray:
    """
    将帧缩放到适合显示的大小，保持宽高比

    Args:
        frame: 原始帧
        max_width: 最大显示宽度
        max_height: 最大显示高度

    Returns:
        缩放后的帧
    """
    h, w = frame.shape[:2]
    scale = min(max_width / w, max_height / h, 1.0)
    if scale < 1.0:
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(frame, (new_w, new_h))
    return frame
