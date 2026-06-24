"""
KNN 手写数字识别器
基于 OpenCV KNN，使用 MNIST 数据集 + 共享预处理流水线

训练脚本: train_knn.py
预处理: preprocessing.py (与 CNN 共用)
"""

import cv2
import numpy as np
import os

# 共享预处理
from preprocessing import preprocess_frame, find_digit_rois, prepare_roi


class DigitRecognizer:
    """KNN 识别器：使用 MNIST 训练的 KNN 模型 + 改进的预处理"""

    def __init__(self, model_path: str = None):
        """
        Args:
            model_path: .npz 模型文件路径
                        默认先用 MNIST 训练的 knn_mnist.npz，
                        不存在则回退到参考仓库的 data.npz
        """
        if model_path is None:
            # 优先使用 MNIST 训练的模型
            mnist_model = os.path.join(
                os.path.dirname(__file__), "..", "model", "knn_mnist.npz"
            )
            fallback = os.path.join(
                os.path.dirname(__file__), "..", "model", "data.npz"
            )
            model_path = mnist_model if os.path.exists(mnist_model) else fallback

        self.knn = cv2.ml.KNearest_create()

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"KNN 模型不存在: {model_path}\n"
                f"请先运行训练脚本: python train_knn.py"
            )

        with np.load(model_path) as data:
            self.train = data["train"]
            self.trainLabel = data["trainLabel"]
        self.knn.train(self.train, cv2.ml.ROW_SAMPLE, self.trainLabel)
        print(f"[KNN] 模型已加载: {os.path.basename(model_path)} "
              f"({self.train.shape[0]} 样本, {self.train.shape[1]} 维)")

    # ------------------------------------------------------------------
    # 帧处理（委托给共享预处理模块）
    # ------------------------------------------------------------------
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        return preprocess_frame(frame)

    def find_digit_rois(self, binary: np.ndarray,
                        min_w: int = 10, min_h: int = 20) -> list:
        return find_digit_rois(binary, min_w, min_h)

    # ------------------------------------------------------------------
    # KNN 识别
    # ------------------------------------------------------------------
    def predict_digit(self, roi_gray: np.ndarray) -> tuple:
        """
        用 KNN 识别单个 ROI（使用改进的共享预处理）

        Args:
            roi_gray: 原始灰度 ROI

        Returns:
            (digit, processed_20x20)
        """
        # 共享预处理：不膨胀（保留细节），输出 28×28
        processed = prepare_roi(roi_gray, target_size=28, dilate=False)

        # KNN 需要 float32 输入
        feat = processed.reshape(1, -1).astype(np.float32)
        _, result, _, _ = self.knn.findNearest(feat, k=5)

        return int(result[0][0]), processed

    def process_frame(self, frame: np.ndarray):
        """
        处理一帧：检测 ROI → 对每个 ROI 用 KNN 识别
        """
        binary = self.preprocess_frame(frame)
        rois = self.find_digit_rois(binary)

        # 使用原始灰度图（非边缘图！）
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        detections = []
        for (x, y, w, h) in rois:
            digit, processed = self.predict_digit(gray[y:y + h, x:x + w])
            detections.append({
                "x": x, "y": y, "w": w, "h": h,
                "digit": digit,
                "th_image": processed,
            })

        return detections

    def draw_detections(self, frame: np.ndarray, detections: list) -> np.ndarray:
        """绘制检测框和结果"""
        result = frame.copy()
        for d in detections:
            x, y, w, h = d["x"], d["y"], d["w"], d["h"]
            cv2.rectangle(result, (x, y), (x + w, y + h), (200, 200, 0), 2)
            cv2.putText(result, str(d["digit"]), (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (127, 0, 255), 2)
        return result
