import tkinter as tk
from tkinter import filedialog
from datetime import datetime
import os
import mss
import customtkinter as ctk

from recorder import ScreenRecorder

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── colour palette ────────────────────────────────────────────────────────────
BG        = "#0f1117"
CARD      = "#1a1d27"
BORDER    = "#2a2d3a"
ACCENT    = "#4f8ef7"
ACCENT_H  = "#6ba3ff"
RED       = "#e05c5c"
RED_H     = "#f07070"
GREEN     = "#4caf82"
TEXT      = "#e8eaf0"
TEXT_DIM  = "#7a7f96"
FONT_BODY = ("Inter", 13)
FONT_SM   = ("Inter", 11)
FONT_LG   = ("Inter", 15, "bold")
FONT_MONO = ("Consolas", 26, "bold")


class FloatingBar(ctk.CTkToplevel):
    """Small always-on-top toolbar shown while recording."""

    def __init__(self, on_stop):
        super().__init__()
        self.overrideredirect(True)           # borderless
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.93)
        self.configure(fg_color="#1a1d27")

        self._on_stop = on_stop
        self._elapsed = 0
        self._tick_job = None
        self._dot_visible = True

        # position: bottom-right corner
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 260, 56
        self.geometry(f"{w}x{h}+{sw - w - 24}+{sh - h - 60}")

        self._build()

    def _build(self):
        outer = ctk.CTkFrame(self, fg_color="#1a1d27", corner_radius=14,
                             border_width=1, border_color="#2a2d3a")
        outer.pack(fill="both", expand=True, padx=2, pady=2)

        # drag support
        outer.bind("<ButtonPress-1>", self._drag_start)
        outer.bind("<B1-Motion>", self._drag_motion)

        # red dot
        self._dot = tk.Label(outer, text="●", fg=RED, bg="#1a1d27",
                             font=("Arial", 13))
        self._dot.pack(side="left", padx=(12, 4))

        # timer
        self._timer_var = tk.StringVar(value="00:00")
        tk.Label(outer, textvariable=self._timer_var, fg=TEXT, bg="#1a1d27",
                 font=("Consolas", 16, "bold")).pack(side="left", padx=(0, 10))

        # stop button
        ctk.CTkButton(outer, text="■  Stop", width=82, height=32,
                      fg_color=RED, hover_color=RED_H, text_color="white",
                      font=("Inter", 12, "bold"), corner_radius=8,
                      command=self._stop).pack(side="right", padx=10)

    def _drag_start(self, e):
        self._dx = e.x_root - self.winfo_x()
        self._dy = e.y_root - self.winfo_y()

    def _drag_motion(self, e):
        self.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def start_timer(self):
        self._elapsed = 0
        self._tick()

    def _tick(self):
        mins, secs = divmod(self._elapsed, 60)
        self._timer_var.set(f"{mins:02d}:{secs:02d}")
        self._elapsed += 1
        # blink dot
        self._dot_visible = not self._dot_visible
        self._dot.config(fg=RED if self._dot_visible else "#1a1d27")
        self._tick_job = self.after(1000, self._tick)

    def stop_timer(self):
        if self._tick_job:
            self.after_cancel(self._tick_job)

    def _stop(self):
        self.stop_timer()
        self._on_stop()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Screen Recorder")
        self.geometry("480x520")
        self.resizable(False, False)
        self.configure(fg_color=BG)

        self._recorder = ScreenRecorder()
        self._monitors = self._get_monitor_list()
        self._bar: FloatingBar | None = None

        self._build_ui()

    # ── monitor helpers ───────────────────────────────────────────────────────
    def _get_monitor_list(self):
        with mss.mss() as sct:
            return [
                f"Monitor {i}  ({m['width']}×{m['height']})"
                for i, m in enumerate(sct.monitors)
                if i > 0
            ]

    def _monitor_index(self):
        sel = self._monitor_var.get()
        try:
            return int(sel.split()[1])
        except (IndexError, ValueError):
            return 1

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        # ── header ────────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(24, 0))

        ctk.CTkLabel(hdr, text="⏺  Screen Recorder",
                     font=("Inter", 20, "bold"), text_color=TEXT).pack(side="left")
        self._status_dot = ctk.CTkLabel(hdr, text="●", font=("Arial", 14),
                                        text_color=GREEN)
        self._status_dot.pack(side="right")
        self._status_lbl = ctk.CTkLabel(hdr, text="Ready", font=FONT_SM,
                                        text_color=TEXT_DIM)
        self._status_lbl.pack(side="right", padx=(0, 4))

        self._divider()

        # ── save path ─────────────────────────────────────────────────────────
        self._section("Output File")
        path_row = ctk.CTkFrame(self, fg_color="transparent")
        path_row.pack(fill="x", padx=24, pady=(4, 0))

        self._path_var = tk.StringVar(value=self._default_path())
        path_entry = ctk.CTkEntry(path_row, textvariable=self._path_var,
                                  height=36, corner_radius=8,
                                  fg_color=CARD, border_color=BORDER,
                                  text_color=TEXT, font=FONT_SM)
        path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(path_row, text="Browse", width=80, height=36,
                      fg_color=CARD, hover_color=BORDER, text_color=TEXT,
                      border_width=1, border_color=BORDER,
                      font=FONT_SM, corner_radius=8,
                      command=self._browse).pack(side="right")

        # ── monitor ───────────────────────────────────────────────────────────
        self._section("Monitor")
        self._monitor_var = tk.StringVar()
        mon_cb = ctk.CTkComboBox(self, values=self._monitors,
                                 variable=self._monitor_var,
                                 height=36, corner_radius=8,
                                 fg_color=CARD, border_color=BORDER,
                                 button_color=BORDER, button_hover_color=ACCENT,
                                 text_color=TEXT, font=FONT_BODY,
                                 dropdown_fg_color=CARD,
                                 dropdown_text_color=TEXT,
                                 dropdown_hover_color=BORDER,
                                 state="readonly")
        mon_cb.pack(fill="x", padx=24, pady=(4, 0))
        if self._monitors:
            mon_cb.set(self._monitors[0])

        # ── FPS ───────────────────────────────────────────────────────────────
        self._section("Frame Rate")
        fps_row = ctk.CTkFrame(self, fg_color="transparent")
        fps_row.pack(fill="x", padx=24, pady=(4, 0))
        self._fps_var = tk.IntVar(value=20)
        for fps in (10, 15, 20, 30):
            ctk.CTkRadioButton(fps_row, text=f"{fps} fps",
                               variable=self._fps_var, value=fps,
                               fg_color=ACCENT, hover_color=ACCENT_H,
                               text_color=TEXT, font=FONT_BODY).pack(
                side="left", padx=(0, 18))

        self._divider()

        # ── record button ─────────────────────────────────────────────────────
        self._rec_btn = ctk.CTkButton(
            self, text="⏺   Start Recording",
            height=52, corner_radius=12,
            fg_color=ACCENT, hover_color=ACCENT_H,
            text_color="white", font=("Inter", 15, "bold"),
            command=self._start)
        self._rec_btn.pack(fill="x", padx=24, pady=(4, 6))

        # ── hint ──────────────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="App hides while recording — use the floating bar to stop.",
                     font=("Inter", 10), text_color=TEXT_DIM).pack()

    def _section(self, title: str):
        ctk.CTkLabel(self, text=title.upper(),
                     font=("Inter", 10, "bold"), text_color=TEXT_DIM,
                     anchor="w").pack(fill="x", padx=24, pady=(14, 0))

    def _divider(self):
        ctk.CTkFrame(self, height=1, fg_color=BORDER).pack(
            fill="x", padx=24, pady=10)

    # ── actions ───────────────────────────────────────────────────────────────
    def _default_path(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        videos = os.path.join(os.path.expanduser("~"), "Videos")
        os.makedirs(videos, exist_ok=True)
        return os.path.join(videos, f"recording_{ts}.mp4")

    def _browse(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 video", "*.mp4")],
            initialfile=os.path.basename(self._path_var.get()),
            initialdir=os.path.dirname(self._path_var.get()),
        )
        if path:
            self._path_var.set(path)

    def _start(self):
        out_path = self._path_var.get().strip()
        if not out_path:
            return

        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        self._recorder.start(out_path, fps=self._fps_var.get(),
                             monitor=self._monitor_index())

        # hide main window
        self.withdraw()

        # show floating bar
        self._bar = FloatingBar(on_stop=self._stop)
        self._bar.start_timer()

    def _stop(self):
        self._recorder.stop()

        if self._bar:
            self._bar.destroy()
            self._bar = None

        out_path = self._path_var.get()
        self._status_lbl.configure(text=f"Saved  ·  {os.path.basename(out_path)}")
        self._status_dot.configure(text_color=GREEN)

        # restore main window with fresh path
        self._path_var.set(self._default_path())
        self.deiconify()
        self.lift()

    def on_close(self):
        if self._recorder.is_recording():
            self._stop()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
