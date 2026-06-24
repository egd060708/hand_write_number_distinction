"""
CNN 手写数字识别器
基于 PyTorch 训练的 2 层卷积神经网络，使用共享预处理流水线

训练代码: train_cnn.py
预处理: preprocessing.py (与 KNN 共用)
参考博客: https://blog.csdn.net/qq_45588019/article/details/120935828
"""

import os
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms

# 共享预处理
from preprocessing import preprocess_frame, find_digit_rois, prepare_roi


# ---------------------------------------------------------------------------
# CNN 网络定义（与 train_cnn.py 保持一致）
# ---------------------------------------------------------------------------
class CNN(nn.Module):
    def __init__(self):
        super(CNN, self).__init__()
        self.conv1 = nn.Sequential(
            nn.Conv2d(1, 10, kernel_size=5),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2),
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(10, 20, kernel_size=5),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2),
        )
        self.fc = nn.Sequential(
            nn.Linear(320, 50),
            nn.Linear(50, 10),
        )

    def forward(self, x):
        batch_size = x.size(0)
        x = self.conv1(x)
        x = self.conv2(x)
        x = x.view(batch_size, -1)
        x = self.fc(x)
        return x


# ---------------------------------------------------------------------------
# CNN 识别器
# ---------------------------------------------------------------------------
class CNNRecognizer:
    """CNN 识别器：使用 MNIST 训练的 CNN + 共享预处理"""

    def __init__(self, model_path: str = None):
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(__file__), "..", "model", "cnn_mnist.pth"
            )

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = CNN().to(self.device)

        if os.path.exists(model_path):
            self.model.load_state_dict(
                torch.load(model_path, map_location=self.device, weights_only=True)
            )
            self.model.eval()
            print(f"[CNN] 模型已加载: {os.path.basename(model_path)} "
                  f"(device={self.device})")
        else:
            raise FileNotFoundError(
                f"CNN 模型不存在: {model_path}\n"
                f"请先运行训练脚本: python train_cnn.py"
            )

        self.transform = transforms.Compose([
            transforms.ToTensor(),                        # [0,255] → [0.0, 1.0]
            transforms.Normalize((0.1307,), (0.3081,)),   # MNIST 标准化
        ])

    # ------------------------------------------------------------------
    # 帧处理（委托给共享预处理模块）
    # ------------------------------------------------------------------
    def preprocess_frame(self, frame):
        return preprocess_frame(frame)

    def find_digit_rois(self, binary, min_w=10, min_h=20):
        return find_digit_rois(binary, min_w, min_h)

    # ------------------------------------------------------------------
    # CNN 推理
    # ------------------------------------------------------------------
    def predict_digit(self, roi_gray):
        """
        用 CNN 识别单个 ROI（使用共享预处理，输出 28×28）
        """
        processed = prepare_roi(roi_gray, target_size=28)
        img = Image.fromarray(processed, mode='L')

        tensor = self.transform(img)                   # (1, 28, 28)
        tensor = tensor.unsqueeze(0).to(self.device)    # (1, 1, 28, 28)

        with torch.no_grad():
            output = self.model(tensor)
            probs = torch.softmax(output, dim=1)
            confidence, predicted = torch.max(probs, dim=1)

        return predicted.item(), confidence.item(), processed

    def process_frame(self, frame):
        """处理一帧"""
        binary = self.preprocess_frame(frame)
        rois = self.find_digit_rois(binary)

        import cv2
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        detections = []
        for (x, y, w, h) in rois:
            digit, conf, processed = self.predict_digit(gray[y:y + h, x:x + w])
            detections.append({
                "x": x, "y": y, "w": w, "h": h,
                "digit": digit,
                "confidence": conf,
                "th_image": processed,
            })
        return detections

    def draw_detections(self, frame, detections):
        """绘制检测框和结果"""
        import cv2
        result = frame.copy()
        for d in detections:
            x, y, w, h = d["x"], d["y"], d["w"], d["h"]
            cv2.rectangle(result, (x, y), (x + w, y + h), (0, 255, 0), 2)
            label = f"{d['digit']} ({d['confidence']:.2f})"
            cv2.putText(result, label, (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        return result
