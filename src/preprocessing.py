"""
共享预处理模块 — KNN 和 CNN 通用

职责:
  1. 帧级预处理: 边缘提取 → 二值图（用于 ROI 检测）
  2. ROI 检测: 轮廓查找 → 筛选候选区域
  3. ROI 预处理: 将原始灰度 ROI 转换为 MNIST 风格的标准化图像
     - OTSU 自适应二值化
     - 形态学闭运算 + 膨胀
     - 居中 + 保持宽高比 padding
     - resize 到目标尺寸

KNN 使用 20×20，CNN 使用 28×28，其他步骤完全一致。
"""

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# 帧级预处理：边缘检测（用于 ROI 发现，所有方法共用）
# ---------------------------------------------------------------------------
def preprocess_frame(frame: np.ndarray, thresh: int = 50) -> np.ndarray:
    """
    对原始帧进行边缘提取，得到二值图用于 ROI 检测

    流水线: 灰度 → 膨胀 → 腐蚀 → absdiff → Sobel → 加权 → 阈值
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.dilate(gray, None, iterations=2)
    gray2 = cv2.erode(gray2, None, iterations=2)
    edges = cv2.absdiff(gray, gray2)
    x = cv2.Sobel(edges, cv2.CV_16S, 1, 0)
    y = cv2.Sobel(edges, cv2.CV_16S, 0, 1)
    absX = cv2.convertScaleAbs(x)
    absY = cv2.convertScaleAbs(y)
    dst = cv2.addWeighted(absX, 0.5, absY, 0.5, 0)
    _, dst = cv2.threshold(dst, thresh, 255, cv2.THRESH_BINARY)
    return dst


# ---------------------------------------------------------------------------
# ROI 检测
# ---------------------------------------------------------------------------
def find_digit_rois(binary: np.ndarray,
                    min_w: int = 10, min_h: int = 20) -> list:
    """
    在二值边缘图中检测数字候选区域

    Returns:
        list of (x, y, w, h) 元组
    """
    contours, _ = cv2.findContours(
        binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    rois = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w > min_w and h > min_h:
            rois.append((x, y, w, h))
    return rois


# ---------------------------------------------------------------------------
# 去噪辅助函数
# ---------------------------------------------------------------------------
def _remove_small_blobs(binary: np.ndarray,
                        min_area_ratio: float = 0.25) -> np.ndarray:
    """
    连通域面积过滤：移除小块噪点，保留主体数字

    策略:
        1. 找到面积最大的连通域（主体数字）
        2. 保留面积 >= 最大面积 * min_area_ratio 的区域（默认 25%）
        3. 对于只有 1-2 个连通域的情况，只保留最大的那个

    这能有效去除划痕、斑点等噪声，同时保留数字的主体结构。

    Args:
        binary: 二值图 (白字黑底, uint8)
        min_area_ratio: 保留阈值（相对于最大连通域，默认 25%）

    Returns:
        去噪后的二值图
    """
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )
    if num_labels <= 1:
        return binary

    areas = stats[1:, cv2.CC_STAT_AREA]
    if len(areas) == 0:
        return binary

    max_area = areas.max()
    threshold = max_area * min_area_ratio

    cleaned = np.zeros_like(binary)
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] >= threshold:
            cleaned[labels == i] = 255

    return cleaned


# ---------------------------------------------------------------------------
# ROI 预处理: 对齐 MNIST 风格
# ---------------------------------------------------------------------------
def prepare_roi(roi_gray: np.ndarray, target_size: int = 28,
                dilate: bool = True, denoise: bool = True) -> np.ndarray:
    """
    将原始灰度 ROI 转换为 MNIST 风格的标准化图像

    步骤:
        1. OTSU 自适应二值化（白字黑底）
        2. [去噪] 连通域面积过滤，去除划痕等小块噪点
        3. 形态学闭运算填充缝隙
        4. [可选] 膨胀加粗笔划（CNN=True, KNN=False）
        5. 裁剪紧贴数字
        6. 保持宽高比 pad 到正方形，居中
        7. 添加外边距（~20%）
        8. resize 到 target_size × target_size

    Args:
        roi_gray: 原始灰度 ROI (uint8, 0-255)
        target_size: 目标尺寸，推荐 28
        dilate: 是否膨胀加粗
        denoise: 是否启用连通域去噪
    """
    # ---- 1. OTSU 二值化 ----
    _, binary = cv2.threshold(
        roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # 确保白字黑底（与 MNIST 一致）
    if binary.mean() > 128:
        binary = cv2.bitwise_not(binary)

    # ---- 2. 去噪：连通域面积过滤 ----
    if denoise:
        binary = _remove_small_blobs(binary)

    # ---- 3. 形态学处理：闭运算填充缝隙，可选膨胀 ----
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    if dilate:
        binary = cv2.dilate(binary, kernel, iterations=1)

    # ---- 3. 裁剪紧贴数字 ----
    coords = cv2.findNonZero(binary)
    if coords is None:
        return np.zeros((target_size, target_size), dtype=np.uint8)

    x, y, w, h = cv2.boundingRect(coords)

    # 扩展边距
    margin = max(2, min(w, h) // 10)
    x = max(0, x - margin)
    y = max(0, y - margin)
    w = min(binary.shape[1] - x, w + 2 * margin)
    h = min(binary.shape[0] - y, h + 2 * margin)

    cropped = binary[y:y + h, x:x + w]

    # ---- 4. 保持宽高比，pad 到正方形，居中 ----
    size = max(w, h)
    square = np.zeros((size, size), dtype=np.uint8)
    x_offset = (size - w) // 2
    y_offset = (size - h) // 2
    square[y_offset:y_offset + h, x_offset:x_offset + w] = cropped

    # ---- 5. 添加外边距 ----
    pad_size = max(2, int(size * 0.2))
    padded_size = size + 2 * pad_size
    padded = np.zeros((padded_size, padded_size), dtype=np.uint8)
    padded[pad_size:pad_size + size, pad_size:pad_size + size] = square

    # ---- 6. resize 到目标尺寸 ----
    result = cv2.resize(padded, (target_size, target_size),
                        interpolation=cv2.INTER_AREA)

    return result
