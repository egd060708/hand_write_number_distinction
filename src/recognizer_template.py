"""
传统视觉方法：基于模板匹配的手写数字识别器
不依赖机器学习，使用平均模板 + 归一化互相关匹配

参考 PDF 实验三的流程：
  数据采集 → 预处理 → 特征提取 → 模板匹配 → 识别结果
"""

import cv2
import numpy as np
import os


class TemplateRecognizer:
    """
    模板匹配识别器

    1. 从 digits.png 中提取 5000 个样本（50行×100列，每格 20×20）
    2. 对每个数字 0-9 计算平均模板
    3. 识别时：ROI → 二值化 → resize 20×20 → 与10个模板做归一化互相关 → 取最大值
    """

    def __init__(self, digits_path: str = None):
        """
        Args:
            digits_path: digits.png 文件路径，默认从 ../model/digits.png 加载
        """
        if digits_path is None:
            digits_path = os.path.join(
                os.path.dirname(__file__), "..", "model", "digits.png"
            )

        # 加载训练图像（用 imdecode 避免中文路径问题）
        if not os.path.exists(digits_path):
            raise FileNotFoundError(f"模板图像不存在: {digits_path}")
        with open(digits_path, "rb") as f:
            data = np.frombuffer(f.read(), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(f"无法解码模板图像: {digits_path}")

        # 分割为 5000 个 20×20 的格子: 50 行 × 100 列
        cells = [np.hsplit(row, 100) for row in np.vsplit(img, 50)]
        samples = np.array(cells).reshape(-1, 400).astype(np.float32)  # (5000, 400)

        # 标签: 每 500 个为一类 (0~9)
        labels = np.repeat(np.arange(10), 500)  # [0,0,...,0, 1,1,...,1, ..., 9]

        # 为每个数字计算平均模板 (10, 400)
        self.templates = np.zeros((10, 400), dtype=np.float32)
        for digit in range(10):
            mask = (labels == digit)
            self.templates[digit] = samples[mask].mean(axis=0)

        # 保存 20×20 版本的模板（用于可视化/调试）
        self.template_images = self.templates.reshape(10, 20, 20)

        print(f"[TemplateRecognizer] 已加载 {len(samples)} 个样本, "
              f"生成 {len(self.templates)} 个平均模板")

    # ------------------------------------------------------------------
    # 预处理（与参考代码一致）
    # ------------------------------------------------------------------
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """边缘提取：灰度 → 膨胀 → 腐蚀 → absdiff → Sobel → 加权 → 阈值"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.dilate(gray, None, iterations=2)
        gray2 = cv2.erode(gray2, None, iterations=2)
        edges = cv2.absdiff(gray, gray2)
        x = cv2.Sobel(edges, cv2.CV_16S, 1, 0)
        y = cv2.Sobel(edges, cv2.CV_16S, 0, 1)
        absX = cv2.convertScaleAbs(x)
        absY = cv2.convertScaleAbs(y)
        dst = cv2.addWeighted(absX, 0.5, absY, 0.5, 0)
        _, dst = cv2.threshold(dst, 50, 255, cv2.THRESH_BINARY)
        return dst

    def find_digit_rois(self, binary: np.ndarray,
                        min_w: int = 10, min_h: int = 20) -> list:
        """轮廓检测 → ROI 筛选"""
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        rois = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w > min_w and h > min_h:
                rois.append((x, y, w, h))
        return rois

    # ------------------------------------------------------------------
    # 模板匹配识别
    # ------------------------------------------------------------------
    def predict_digit(self, roi_gray: np.ndarray, thresh_value: int = 50) -> tuple:
        """
        用归一化互相关匹配识别数字

        方法: 将 ROI 二值化 → 归一化 → 与每个数字的模板计算皮尔逊相关系数

        Args:
            roi_gray: ROI 灰度图
            thresh_value: 二值化阈值

        Returns:
            (digit, confidence, th) — 数字、置信度、预处理后的 20×20 图
        """
        _, th = cv2.threshold(roi_gray, thresh_value, 255, cv2.THRESH_BINARY)
        th = cv2.resize(th, (20, 20))
        sample = th.reshape(1, -1).astype(np.float32)

        # 归一化样本
        sample = self._normalize(sample)

        # 与 10 个模板计算皮尔逊相关系数
        best_digit = 0
        best_score = -1.0
        for d in range(10):
            score = self._pearson_corr(sample, self.templates[d])
            if score > best_score:
                best_score = score
                best_digit = d

        return best_digit, best_score, th

    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        """Z-score 归一化"""
        std = vec.std()
        if std < 1e-6:
            return vec - vec.mean()
        return (vec - vec.mean()) / std

    def _pearson_corr(self, a: np.ndarray, b: np.ndarray) -> float:
        """皮尔逊相关系数"""
        a_norm = self._normalize(a)
        b_norm = self._normalize(b.reshape(1, -1))
        return float(np.dot(a_norm, b_norm.T)[0, 0] / a.shape[1])

    # ------------------------------------------------------------------
    # 完整帧处理
    # ------------------------------------------------------------------
    def process_frame(self, frame: np.ndarray, thresh_value: int = 50):
        """处理一帧，返回检测结果列表"""
        binary = self.preprocess_frame(frame)
        rois = self.find_digit_rois(binary)

        # 用于识别的边缘图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.dilate(gray, None, iterations=2)
        gray2 = cv2.erode(gray2, None, iterations=2)
        edges = cv2.absdiff(gray, gray2)

        detections = []
        for (x, y, w, h) in rois:
            digit, conf, th = self.predict_digit(edges[y:y + h, x:x + w], thresh_value)
            detections.append({
                "x": x, "y": y, "w": w, "h": h,
                "digit": digit,
                "confidence": conf,
                "th_image": th,
            })

        return detections

    def draw_detections(self, frame: np.ndarray, detections: list) -> np.ndarray:
        """在帧上绘制检测框和结果"""
        result = frame.copy()
        for d in detections:
            x, y, w, h = d["x"], d["y"], d["w"], d["h"]
            digit = d["digit"]
            conf = d.get("confidence", 0)
            cv2.rectangle(result, (x, y), (x + w, y + h), (200, 200, 0), 2)
            label = f"{digit} ({conf:.2f})"
            cv2.putText(result, label, (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (127, 0, 255), 2)
        return result
