import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import os
import mss

from recorder import ScreenRecorder


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Screen Recorder")
        self.resizable(False, False)

        self._recorder = ScreenRecorder()
        self._monitors = self._get_monitor_list()
        self._elapsed = 0
        self._timer_job = None

        self._build_ui()

    def _get_monitor_list(self):
        with mss.mss() as sct:
            # index 0 is the virtual "all monitors" combined screen
            return [
                f"Monitor {i}: {m['width']}x{m['height']}"
                for i, m in enumerate(sct.monitors)
                if i > 0
            ]

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # Output path row
        path_frame = ttk.Frame(self)
        path_frame.grid(row=0, column=0, columnspan=2, sticky="ew", **pad)

        self._path_var = tk.StringVar(value=self._default_path())
        ttk.Label(path_frame, text="Save to:").pack(side="left")
        ttk.Entry(path_frame, textvariable=self._path_var, width=42).pack(side="left", padx=(6, 4))
        ttk.Button(path_frame, text="Browse", command=self._browse).pack(side="left")

        # Monitor selection
        monitor_frame = ttk.Frame(self)
        monitor_frame.grid(row=1, column=0, columnspan=2, sticky="ew", **pad)
        ttk.Label(monitor_frame, text="Monitor:").pack(side="left")
        self._monitor_var = tk.StringVar()
        monitor_cb = ttk.Combobox(
            monitor_frame,
            textvariable=self._monitor_var,
            values=self._monitors,
            state="readonly",
            width=32,
        )
        monitor_cb.pack(side="left", padx=(6, 0))
        if self._monitors:
            monitor_cb.current(0)

        # FPS selection
        fps_frame = ttk.Frame(self)
        fps_frame.grid(row=2, column=0, columnspan=2, sticky="ew", **pad)
        ttk.Label(fps_frame, text="FPS:").pack(side="left")
        self._fps_var = tk.IntVar(value=20)
        for fps in (10, 15, 20, 30):
            ttk.Radiobutton(fps_frame, text=str(fps), variable=self._fps_var, value=fps).pack(
                side="left", padx=4
            )

        # Timer display
        self._timer_var = tk.StringVar(value="00:00")
        ttk.Label(self, textvariable=self._timer_var, font=("Courier", 22)).grid(
            row=3, column=0, columnspan=2, pady=(4, 2)
        )

        # Control buttons
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(2, 10))

        self._start_btn = ttk.Button(btn_frame, text="Start", command=self._start, width=12)
        self._start_btn.pack(side="left", padx=6)

        self._stop_btn = ttk.Button(
            btn_frame, text="Stop", command=self._stop, width=12, state="disabled"
        )
        self._stop_btn.pack(side="left", padx=6)

        # Status bar
        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self._status_var, foreground="gray").grid(
            row=5, column=0, columnspan=2, pady=(0, 6)
        )

    def _default_path(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(os.path.expanduser("~"), "Videos", f"recording_{ts}.mp4")

    def _browse(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 video", "*.mp4")],
            initialfile=os.path.basename(self._path_var.get()),
            initialdir=os.path.dirname(self._path_var.get()),
        )
        if path:
            self._path_var.set(path)

    def _selected_monitor_index(self):
        # Combobox shows "Monitor 1: ...", "Monitor 2: ..." etc.
        selected = self._monitor_var.get()
        if not selected:
            return 1
        return int(selected.split(":")[0].split()[1])

    def _start(self):
        out_path = self._path_var.get().strip()
        if not out_path:
            messagebox.showerror("Error", "Please specify an output file path.")
            return

        out_dir = os.path.dirname(out_path)
        if out_dir and not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except OSError as e:
                messagebox.showerror("Error", f"Cannot create directory:\n{e}")
                return

        monitor_idx = self._selected_monitor_index()
        fps = self._fps_var.get()

        self._recorder.start(out_path, fps=fps, monitor=monitor_idx)

        self._start_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._status_var.set(f"Recording → {os.path.basename(out_path)}")
        self._elapsed = 0
        self._tick()

    def _stop(self):
        self._recorder.stop()
        if self._timer_job:
            self.after_cancel(self._timer_job)
            self._timer_job = None

        out_path = self._path_var.get()
        self._start_btn.config(state="normal")
        self._stop_btn.config(state="disabled")
        self._status_var.set(f"Saved: {out_path}")
        # Reset path for next recording
        self._path_var.set(self._default_path())

    def _tick(self):
        mins, secs = divmod(self._elapsed, 60)
        self._timer_var.set(f"{mins:02d}:{secs:02d}")
        self._elapsed += 1
        self._timer_job = self.after(1000, self._tick)

    def on_close(self):
        if self._recorder.is_recording():
            self._stop()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
