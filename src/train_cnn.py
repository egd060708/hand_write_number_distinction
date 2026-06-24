"""
CNN 手写数字识别 — 训练脚本
基于 PyTorch，使用 MNIST 数据集训练一个 2 层卷积神经网络

参考: https://blog.csdn.net/qq_45588019/article/details/120935828

用法:
    python train_cnn.py                    # 默认参数训练
    python train_cnn.py --epochs 20        # 指定训练轮数
    python train_cnn.py --lr 0.005         # 指定学习率
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import transforms, datasets
import os
import argparse
from matplotlib import pyplot as plt


# ---------------------------------------------------------------------------
# 超参数
# ---------------------------------------------------------------------------
BATCH_SIZE = 64
LEARNING_RATE = 0.01
MOMENTUM = 0.5
EPOCH = 10


# ---------------------------------------------------------------------------
# CNN 网络定义（来自博客）
#   输入: 1×28×28 灰度图
#   输出: 10 类 (0-9)
# ---------------------------------------------------------------------------
class CNN(nn.Module):
    def __init__(self):
        super(CNN, self).__init__()
        self.conv1 = nn.Sequential(
            nn.Conv2d(1, 10, kernel_size=5),   # 1→10 通道, 24×24
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2),        # 12×12
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(10, 20, kernel_size=5),  # 10→20 通道, 8×8
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2),        # 4×4
        )
        self.fc = nn.Sequential(
            nn.Linear(320, 50),                 # 20×4×4=320
            nn.Linear(50, 10),
        )

    def forward(self, x):
        batch_size = x.size(0)
        x = self.conv1(x)
        x = self.conv2(x)
        x = x.view(batch_size, -1)             # flatten → (batch, 320)
        x = self.fc(x)
        return x


# ---------------------------------------------------------------------------
# 训练与测试
# ---------------------------------------------------------------------------
def train(model, device, train_loader, optimizer, criterion, epoch):
    """单轮训练，每 300 batch 输出一次 loss 和 acc"""
    model.train()
    running_loss = 0.0
    running_total = 0
    running_correct = 0

    for batch_idx, (inputs, target) in enumerate(train_loader, 1):
        inputs, target = inputs.to(device), target.to(device)
        optimizer.zero_grad()

        outputs = model(inputs)
        loss = criterion(outputs, target)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        _, predicted = torch.max(outputs.data, dim=1)
        running_total += inputs.shape[0]
        running_correct += (predicted == target).sum().item()

        if batch_idx % 300 == 0:
            avg_loss = running_loss / 300
            avg_acc = 100 * running_correct / running_total
            print(f'  Epoch {epoch:2d} [{batch_idx:4d}]: '
                  f'loss={avg_loss:.3f}, acc={avg_acc:.2f}%')
            running_loss = 0.0
            running_total = 0
            running_correct = 0


def test(model, device, test_loader):
    """测试集评估"""
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            _, predicted = torch.max(outputs.data, dim=1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    acc = correct / total
    return acc


# ---------------------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="CNN MNIST 训练")
    parser.add_argument("--epochs", type=int, default=EPOCH, help="训练轮数")
    parser.add_argument("--lr", type=float, default=LEARNING_RATE, help="学习率")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="批次大小")
    parser.add_argument("--model-dir", type=str, default=None, help="模型保存目录")
    args = parser.parse_args()

    # 设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"使用设备: {device}")

    # 数据准备 — MNIST 归一化 (mean=0.1307, std=0.3081)
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])

    data_root = os.path.join(os.path.dirname(__file__), "..", "data", "mnist")
    train_dataset = datasets.MNIST(root=data_root, train=True,
                                   transform=transform, download=True)
    test_dataset = datasets.MNIST(root=data_root, train=False,
                                  transform=transform, download=True)

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size, shuffle=False)

    print(f"训练集: {len(train_dataset)} 张, 测试集: {len(test_dataset)} 张")

    # 模型、损失函数、优化器
    model = CNN().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=args.lr, momentum=MOMENTUM)

    # 模型保存路径
    if args.model_dir is None:
        model_dir = os.path.join(os.path.dirname(__file__), "..", "model")
    else:
        model_dir = args.model_dir
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "cnn_mnist.pth")

    # 训练循环
    print(f"\n开始训练: {args.epochs} epochs, lr={args.lr}, batch={args.batch_size}")
    print("-" * 50)

    acc_list = []
    best_acc = 0.0

    for epoch in range(1, args.epochs + 1):
        train(model, device, train_loader, optimizer, criterion, epoch)
        acc = test(model, device, test_loader)
        acc_list.append(acc)
        print(f'  >>> Epoch {epoch:2d}  Test Accuracy: {acc:.4f} ({acc*100:.2f}%)')

        # 保存最佳模型
        if acc > best_acc:
            best_acc = acc
            torch.save(model.state_dict(), model_path)
            print(f'  >>> 已保存最佳模型: {model_path} (acc={best_acc:.4f})')

    print("-" * 50)
    print(f"训练完成! 最佳准确率: {best_acc*100:.2f}%")
    print(f"模型已保存至: {model_path}")

    # 绘制准确率曲线
    plt.figure()
    plt.plot(range(1, args.epochs + 1), [a * 100 for a in acc_list], 'b-o')
    plt.xlabel("Epoch")
    plt.ylabel("Test Accuracy (%)")
    plt.title("CNN MNIST Training Curve")
    acc_plot_path = os.path.join(model_dir, "cnn_training_curve.png")
    plt.savefig(acc_plot_path, dpi=150)
    print(f"训练曲线已保存至: {acc_plot_path}")


if __name__ == "__main__":
    main()
