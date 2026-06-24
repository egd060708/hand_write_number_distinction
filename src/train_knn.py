"""
KNN 手写数字识别 — 训练脚本
使用 MNIST 数据集 + 共享预处理流水线，训练 OpenCV KNN 模型

与 CNN 使用相同的预处理（OTSU、形态学、居中 padding），确保推理时一致

用法:
    python train_knn.py                  # 默认参数
    python train_knn.py --samples 10000  # 使用更多训练样本
"""

import os
import sys
import argparse
import numpy as np
import cv2
from torchvision import datasets, transforms

# 确保能找到同目录模块
_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from preprocessing import prepare_roi


def load_mnist(data_root: str, train: bool = True, max_samples: int = None):
    """加载 MNIST 数据集，返回 (images, labels)"""
    transform = transforms.ToTensor()
    dataset = datasets.MNIST(
        root=data_root, train=train,
        transform=transform, download=True
    )
    images = []
    labels = []
    n = len(dataset) if max_samples is None else min(len(dataset), max_samples)
    for i in range(n):
        img_tensor, label = dataset[i]
        # 转为 uint8 灰度图 (28×28, 白字黑底)
        img = (img_tensor.squeeze().numpy() * 255).astype(np.uint8)
        images.append(img)
        labels.append(label)
    return np.array(images), np.array(labels)


def preprocess_for_knn(img: np.ndarray) -> np.ndarray:
    """
    对 MNIST 图片应用与推理时相同的预处理
    关键: dilate=False，与 CNN 区分（KNN 保留细节更准）
    """
    processed = prepare_roi(img, target_size=28, dilate=False)
    return processed


def main():
    parser = argparse.ArgumentParser(description="KNN MNIST 训练")
    parser.add_argument("--samples", type=int, default=20000,
                        help="训练样本数 (默认 20000)")
    parser.add_argument("--model-dir", type=str, default=None,
                        help="模型保存目录")
    args = parser.parse_args()

    # 数据路径
    data_root = os.path.join(os.path.dirname(__file__), "..", "data", "mnist")

    # 加载 MNIST
    print("[KNN Train] 加载 MNIST 数据集...")
    train_images, train_labels = load_mnist(data_root, train=True,
                                            max_samples=args.samples)
    print(f"  训练集: {len(train_images)} 张")

    # 预处理
    print("[KNN Train] 预处理 (OTSU + 形态学 + 居中 padding → 20×20)...")
    processed = np.zeros((len(train_images), 784), dtype=np.float32)
    for i in range(len(train_images)):
        img_20 = preprocess_for_knn(train_images[i])
        processed[i] = img_20.reshape(-1).astype(np.float32)
        if (i + 1) % 10000 == 0:
            print(f"  已处理: {i + 1}/{len(train_images)}")

    train_labels = train_labels.astype(np.int32)

    # 训练 KNN
    print("[KNN Train] 训练 KNN (k=5)...")
    knn = cv2.ml.KNearest_create()
    knn.train(processed, cv2.ml.ROW_SAMPLE, train_labels)

    # 保存
    if args.model_dir is None:
        model_dir = os.path.join(os.path.dirname(__file__), "..", "model")
    else:
        model_dir = args.model_dir
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "knn_mnist.npz")
    np.savez(model_path, train=processed, trainLabel=train_labels)
    print(f"[KNN Train] 模型已保存: {model_path}")
    print(f"  样本数: {len(train_images)}, 特征维度: 784 (28×28)")

    # 快速自测
    print("[KNN Train] 自测 (前 1000 个训练样本)...")
    test_samples = processed[:1000]
    test_labels = train_labels[:1000]
    correct = 0
    for i in range(len(test_samples)):
        sample = test_samples[i].reshape(1, -1).astype(np.float32)
        ret, result, neighbours, dist = knn.findNearest(sample, k=5)
        if int(result[0][0]) == test_labels[i]:
            correct += 1
    acc = correct / len(test_samples) * 100
    print(f"  训练集准确率: {acc:.2f}%")


if __name__ == "__main__":
    main()
