"""
视频处理线程模块
负责读取视频帧、调用识别器、将结果通过队列发送给 GUI
"""

import cv2
import time
import threading
from collections import deque


class VideoProcessor:
    """
    视频处理器：在后台线程中读取视频、执行数字识别

    通过回调函数将处理后的帧和检测结果发送给 GUI 主线程
    """

    def __init__(self, recognizer):
        """
        Args:
            recognizer: DigitRecognizer 实例
        """
        self.recognizer = recognizer
        self.cap = None
        self.total_frames = 0
        self.current_frame_idx = 0
        self.fps = 30

        # 状态控制
        self.playing = False
        self.paused = False
        self.stop_requested = False

        # 速度倍率
        self.speed = 1.0

        # 回调函数: (frame_bgr, detections, frame_idx)
        self.frame_callback = None

        # 处理线程
        self._thread = None

    def open_video(self, video_path: str) -> bool:
        """
        打开视频文件

        Args:
            video_path: 视频文件路径

        Returns:
            是否成功打开
        """
        self.stop()
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            return False

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 30
        self.current_frame_idx = 0
        return True

    def set_frame_callback(self, callback):
        """设置帧更新回调: callback(frame_bgr, detections, frame_idx)"""
        self.frame_callback = callback

    def play(self):
        """开始播放"""
        if self.cap is None:
            return
        self.paused = False
        if not self.playing:
            self.playing = True
            self.stop_requested = False
            self._thread = threading.Thread(target=self._process_loop, daemon=True)
            self._thread.start()

    def pause(self):
        """暂停/恢复"""
        self.paused = not self.paused

    def stop(self):
        """停止播放"""
        self.stop_requested = True
        self.playing = False
        self.paused = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
            self.cap = None
        self.current_frame_idx = 0

    def seek(self, frame_idx: int):
        """跳转到指定帧"""
        if self.cap is None:
            return
        frame_idx = max(0, min(frame_idx, self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        self.current_frame_idx = frame_idx

    def set_speed(self, speed: float):
        """设置播放速度倍率 (0.5, 1.0, 1.5, 2.0)"""
        self.speed = max(0.1, min(speed, 5.0))

    def _process_loop(self):
        """后台处理循环（运行在子线程）"""
        frame_delay = 1.0 / self.fps  # 每帧理论时间间隔

        while self.playing and not self.stop_requested:
            if self.paused:
                time.sleep(0.05)
                continue

            ret, frame = self.cap.read()
            if not ret:
                # 视频播放完毕
                self.playing = False
                if self.frame_callback:
                    self.frame_callback(None, [], self.current_frame_idx)
                break

            self.current_frame_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))

            # 执行数字识别
            detections = self.recognizer.process_frame(frame)

            # 在帧上绘制检测结果
            annotated = self.recognizer.draw_detections(frame, detections)

            # 回调 GUI 更新
            if self.frame_callback:
                self.frame_callback(annotated, detections, self.current_frame_idx)

            # 根据速度倍率控制帧间隔
            actual_delay = frame_delay / self.speed
            time.sleep(actual_delay)

    @property
    def is_playing(self):
        return self.playing and not self.paused

    @property
    def is_stopped(self):
        return not self.playing
