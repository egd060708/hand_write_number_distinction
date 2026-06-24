# 手写数字视频识别 — 实现文档

> 本文档以 **问题 → 方案 → 效果** 的形式，记录整个项目的实现过程与关键技术决策。

---

## 目录

1. [系统概览](#1-系统概览)
2. [问题一：如何构建可交互的识别系统](#2-问题一如何构建可交互的识别系统)
3. [问题二：边缘线条 vs 填充数字](#3-问题二边缘线条-vs-填充数字)
4. [问题三：KNN 性能退化](#4-问题三knn-性能退化)
5. [问题四：预处理中的噪声干扰](#5-问题四预处理中的噪声干扰)
6. [问题五：传统视觉 vs 深度学习](#6-问题五传统视觉-vs-深度学习)
7. [问题六：三种方法如何统一管理](#7-问题六三种方法如何统一管理)
8. [项目结构](#8-项目结构)
9. [经验总结](#9-经验总结)

---

## 1. 系统概览

### 目标

输入一段手写数字视频，实时检测画面中的数字位置，识别数字并标注结果。

### 整体架构

```
┌─────────────────────────────────────────────────┐
│                   tkinter GUI                     │
│  [方法选择] [播放控制] [进度条] [状态栏]            │
├─────────────────────────────────────────────────┤
│               VideoProcessor (线程)               │
│  读取帧 → 调用 Recognizer → 回调 GUI 更新          │
├─────────────────────────────────────────────────┤
│              preprocessing.py (共享)              │
│  边缘检测 → ROI 定位 → 数字标准化 (OTSU+去噪+居中)  │
├─────────────────────────────────────────────────┤
│        Recognizer (三选一，界面内切换)              │
│  ├─ KNN     (OpenCV,  28×28,  20k 样本)           │
│  ├─ Template (OpenCV,  20×20,  10 模板)           │
│  └─ CNN     (PyTorch, 28×28,  60k 训练)           │
└─────────────────────────────────────────────────┘
```

**代码量**: 10 个模块，1565 行 Python

---

## 2. 问题一：如何构建可交互的识别系统

### 问题

需要一个 GUI，能够：
- 浏览本地任意视频
- 边播放边实时识别
- 界面内切换不同识别方法
- 不阻塞、不卡顿

### 方案

**技术选型**: tkinter（Python 标准库，零额外依赖）

**多线程架构**:
```
主线程 (GUI)          后台线程 (VideoProcessor)
    │                      │
    │── 播放 ──────────────→│ 读取帧
    │                      │ 调用 recognizer.process_frame()
    │                      │ 绘制检测框
    │←── after() 回调 ─────│ 返回带标注的帧
    │ 更新 Canvas          │
    │ 更新进度条            │
    │ 更新状态栏            │
```

**懒加载策略**: 启动时只加载默认方法（CNN），其他方法在用户切换时按需加载。后台线程异步预加载全部模型，切换几乎无等待。

**关键代码**: `src/gui.py` (401 行), `src/video_processor.py` (148 行)

---

## 3. 问题二：边缘线条 vs 填充数字

### 问题

参考仓库 (`test1.py`) 使用 OpenCV KNN，但识别准确率低。分析发现其用 **边缘检测图 (edges)** 做识别——边缘是细线条（白色像素 ~100），而 MNIST 训练数据是 **填充的粗体数字**（白色像素 ~150-200）。两者分布严重不匹配。

```
参考代码流程:  edges → 固定阈值(50) → resize 20×20 → KNN
                     ↑ 细线条，信息丢失严重
```

### 方案

**统一预处理流水线** (`src/preprocessing.py`)，对齐 MNIST 数据分布：

```
原始灰度 ROI
  → OTSU 自适应二值化 (自动选阈值，适应不同光照)
  → 连通域去噪 (去除划痕)
  → 形态学闭运算 (填充数字内部缝隙)
  → [CNN] 膨胀加粗笔划 / [KNN] 保持原粗细
  → 裁剪 + 居中 + 保持宽高比 padding (模拟 MNIST 的 20% 外边距)
  → resize 28×28
```

**效果**:

| 指标 | 旧方法 (edges) | 新方法 (OTSU+居中) |
|------|:-----------:|:---------------:|
| 预处理白像素 | ~100 | ~150-200 |
| CNN 置信度 | ~0.17 | **0.85-1.0** |
| KNN 与 CNN 一致性 | 42% | **58%** |

**关键代码**: `src/preprocessing.py` — `prepare_roi()` (183 行)

---

## 4. 问题三：KNN 性能退化

### 问题

共享预处理后，CNN 表现优异（置信度 0.9+），但 KNN 反而不如旧的 edges 方法。

### 根因分析

| 因素 | 影响 |
|------|------|
| **膨胀 (dilation)** | MNIST 训练数据被加粗 → 视频 ROI 相对变细 → 分布不匹配 |
| **低分辨率 (20×20)** | 400 维特征丢失区分性细节 |
| **过多样本 (60k)** | 噪声样本干扰 KNN 的最近邻搜索 |

CNN 不受影响是因为它学习层次化特征，对粗细变化鲁棒。KNN 做像素级 L2 距离匹配，对分布偏移极其敏感。

### 方案

KNN 使用 **不同于 CNN 的预处理参数**：

| 参数 | CNN | KNN |
|------|:---:|:---:|
| `target_size` | 28 | **28** |
| `dilate` | True | **False** |
| 训练样本 | 60k | **20k** |
| 特征维度 | 784 | 784 |

**效果**:

```
与 CNN 一致性:  旧KNN 42% → 改进KNN 58% (+16pp)
模型大小:      92MB → 60MB
```

**关键代码**: `src/train_knn.py`, `src/recognizer.py` 第 42 行 `prepare_roi(..., dilate=False)`

---

## 5. 问题四：预处理中的噪声干扰

### 问题

手写过程中常见的噪声：
- 多余的划痕、试笔痕迹
- 纸张上的斑点
- 书写时未抬笔产生的拖尾

这些噪声和数字主体一样是深色，OTSU 二值化后无法区分。例如 `data/noise.jpg`（数字 5 带划痕）识别置信度仅 0.56。

### 方案

在 `prepare_roi()` 中增加 **连通域面积过滤**：

```
OTSU 二值化
  → connectedComponentsWithStats() 标记各连通域
  → 计算最大连通域面积 A_max
  → 保留 面积 ≥ A_max × 25% 的区域
  → 丢弃小块噪点
```

**效果 (noise.jpg)**:

| 指标 | 去噪前 | 去噪后 |
|------|:-----:|:-----:|
| 置信度 | 0.56 | **0.70** (+25%) |
| 白像素 | 37 | 29 (划痕被清除) |
| 预测 | 5 ✅ | 5 ✅ |

视频回归测试无副作用（平均置信度 0.86-0.91）。

**关键代码**: `src/preprocessing.py` — `_remove_small_blobs()`

---

## 6. 问题五：传统视觉 vs 深度学习

### 问题

项目需要覆盖多种方法进行对比实验。

### 三种方法的设计与权衡

#### 方法一：KNN 机器学习

| 项目 | 说明 |
|------|------|
| 原理 | K-近邻 (k=5)，28×28=784 维特征，L2 距离 |
| 训练 | MNIST 20k 样本 (`src/train_knn.py`) |
| 模型 | `knn_mnist.npz` (~60 MB) |
| 优点 | 实现简单，可解释，无需 GPU |
| 缺点 | 像素级匹配，泛化能力有限，模型大 |

#### 方法二：模板匹配（传统视觉）

| 项目 | 说明 |
|------|------|
| 原理 | 皮尔逊相关系数，10 个平均模板 |
| 训练 | 无需训练，从 `digits.png` 直接计算 |
| 模型 | 10 个 20×20 模板（内存可忽略） |
| 优点 | 零训练成本，完全可解释 |
| 缺点 | 准确率最低，对形变敏感 |

#### 方法三：CNN 深度学习

| 项目 | 说明 |
|------|------|
| 原理 | 2 层卷积网络 (Conv→ReLU→MaxPool)×2 → FC |
| 训练 | MNIST 60k，10 epochs (`src/train_cnn.py`) |
| 模型 | `cnn_mnist.pth` (89 KB) |
| 优点 | 准确率最高 (98.86%)，置信度最可靠，模型极小 |
| 缺点 | 需 PyTorch + GPU 训练 |

#### 效果对比

```
Frame 1200 (19 ROIs):
  KNN:      3,7,4,7,6,4...    (无置信度)
  Template: 3(0.08),2(-0.03)... (低置信)
  CNN:      3(1.00),2(0.99),4(0.89),7(1.00),6(0.98)... ★
```

**CNN 为推荐方法**，KNN 和模板匹配供对比实验使用。

**关键代码**: `src/recognizer.py`, `src/recognizer_template.py`, `src/recognizer_cnn.py`

---

## 7. 问题六：三种方法如何统一管理

### 问题

三种方法各有不同的：
- 模型文件格式 (`.npz` / `.pth` / 无)
- 预处理参数 (`dilate` / `target_size`)
- 输出格式 (有无置信度)

如何在 GUI 中无缝切换？

### 方案

**工厂模式 + 统一接口**：

```python
# RecognizerFactory — 懒加载 + 缓存
factory = RecognizerFactory()
recognizer = factory.get("cnn")  # 首次调用才加载模型

# 所有 Recognizer 实现相同接口:
recognizer.preprocess_frame(frame)   → binary
recognizer.find_digit_rois(binary)   → [(x,y,w,h), ...]
recognizer.predict_digit(roi_gray)   → (digit, conf?, image)
recognizer.process_frame(frame)      → [{x,y,w,h,digit,confidence?}, ...]
recognizer.draw_detections(frame,dets) → annotated_frame
```

**GUI 方法选择器**:

```
┌────────────────────────────────────────────┐
│ [📁 选择视频] │ ●CNN ○KNN ○模板匹配 │ file  │
├────────────────────────────────────────────┤
```

单选按钮绑定 `current_method` 变量，切换时：
1. 暂停播放（如正在播放）
2. 调用 `factory.get(method)` 获取/创建 Recognizer
3. 更新 `VideoProcessor.recognizer` 引用
4. 更新窗口标题和状态栏格式（有无置信度）

**关键代码**: `src/gui.py` — `RecognizerFactory`, `_on_method_changed()`

---

## 8. 项目结构

```
hand_write_number_distinction/
├── docs/
│   └── IMPLEMENTATION.md        ← 本文档
├── src/                          # 源代码 (1565 行)
│   ├── main.py                   # 入口（参数解析 + GUI 启动）
│   ├── gui.py                    # GUI 界面 (401 行)
│   │   ├── RecognizerFactory     #   懒加载 + 缓存
│   │   ├── App._build_ui()       #   UI 构建
│   │   ├── App._on_method_changed() # 方法切换
│   │   └── App._on_frame_ready() #   帧回调
│   ├── preprocessing.py          # 共享预处理 (183 行) ★
│   │   ├── preprocess_frame()    #   边缘检测（ROI 发现）
│   │   ├── find_digit_rois()     #   轮廓检测 + 筛选
│   │   ├── prepare_roi()         #   MNIST 标准化（OTSU+去噪+居中）
│   │   └── _remove_small_blobs() #   连通域去噪
│   ├── recognizer.py             # KNN 识别器 (114 行)
│   ├── recognizer_cnn.py         # CNN 识别器 (142 行)
│   ├── recognizer_template.py    # 模板匹配识别器 (176 行)
│   ├── train_cnn.py              # CNN 训练脚本 (195 行)
│   ├── train_knn.py              # KNN 训练脚本 (115 行)
│   ├── video_processor.py        # 视频处理线程 (148 行)
│   └── utils.py                  # OpenCV ↔ tkinter 转换 (61 行)
├── model/                        # 模型文件
│   ├── cnn_mnist.pth             # CNN (89 KB)
│   ├── knn_mnist.npz             # KNN (~60 MB)
│   ├── data.npz                  # 参考 KNN (备选)
│   └── digits.png                # 模板匹配训练图 (5000 样本)
├── data/                         # 测试数据
│   ├── 手写数字.mp4               # 测试视频
│   └── noise.jpg                 # 噪声测试图
├── run.bat / run.sh              # 一键启动 (Windows / Linux)
├── requirements.txt              # Python 依赖清单
└── README.md                     # 使用说明
```

### 模块职责

| 模块 | 行数 | 职责 | 依赖 |
|------|:----:|------|------|
| `main.py` | 37 | 入口，参数解析 | gui |
| `gui.py` | 401 | tkinter GUI，方法管理 | video_processor, utils |
| `preprocessing.py` | 183 | 边缘检测、ROI定位、MNIST标准化 | cv2, numpy |
| `recognizer.py` | 114 | KNN 识别（k=5, L2距离） | preprocessing, cv2 |
| `recognizer_cnn.py` | 142 | CNN 识别（2层卷积+Softmax） | preprocessing, torch |
| `recognizer_template.py` | 176 | 模板匹配（皮尔逊相关） | cv2, numpy |
| `train_cnn.py` | 195 | CNN 训练（SGD, 10 epoch） | torch, torchvision |
| `train_knn.py` | 115 | KNN 训练（MNIST 20k样本） | torchvision, cv2 |
| `video_processor.py` | 148 | 后台线程视频读取与帧处理 | cv2, threading |
| `utils.py` | 61 | BGR→RGB→PhotoImage 转换 | cv2, PIL |

### Recognizer 统一接口

所有识别器实现相同接口，由 `RecognizerFactory` 统一管理：

```python
class Recognizer:
    def preprocess_frame(frame) -> binary        # 帧→边缘二值图
    def find_digit_rois(binary) -> [(x,y,w,h)]   # 定位候选ROI
    def predict_digit(roi_gray) -> (digit, conf?) # 单ROI识别
    def process_frame(frame) -> [detection]       # 完整帧处理
    def draw_detections(frame, dets) -> annotated # 可视化绘制
```

---

## 9. 经验总结

### 关键教训

1. **预处理比模型更重要**
   CNN 从 ~0.17 提升到 ~0.90 靠的不是换模型，而是把 edges 换成 OTSU + 居中 padding。
   数据分布对齐是识别系统的第一要务。

2. **共享预处理 ≠ 相同参数**
   KNN 和 CNN 虽然共用 `prepare_roi()`，但需要不同的参数（`dilate` / `target_size`）。
   一刀切的预处理会损害某些方法的性能。

3. **简单的去噪策略很有效**
   连通域面积过滤（仅保留 >25% 最大面积的区域）即能有效去除划痕，
   无需复杂的深度学习去噪模型。

4. **模型大小与性能不成正比**
   CNN (89 KB) > KNN (60 MB) > Template (可忽略)。
   深度学习模型虽小但泛化能力最强。

5. **GUI 框架选择**
   tkinter 虽简陋但足够：零依赖、跨平台、与 OpenCV/PyTorch 无冲突。
   复杂的 UI 需求才需要考虑 PyQt。

### 后续改进方向

| 方向 | 说明 |
|------|------|
| **多数字同时识别** | 当前每个 ROI 独立识别，未利用帧间时序信息 |
| **自适应阈值** | OTSU 有时失效（极端光照），可加入自适应阈值回退 |
| **CNN 模型升级** | 可用 ResNet/LeNet-5 替换当前简单 CNN |
| **视频专用训练** | 用视频帧标注数据微调模型，进一步缩小 domain gap |
| **打包发布** | 用 PyInstaller 打包为 exe，免去 conda 环境配置 |
| **摄像头实时识别** | 将 `VideoProcessor` 的视频文件源替换为 `cv2.VideoCapture(0)` |

### 扩展指南

#### 添加新的识别方法

1. 在 `src/` 下新建 `recognizer_xxx.py`
2. 实现统一接口：`preprocess_frame`, `find_digit_rois`, `predict_digit`, `process_frame`, `draw_detections`
3. 在 `gui.py` 的 `METHODS` 字典中注册：`"xxx": {"label": "...", "color": "...", "has_confidence": True/False}`
4. 在 `RecognizerFactory._create()` 中添加分支

#### 使用摄像头实时识别

```python
# 修改 video_processor.py 的 open_video 方法：
def open_camera(self, camera_id=0):
    self.cap = cv2.VideoCapture(camera_id)
    self.total_frames = float('inf')  # 无限流
    self.fps = 30
``` |
