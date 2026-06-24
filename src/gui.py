"""
手写数字视频识别 GUI 界面
基于 tkinter，集成视频播放、数字识别与结果可视化

支持在界面中切换三种识别方法: KNN / 模板匹配 / CNN
"""

import os
import tkinter as tk
from tkinter import filedialog, ttk
import threading

from video_processor import VideoProcessor
from utils import cv2_to_image_tk, resize_frame_to_display


# ---------------------------------------------------------------------------
# 方法元数据
# ---------------------------------------------------------------------------
METHODS = {
    "knn":      {"label": "KNN 机器学习",   "color": "#4a90d9", "has_confidence": False},
    "template": {"label": "模板匹配",       "color": "#e6a817", "has_confidence": True},
    "cnn":      {"label": "CNN 深度学习",   "color": "#34a853", "has_confidence": True},
}
DEFAULT_METHOD = "cnn"


# ---------------------------------------------------------------------------
# 懒加载识别器工厂
# ---------------------------------------------------------------------------
class RecognizerFactory:
    """按需加载识别器，避免启动时加载全部模型"""

    def __init__(self, model_override: str = None):
        self._cache = {}
        self._model_override = model_override

    def get(self, method: str):
        if method not in self._cache:
            self._cache[method] = self._create(method)
        return self._cache[method]

    def _create(self, method: str):
        print(f"[GUI] 加载识别器: {method} ...")
        if method == "knn":
            from recognizer import DigitRecognizer
            return DigitRecognizer(model_path=self._model_override)
        elif method == "template":
            from recognizer_template import TemplateRecognizer
            return TemplateRecognizer()
        elif method == "cnn":
            from recognizer_cnn import CNNRecognizer
            return CNNRecognizer(model_path=self._model_override)
        else:
            raise ValueError(f"未知方法: {method}")

    def preload_all(self):
        """后台预加载所有模型"""
        for m in METHODS:
            try:
                self.get(m)
            except Exception as e:
                print(f"[GUI] 预加载 {m} 失败: {e}")


# ---------------------------------------------------------------------------
# 主界面
# ---------------------------------------------------------------------------
class App:
    DISPLAY_WIDTH = 480
    DISPLAY_HEIGHT = 680

    def __init__(self, root: tk.Tk, model_override: str = None):
        self.root = root
        self.root.title("手写数字视频识别")
        self.root.geometry("660x840")
        self.root.minsize(550, 650)
        self.root.configure(bg="#2b2b2b")

        # 识别器工厂（懒加载）
        self.factory = RecognizerFactory(model_override)

        # 当前状态
        self.current_method = tk.StringVar(value=DEFAULT_METHOD)
        self._recognizer = None
        self._current_photo = None
        self._video_path = tk.StringVar()
        self._status_text = tk.StringVar(value="就绪 — 请选择视频文件")
        self._frame_info = tk.StringVar(value="Frame: --/--")
        self._seeking = False
        self._seek_debounce_id = None

        # 视频处理器（稍后用选中的 recognizer 初始化）
        self.processor = VideoProcessor(None)
        self.processor.set_frame_callback(self._on_frame_ready)

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 启动时加载默认方法
        self._switch_method(DEFAULT_METHOD)
        # 后台预加载其他模型
        threading.Thread(target=self.factory.preload_all, daemon=True).start()

    # ==================================================================
    # 界面构建
    # ==================================================================
    def _build_ui(self):
        self._build_toolbar()
        self._build_video_display()
        self._build_controls()
        self._build_statusbar()

    def _build_toolbar(self):
        """顶部工具栏：浏览按钮 + 方法选择 + 文件路径"""
        toolbar = tk.Frame(self.root, bg="#333333", padx=8, pady=6)
        toolbar.pack(fill=tk.X)

        # 浏览按钮
        btn_browse = tk.Button(
            toolbar, text="📁 选择视频", command=self._browse_video,
            bg="#4a90d9", fg="white", activebackground="#357abd",
            font=("Microsoft YaHei", 10), padx=12, pady=2, bd=0, cursor="hand2"
        )
        btn_browse.pack(side=tk.LEFT)

        # 分隔线
        tk.Frame(toolbar, bg="#555555", width=1, height=24).pack(side=tk.LEFT, padx=10)

        # 方法选择器
        method_frame = tk.Frame(toolbar, bg="#333333")
        method_frame.pack(side=tk.LEFT)

        tk.Label(method_frame, text="方法:", bg="#333333", fg="#cccccc",
                 font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(0, 6))

        for key, meta in METHODS.items():
            rb = tk.Radiobutton(
                method_frame, text=meta["label"], variable=self.current_method,
                value=key, command=self._on_method_changed,
                bg="#333333", fg="#aaaaaa", selectcolor="#444444",
                activebackground="#3a3a3a", activeforeground="white",
                font=("Microsoft YaHei", 9),
                cursor="hand2"
            )
            rb.pack(side=tk.LEFT, padx=(0, 4))

        # 文件路径（右侧）
        lbl_path = tk.Label(
            toolbar, textvariable=self._video_path,
            bg="#333333", fg="#888888", anchor=tk.E,
            font=("Microsoft YaHei", 8)
        )
        lbl_path.pack(side=tk.RIGHT, padx=(10, 0))

    def _build_video_display(self):
        """视频显示画布"""
        display_frame = tk.Frame(self.root, bg="#1e1e1e", padx=5, pady=5)
        display_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 0))

        self.canvas = tk.Canvas(
            display_frame,
            width=self.DISPLAY_WIDTH, height=self.DISPLAY_HEIGHT,
            bg="#1e1e1e", highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._placeholder_text = self.canvas.create_text(
            self.DISPLAY_WIDTH // 2, self.DISPLAY_HEIGHT // 2,
            text="📁 选择视频 → 选择方法 → ▶ 播放",
            fill="#555555", font=("Microsoft YaHei", 13),
            anchor=tk.CENTER
        )

    def _build_controls(self):
        """底部控制栏"""
        ctrl_frame = tk.Frame(self.root, bg="#333333", padx=8, pady=6)
        ctrl_frame.pack(fill=tk.X, padx=8, pady=(4, 0))

        btn_frame = tk.Frame(ctrl_frame, bg="#333333")
        btn_frame.pack(side=tk.LEFT)

        btn_style = {
            "bg": "#555555", "fg": "white", "activebackground": "#666666",
            "font": ("Microsoft YaHei", 10), "padx": 12, "pady": 2,
            "bd": 0, "cursor": "hand2"
        }

        self.btn_play = tk.Button(btn_frame, text="▶ 播放", command=self._play, **btn_style)
        self.btn_play.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_pause = tk.Button(btn_frame, text="⏸ 暂停", command=self._pause, **btn_style)
        self.btn_pause.pack(side=tk.LEFT)

        # 速度选择
        tk.Label(ctrl_frame, text="速度:", bg="#333333", fg="#cccccc",
                 font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(15, 4))
        self.speed_var = tk.StringVar(value="1.0x")
        speed_menu = ttk.Combobox(
            ctrl_frame, textvariable=self.speed_var, width=6,
            values=["0.5x", "0.75x", "1.0x", "1.5x", "2.0x"],
            state="readonly"
        )
        speed_menu.pack(side=tk.LEFT)
        speed_menu.bind("<<ComboboxSelected>>", self._on_speed_change)

        # 帧信息
        lbl_frame = tk.Label(
            ctrl_frame, textvariable=self._frame_info,
            bg="#333333", fg="#aaaaaa", font=("Consolas", 9)
        )
        lbl_frame.pack(side=tk.RIGHT)

        # 进度条
        progress_frame = tk.Frame(self.root, bg="#333333", padx=8)
        progress_frame.pack(fill=tk.X, padx=8, pady=(2, 4))

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_scale = tk.Scale(
            progress_frame, variable=self.progress_var,
            from_=0, to=100, orient=tk.HORIZONTAL,
            bg="#333333", fg="white", troughcolor="#555555",
            highlightthickness=0, bd=0, sliderlength=15,
            command=self._on_progress_drag
        )
        self.progress_scale.pack(fill=tk.X)

    def _build_statusbar(self):
        """底部状态栏"""
        status = tk.Frame(self.root, bg="#2b2b2b", padx=10, pady=4)
        status.pack(fill=tk.X)

        self.lbl_status = tk.Label(
            status, textvariable=self._status_text,
            bg="#2b2b2b", fg="#888888", anchor=tk.W,
            font=("Microsoft YaHei", 9)
        )
        self.lbl_status.pack(fill=tk.X)

    # ==================================================================
    # 方法切换
    # ==================================================================
    def _on_method_changed(self):
        """用户点击方法单选按钮"""
        method = self.current_method.get()
        # 如果正在播放，先暂停
        was_playing = self.processor.is_playing
        if was_playing:
            self.processor.pause()

        self._switch_method(method)

        if was_playing:
            self.processor.pause()  # 恢复播放

    def _switch_method(self, method: str):
        """切换到指定方法，更新标题栏和处理器"""
        self._recognizer = self.factory.get(method)
        self.processor.recognizer = self._recognizer

        meta = METHODS[method]
        self.root.title(f"手写数字视频识别 — {meta['label']}")
        self._status_text.set(f"方法已切换: {meta['label']} — 就绪")
        print(f"[GUI] 当前方法: {meta['label']}")

    # ==================================================================
    # 事件处理
    # ==================================================================
    def _browse_video(self):
        path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv"),
                ("所有文件", "*.*"),
            ]
        )
        if path:
            self._video_path.set(os.path.basename(path))
            self._status_text.set("正在加载视频...")
            self.root.update_idletasks()

            if self.processor.open_video(path):
                total = self.processor.total_frames
                fps = self.processor.fps
                self._status_text.set(f"已加载 — {total} 帧, {fps:.0f} fps")
                self.progress_var.set(0)
                self._update_frame_info(0)
                self._seek_and_show(0)
            else:
                self._status_text.set("❌ 无法打开视频文件")

    def _play(self):
        if self.processor.cap is None:
            self._status_text.set("⚠ 请先选择视频文件")
            return
        if self.processor.paused:
            self.processor.pause()
            self._status_text.set("▶ 播放中...")
            return
        self.processor.play()
        self._status_text.set("▶ 播放中...")
        self.canvas.delete(self._placeholder_text)

    def _pause(self):
        self.processor.pause()
        if self.processor.paused:
            self._status_text.set("⏸ 已暂停")
        else:
            self._status_text.set("▶ 播放中...")

    def _on_speed_change(self, event=None):
        val = self.speed_var.get().replace("x", "")
        try:
            self.processor.set_speed(float(val))
        except ValueError:
            pass

    def _on_progress_drag(self, value):
        if self.processor.total_frames <= 0:
            return
        self._seeking = True
        if self._seek_debounce_id is not None:
            self.root.after_cancel(self._seek_debounce_id)
        self._seek_debounce_id = self.root.after(500, self._reset_seeking)
        pct = float(value) / 100.0
        frame_idx = int(pct * (self.processor.total_frames - 1))
        self._seek_and_show(frame_idx)

    def _reset_seeking(self):
        self._seeking = False
        self._seek_debounce_id = None

    def _seek_and_show(self, frame_idx: int):
        """跳转并显示预览帧"""
        if self.processor.cap is None:
            return
        was_paused = self.processor.paused
        self.processor.pause()
        self.processor.seek(frame_idx)
        ret, frame = self.processor.cap.read()
        if ret:
            self.processor.current_frame_idx = frame_idx
            self._display_frame(frame, frame_idx)
            self._update_frame_info(frame_idx)
        if not was_paused:
            self.processor.pause()

    # ==================================================================
    # 帧回调（后台线程 → 主线程）
    # ==================================================================
    def _on_frame_ready(self, frame, detections, frame_idx):
        if frame is None:
            self.root.after(0, self._on_video_end)
            return
        self.root.after(0, self._display_frame, frame, frame_idx)
        self.root.after(0, self._update_frame_info, frame_idx)
        self.root.after(0, self._update_status_from_detections, detections)

    def _display_frame(self, frame, frame_idx):
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w < 50:
            canvas_w = self.DISPLAY_WIDTH
        if canvas_h < 50:
            canvas_h = self.DISPLAY_HEIGHT

        display = resize_frame_to_display(frame, canvas_w, canvas_h)
        self._current_photo = cv2_to_image_tk(display)

        self.canvas.delete("all")
        self.canvas.create_image(canvas_w // 2, canvas_h // 2,
                                 image=self._current_photo, anchor=tk.CENTER)

        if not self._seeking and self.processor.total_frames > 0:
            pct = frame_idx / (self.processor.total_frames - 1) * 100
            self.progress_var.set(pct)

    def _update_frame_info(self, frame_idx):
        total = self.processor.total_frames
        self._frame_info.set(f"Frame: {frame_idx} / {total}")

    def _update_status_from_detections(self, detections):
        if detections:
            method = self.current_method.get()
            if METHODS[method]["has_confidence"]:
                items = [f"{d['digit']}({d.get('confidence', 0):.2f})" for d in detections]
            else:
                items = [str(d["digit"]) for d in detections]
            self._status_text.set(f"检测到 {len(detections)} 个: [{', '.join(items)}]")
        elif self.processor.is_playing:
            self._status_text.set("▶ 播放中... (未检测到数字)")

    def _on_video_end(self):
        self.processor.playing = False
        self._status_text.set("✅ 播放完毕")
        self.progress_var.set(100)
        self._update_frame_info(self.processor.total_frames)

    def _on_close(self):
        self.processor.stop()
        self.root.destroy()
