import threading
import time
import cv2
import numpy as np
import mss
import mss.tools


class ScreenRecorder:
    def __init__(self):
        self._recording = False
        self._thread = None
        self._output_path = None
        self._fps = 20
        self._monitor_index = 1  # 1 = primary monitor

    def start(self, output_path: str, fps: int = 20, monitor: int = 1):
        if self._recording:
            return
        self._output_path = output_path
        self._fps = fps
        self._monitor_index = monitor
        self._recording = True
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._recording = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def is_recording(self) -> bool:
        return self._recording

    def _record_loop(self):
        with mss.mss() as sct:
            monitor = sct.monitors[self._monitor_index]
            width = monitor["width"]
            height = monitor["height"]

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(self._output_path, fourcc, self._fps, (width, height))

            frame_duration = 1.0 / self._fps
            try:
                while self._recording:
                    t0 = time.perf_counter()
                    img = sct.grab(monitor)
                    frame = np.array(img)
                    # mss gives BGRA; convert to BGR for OpenCV
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    out.write(frame)
                    elapsed = time.perf_counter() - t0
                    sleep_time = frame_duration - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)
            finally:
                out.release()
