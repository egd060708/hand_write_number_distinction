# 手写数字视频识别 🖊️

基于 OpenCV + PyTorch 的手写数字视频实时识别系统。提供 tkinter 图形界面，支持浏览本地视频文件，边播放边识别，并在画面中框出数字、标注识别结果。

提供 **三种识别方法**：KNN 机器学习、传统模板匹配、CNN 深度学习。

## 效果预览

- 打开视频后，选择识别方法，点击 ▶ 播放即可实时识别
- 检测到的数字以彩色矩形框标出，标注识别结果和置信度
- 支持 0.5x ~ 2.0x 变速播放，拖拽进度条任意跳转
- **在界面中一键切换** KNN / 模板匹配 / CNN 三种方法

## 系统要求

| 项目 | 最低要求 | 推荐配置 |
|------|----------|----------|
| 操作系统 | Windows 10 / Ubuntu 20.04 / macOS 12 | Windows 11 / Ubuntu 22.04 |
| Python | 3.10+ | 3.11 |
| 内存 | 4 GB | 8 GB+ |
| 磁盘空间 | ~200 MB（含 MNIST 数据集） | 500 MB |
| GPU（可选） | — | NVIDIA GPU + CUDA（CNN 推理加速） |

## 环境配置

### 1. 创建 conda 环境

```bash
conda create -n digit_recognition python=3.11 -y
conda activate digit_recognition
```

### 2. 安装依赖

**方式一：一键安装（推荐）**

```bash
pip install -r requirements.txt
```

**方式二：手动安装**

```bash
pip install numpy==1.26.4
pip install opencv-python==4.9 opencv-contrib-python==4.9
pip install pillow pymupdf matplotlib
pip install torch torchvision
```

> **注意**：PyTorch 2.x 需要 numpy<2，OpenCV 4.9 兼容 numpy 1.x。请严格按以上顺序安装。
>
> **Ubuntu 用户注意**：
> 1. 如果 tkinter 未安装（`ModuleNotFoundError: No module named 'tkinter'`），请执行：
>    ```bash
>    sudo apt install python3-tk
>    ```
> 2. 如果 OpenCV 提示缺少库（`ImportError: libGL.so.1` 等），请安装系统依赖：
>    ```bash
>    sudo apt install libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1
>    ```

### 3. 检查安装

```bash
python -c "import torch; print('PyTorch', torch.__version__, 'CUDA:', torch.cuda.is_available())"
python -c "import cv2; print('OpenCV', cv2.__version__); import tkinter; print('tkinter OK')"
```

## 快速开始

### Windows — 双击运行

双击仓库根目录下的 **`run.bat`**。

### Linux / macOS — 命令行运行

```bash
chmod +x run.sh
./run.sh
```

### 命令行

```bash
conda activate digit_recognition
python src/main.py
```

> 启动后默认使用 **CNN**，可在界面顶部直接切换 KNN / 模板匹配 / CNN。

### 训练模型（首次使用前各执行一次）

```bash
python src/train_cnn.py    # CNN: 2-3 分钟
python src/train_knn.py    # KNN: 2-3 分钟
```

> 模板匹配无需训练，开箱即用。

### 命令行参数

```
python src/main.py [--model PATH]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--model PATH` | 覆盖模型文件路径（高级用法） | 自动选择 `model/` 下的文件 |

### 训练脚本参数

```bash
# CNN 训练
python src/train_cnn.py --epochs 10 --lr 0.01 --batch-size 64

# KNN 训练
python src/train_knn.py --samples 20000
```

| 脚本 | 参数 | 说明 | 默认值 |
|------|------|------|--------|
| `train_cnn.py` | `--epochs` | 训练轮数 | 10 |
| | `--lr` | 学习率 | 0.01 |
| | `--batch-size` | 批次大小 | 64 |
| | `--model-dir` | 模型保存目录 | `model/` |
| `train_knn.py` | `--samples` | 训练样本数 | 20000 |
| | `--model-dir` | 模型保存目录 | `model/` |

### 操作流程

1. 点击 **📁 选择视频**，浏览并选择本地视频文件
2. 在顶部选择识别方法：🟢 CNN 深度学习 / 🔵 KNN 机器学习 / 🟡 模板匹配
3. 点击 **▶ 播放** 开始实时识别
4. 可随时 **⏸ 暂停** 查看某一帧，或切换方法对比效果
5. 状态栏实时显示检测到的数字及置信度（KNN 除外）

## 三种识别方法对比

| 特性 | KNN 机器学习 | 模板匹配 | CNN 深度学习 |
|------|:-----------:|:-------:|:----------:|
| 训练数据 | data.npz (6157 样本) | digits.png (5000 样本) | MNIST (60000 样本) |
| 模型大小 | ~9.8 MB | ~10 个模板 | ~80 KB (.pth) |
| 识别原理 | K-近邻 (k=5) | 皮尔逊相关系数 | 2层卷积神经网络 |
| 预训练 | 需要 | **不需要** | 需训练 (2-3 min) |
| 置信度 | 无 | ✅ 有 | ✅ 有 |
| 准确率 (MNIST) | — | — | **98.86%** |
| 启动命令 | `python src/main.py` | `--method template` | `--method cnn` |
| 本质 | 机器学习 | 传统视觉 | **深度学习** |

## 项目结构

```
hand_write_number_distinction/
├── src/                        # 源代码
│   ├── main.py                 # 入口脚本
│   ├── gui.py                  # tkinter 图形界面（内置方法选择）
│   ├── preprocessing.py        # 共享预处理（KNN/CNN 共用）
│   ├── recognizer.py           # KNN 识别器
│   ├── recognizer_template.py  # 模板匹配识别器
│   ├── recognizer_cnn.py       # CNN 识别器
│   ├── train_cnn.py            # CNN 训练脚本
│   ├── train_knn.py            # KNN 训练脚本
│   ├── video_processor.py      # 视频读取与后台处理线程
│   └── utils.py                # 图像格式转换工具
├── model/                      # 模型
│   ├── knn_mnist.npz           # KNN 模型 (MNIST 60k)
│   ├── cnn_mnist.pth           # CNN 模型 (89 KB)
│   ├── data.npz                # 参考 KNN 模型 (备选)
│   └── digits.png              # 模板匹配训练图
├── data/
│   └── 手写数字.mp4             # 测试视频
├── run.bat                     # 一键启动 (Windows)
├── run.sh                      # 一键启动 (Linux/macOS)
├── requirements.txt            # Python 依赖清单
└── README.md
```

## 识别算法流程

三种方法共用相同的图像预处理流水线，仅在最终分类阶段不同：

```
视频帧 (BGR)
  │
  ├─→ 灰度化
  ├─→ 形态学膨胀 (iterations=2)
  ├─→ 形态学腐蚀 (iterations=2)
  ├─→ absdiff 作差提取边缘
  ├─→ Sobel X + Sobel Y 边缘检测
  ├─→ 加权融合 → 阈值二值化 (thresh=50)
  ├─→ 轮廓检测 → 筛选 ROI (w>10, h>20)
  │
  └─→ 对每个 ROI:
        ├─→ 二值化 (thresh=50)
        ├─→ resize
        │     ├─ KNN/Template: 20×20 → 400 维向量
        │     └─ CNN: 28×28 → PIL → ToTensor → Normalize
        │
        └─→ 分类 ──┬── KNN (k=5)              → 数字
                   ├── 皮尔逊相关系数 × 10 模板  → 数字 + 置信度
                   └── CNN 前向推理 + Softmax   → 数字 + 置信度
```

### CNN 网络结构

```
输入: 1×28×28 (灰度图)
  ↓
Conv1: 1→10 channels, kernel=5, ReLU, MaxPool2 → 10×12×12
  ↓
Conv2: 10→20 channels, kernel=5, ReLU, MaxPool2 → 20×4×4
  ↓
Flatten → 320
  ↓
FC1: 320→50 → ReLU
  ↓
FC2: 50→10 → 输出 (0-9)
```

> 参考博客: https://blog.csdn.net/qq_45588019/article/details/120935828

## 技术要点

| 模块 | 说明 |
|------|------|
| **GUI 框架** | Python 标准库 tkinter，界面内一键切换三种方法 |
| **共享预处理** | `preprocessing.py` 统一 KNN/CNN 预处理（OTSU+形态学+居中） |
| **多线程** | 视频读取与识别在后台线程执行，`after()` 回调更新界面 |
| **懒加载** | 启动时只加载默认方法，其他方法按需加载，后台预初始化 |
| **GPU 加速** | CNN 推理自动使用 CUDA（若可用） |
| **中文路径** | 使用 `imdecode` 替代 `imread`，支持含中文的路径 |

## 实测对比（Frame 800）

| 方法 | 结果 | 置信度 |
|------|:---:|:------:|
| KNN | 1 | — |
| Template | 4 | 0.08 |
| **CNN** | **7** | **0.89** |

> CNN 以高置信度 (0.89) 输出结果，明显优于模板匹配 (0.08)。实际应用中 CNN 表现最为可靠。

## 参考

- 参考仓库 `number_classification-master` — 基于 OpenCV KNN
- 参考仓库 `DL` — CNN 训练框架
- CSDN 博客: [手写数字识别](https://blog.csdn.net/reason125132/article/details/124741701)
- CSDN 博客: [PyTorch MNIST CNN](https://blog.csdn.net/qq_45588019/article/details/120935828)
- PDF 实验指导: `实验三.pdf`

## 常见问题

### Q1: 启动报错 `ModuleNotFoundError: No module named 'tkinter'`

**Ubuntu/Debian**:
```bash
sudo apt install python3-tk
```

**Windows/macOS**: tkinter 随 Python 一起安装，如缺失请重装 Python 并勾选 tcl/tk 组件。

### Q2: 启动报错 `ImportError: libGL.so.1`

此为 OpenCV 依赖的系统库缺失（常见于无 GUI 的 Linux 服务器）：
```bash
sudo apt install libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1
```

### Q3: CNN 模型加载失败

请先运行训练脚本生成模型文件：
```bash
python src/train_cnn.py
```
训练约 2-3 分钟，模型将保存至 `model/cnn_mnist.pth`。

### Q4: KNN 模型加载失败

```bash
python src/train_knn.py
```
训练约 2-3 分钟，模型将保存至 `model/knn_mnist.npz`（~60 MB）。

### Q5: 视频无法打开/识别效果差

- 确保视频编码格式为 H.264（MP4/AVI），OpenCV 默认不支持部分编码
- 建议使用 `data/` 目录下的测试视频
- 识别时保持数字书写清晰，避免大面积遮挡

### Q6: 切换方法后界面卡住

首次切换方法时会加载模型（懒加载），CNN 模型加载约 1-2 秒。程序启动时会在后台预加载所有模型，通常切换是即时的。

### Q7: 如何用自己的摄像头实时识别？

当前版本使用视频文件输入。如需摄像头实时识别，可将 `gui.py` 中的 `VideoProcessor` 替换为 `cv2.VideoCapture(0)` 读取摄像头流。详见 `docs/IMPLEMENTATION.md`。
