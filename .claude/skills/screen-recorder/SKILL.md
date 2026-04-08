---
name: screen-recorder
description: >
  Python desktop screen recorder built with customtkinter, mss, and opencv.
  Use this skill when the user wants to add features, fix bugs, change the UI,
  adjust recording behaviour, or extend the application. Triggers: record,
  capture, fps, monitor, output, save path, floating bar, hide window,
  overlay, codec, export, replay.
compatibility: Python 3.11+, Windows 10/11. Requires mss, opencv-python, numpy, customtkinter.
---

# Screen Recorder — Agent Skill

## Project Layout

```
screen_recorder/
├── main.py          # customtkinter GUI + FloatingBar overlay
├── recorder.py      # ScreenRecorder thread (mss + opencv VideoWriter)
├── requirements.txt
├── run.bat          # Double-click launcher
└── dist/
    └── ScreenRecorder.exe   # Standalone build (PyInstaller --onefile --windowed)
```

## Key Design Decisions

- **Hide-while-recording**: `self.withdraw()` hides the main window on Start;
  `FloatingBar` (borderless `CTkToplevel`, always-on-top, draggable) takes over.
  `self.deiconify()` restores the main window when Stop is pressed.
- **Threading**: recording runs in a `daemon=True` thread so the GUI stays
  responsive. The thread writes frames via `cv2.VideoWriter` (mp4v codec).
- **Frame pacing**: each loop iteration sleeps `max(0, frame_duration - elapsed)`
  to hit the target FPS without busy-waiting.
- **Colour palette**: dark `#0f1117` background, `#1a1d27` cards, `#4f8ef7` accent.

## Extending the App

### Add pause/resume
1. Add `self._paused = False` to `ScreenRecorder`.
2. In `_record_loop`, check `self._paused` and `time.sleep(0.05)` while paused.
3. Expose `pause()` / `resume()` methods.
4. Add a Pause button to `FloatingBar` that calls these.

### Add audio recording
Use `sounddevice` + `soundfile` to record a WAV in a parallel thread,
then mux with `ffmpeg` (subprocess) after both streams stop.

### Change output codec
Replace `"mp4v"` in `recorder.py` with `"avc1"` (H.264) or `"XVID"` (AVI).
Update the file extension accordingly.

### Add multi-monitor selection
`mss.mss().monitors[0]` is the virtual combined display — pass index 0 to
capture all monitors at once.

### Build a new EXE after changes
```bash
pyinstaller --onefile --windowed --name "ScreenRecorder" main.py
```
Output lands in `dist/ScreenRecorder.exe`.

## Common Pitfalls

- `cv2.VideoWriter` silently fails if the output directory does not exist —
  always `os.makedirs(out_dir, exist_ok=True)` before opening the writer.
- `mss` returns BGRA frames; convert with `cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)`
  before writing, otherwise colours are wrong.
- `CTkToplevel` windows must be created **after** the main `CTk()` loop starts,
  not at module level, or Tk raises a `RuntimeError`.
- PyInstaller `--windowed` suppresses the console; remove it when debugging so
  you see tracebacks.
