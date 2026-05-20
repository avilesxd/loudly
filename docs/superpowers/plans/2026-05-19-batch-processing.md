# Batch Processing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a batch processing window that lets the user auto-master multiple tracks against a single reference and export them automatically as `<stem>_remastered.wav` in their original folder.

**Architecture:** A new self-contained `CTkToplevel` (`BatchWindow`) is launched from Step 1 via a secondary button. It owns its own list of `BatchItem` dataclasses, runs matchering sequentially in a daemon thread, and exports each result without user interaction. The existing single-track wizard is unchanged.

**Tech Stack:** customtkinter (CTkToplevel, CTkScrollableFrame), soundfile, matchering (via `audio.automaster.apply_automaster`), threading, dataclasses, tempfile

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `ui/batch_window.py` | **Create** | BatchItem dataclass, output path helper, BatchWindow UI + processing |
| `ui/steps/step1_load.py` | **Modify** | Add secondary "batch" button that opens BatchWindow |
| `tests/test_batch_window.py` | **Create** | Tests for pure logic (path helper, deduplication) |

---

### Task 1: BatchItem dataclass and output path helper

**Files:**
- Create: `ui/batch_window.py`
- Create: `tests/test_batch_window.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_batch_window.py`:

```python
import pytest
from ui.batch_window import _remastered_path, BatchItem


def test_remastered_path_wav():
    assert _remastered_path("/music/track_a.wav") == "/music/track_a_remastered.wav"


def test_remastered_path_flac():
    assert _remastered_path("/music/track_b.flac") == "/music/track_b_remastered.wav"


def test_remastered_path_mp3():
    assert _remastered_path("/some/folder/my track.mp3") == "/some/folder/my track_remastered.wav"


def test_batch_item_defaults():
    item = BatchItem(path="/music/a.wav")
    assert item.status == "pending"
    assert item.message == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_batch_window.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `ui/batch_window.py` does not exist yet.

- [ ] **Step 3: Create `ui/batch_window.py` with the dataclass and helper**

```python
import os
import tempfile
import threading
from dataclasses import dataclass, field
from tkinter import filedialog
from typing import Literal

import customtkinter as ctk
import soundfile as sf

from audio.automaster import apply_automaster
from audio.loader import load_audio

SUPPORTED = (
    ("Audio files", "*.wav *.mp3 *.flac *.aiff *.aif"),
    ("All files", "*.*"),
)


@dataclass
class BatchItem:
    path: str
    status: Literal["pending", "processing", "done", "error"] = "pending"
    message: str = ""


def _remastered_path(source_path: str) -> str:
    stem, _ = os.path.splitext(source_path)
    return stem + "_remastered.wav"
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_batch_window.py -v
```

Expected: 4 PASSED.

- [ ] **Step 5: Commit**

```
git add ui/batch_window.py tests/test_batch_window.py
git commit -m "feat: add BatchItem dataclass and output path helper"
```

---

### Task 2: Deduplication logic tests

**Files:**
- Modify: `tests/test_batch_window.py`

The `BatchWindow` will expose a method `_add_paths(paths: list[str])` that appends new items, ignoring duplicates by path. Test this logic in isolation before building the UI.

- [ ] **Step 1: Add deduplication tests**

Append to `tests/test_batch_window.py`:

```python
from unittest.mock import patch, MagicMock


def _make_window():
    """Create a BatchWindow without displaying it."""
    with patch("ui.batch_window.ctk.CTkToplevel.__init__", return_value=None), \
         patch("ui.batch_window.BatchWindow._build_ui"):
        win = object.__new__(__import__("ui.batch_window", fromlist=["BatchWindow"]).BatchWindow)
        win._items = []
        win._rows = []
        win._ref_path = None
        win._cancel = False
        win._worker_thread = None
        return win


def test_add_paths_appends_items():
    win = _make_window()
    win._items = []

    # simulate _add_paths logic directly
    paths = ["/a/track1.wav", "/a/track2.flac"]
    existing = {item.path for item in win._items}
    for p in paths:
        if p not in existing:
            win._items.append(BatchItem(path=p))
            existing.add(p)

    assert len(win._items) == 2
    assert win._items[0].path == "/a/track1.wav"


def test_add_paths_ignores_duplicates():
    win = _make_window()
    win._items = [BatchItem(path="/a/track1.wav")]

    paths = ["/a/track1.wav", "/a/track2.flac"]
    existing = {item.path for item in win._items}
    for p in paths:
        if p not in existing:
            win._items.append(BatchItem(path=p))
            existing.add(p)

    assert len(win._items) == 2  # not 3
```

- [ ] **Step 2: Run tests to verify they pass**

```
pytest tests/test_batch_window.py -v
```

Expected: all PASSED (the logic is tested directly without needing a real window).

- [ ] **Step 3: Commit**

```
git add tests/test_batch_window.py
git commit -m "test: add deduplication logic tests for BatchWindow"
```

---

### Task 3: BatchWindow UI skeleton

**Files:**
- Modify: `ui/batch_window.py`

Add the full `BatchWindow` class with layout but no processing logic yet. The "Procesar todos" button will exist but be disabled.

- [ ] **Step 1: Add BatchWindow class to `ui/batch_window.py`**

Append after `_remastered_path`:

```python
class BatchWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Batch Processing")
        self.geometry("620x480")
        self.resizable(False, False)

        self._items: list[BatchItem] = []
        self._rows: list[dict] = []  # {"name": CTkLabel, "status": CTkLabel}
        self._ref_path: str | None = None
        self._cancel = False
        self._worker_thread: threading.Thread | None = None

        self._build_ui()

    def _build_ui(self):
        # Reference row
        ref_frame = ctk.CTkFrame(self, fg_color="transparent")
        ref_frame.pack(fill="x", padx=20, pady=(16, 8))

        ctk.CTkLabel(
            ref_frame,
            text="Referencia:",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left")

        self._ref_label = ctk.CTkLabel(
            ref_frame,
            text="no seleccionada",
            text_color="#888888",
            font=ctk.CTkFont(size=12),
        )
        self._ref_label.pack(side="left", padx=10)

        ctk.CTkButton(
            ref_frame,
            text="Elegir",
            width=70,
            command=self._pick_reference,
            fg_color="#1e1e2e",
            hover_color="#2d2d3e",
        ).pack(side="right")

        # Scrollable track list
        self._list_frame = ctk.CTkScrollableFrame(self, height=280)
        self._list_frame.pack(fill="x", padx=20, pady=8)

        self._empty_label = ctk.CTkLabel(
            self._list_frame,
            text="No hay tracks cargados",
            text_color="#555555",
            font=ctk.CTkFont(size=12),
        )
        self._empty_label.pack(pady=20)

        # Bottom buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=12)

        ctk.CTkButton(
            btn_frame,
            text="+ Agregar tracks",
            command=self._add_tracks,
            fg_color="#1e1e2e",
            hover_color="#2d2d3e",
            width=160,
        ).pack(side="left")

        self._process_btn = ctk.CTkButton(
            btn_frame,
            text="⚡ Procesar todos",
            command=self._start_batch,
            state="disabled",
            width=180,
        )
        self._process_btn.pack(side="right")

        self._status_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12), text_color="#888888"
        )
        self._status_label.pack(pady=(0, 8))
```

- [ ] **Step 2: Run the app manually and verify the window opens**

```
python main.py
```

Expected: app launches, Step 1 visible (batch button not wired yet — that's Task 6).

- [ ] **Step 3: Commit**

```
git add ui/batch_window.py
git commit -m "feat: add BatchWindow UI skeleton"
```

---

### Task 4: Track list management and reference selector

**Files:**
- Modify: `ui/batch_window.py`

Implement `_add_tracks`, `_pick_reference`, `_add_row`, and the enable/disable logic for the process button.

- [ ] **Step 1: Add the four methods to `BatchWindow`**

Add these methods inside the `BatchWindow` class (after `_build_ui`):

```python
    def _pick_reference(self):
        path = filedialog.askopenfilename(
            parent=self, filetypes=SUPPORTED, title="Seleccionar referencia"
        )
        if not path:
            return
        self._ref_path = path
        self._ref_label.configure(
            text=os.path.basename(path), text_color="#60a5fa"
        )
        self._refresh_process_btn()

    def _add_tracks(self):
        paths = filedialog.askopenfilenames(
            parent=self, filetypes=SUPPORTED, title="Seleccionar tracks"
        )
        if not paths:
            return
        existing = {item.path for item in self._items}
        for path in paths:
            if path in existing:
                continue
            item = BatchItem(path=path)
            self._items.append(item)
            existing.add(path)
            self._add_row(item)
        if self._items:
            self._empty_label.pack_forget()
        self._refresh_process_btn()

    def _add_row(self, item: BatchItem):
        row = ctk.CTkFrame(self._list_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)

        name_lbl = ctk.CTkLabel(
            row,
            text=os.path.basename(item.path),
            font=ctk.CTkFont(size=12),
            anchor="w",
            width=380,
        )
        name_lbl.pack(side="left")

        status_lbl = ctk.CTkLabel(
            row,
            text="⏳ en cola",
            font=ctk.CTkFont(size=12),
            text_color="#888888",
            width=160,
            anchor="w",
        )
        status_lbl.pack(side="left")

        self._rows.append({"name": name_lbl, "status": status_lbl})

    def _refresh_process_btn(self):
        can_run = (
            bool(self._items)
            and self._ref_path is not None
            and (self._worker_thread is None or not self._worker_thread.is_alive())
        )
        self._process_btn.configure(state="normal" if can_run else "disabled")
```

- [ ] **Step 2: Wire the window close event to set the cancel flag**

Add this at the end of `__init__`, after `self._build_ui()`:

```python
        self.protocol("WM_DELETE_WINDOW", self._on_close)
```

And add the method:

```python
    def _on_close(self):
        self._cancel = True
        self.destroy()
```

- [ ] **Step 3: Run the app manually — open batch window via Python console or temp wire**

Temporarily add to the bottom of `ui/batch_window.py` to test standalone:

```python
if __name__ == "__main__":
    import customtkinter as ctk
    root = ctk.CTk()
    root.withdraw()
    w = BatchWindow(root)
    root.mainloop()
```

Run:
```
python ui/batch_window.py
```

Expected: BatchWindow opens. "Elegir" lets you pick a reference, "+ Agregar tracks" lets you pick multiple files, rows appear in the list, "⚡ Procesar todos" enables only when both tracks and reference are loaded.

- [ ] **Step 4: Remove the `if __name__ == "__main__"` block**

Delete the test block added in Step 3.

- [ ] **Step 5: Commit**

```
git add ui/batch_window.py
git commit -m "feat: add track list management and reference selector to BatchWindow"
```

---

### Task 5: Sequential batch processing engine

**Files:**
- Modify: `ui/batch_window.py`

Implement `_start_batch` and `_process_all` (the daemon thread worker).

- [ ] **Step 1: Add `_start_batch` and `_process_all` to `BatchWindow`**

```python
    def _start_batch(self):
        self._cancel = False
        self._process_btn.configure(state="disabled", text="⏳ Procesando…")
        self._status_label.configure(text="Procesando…", text_color="#888888")
        self._worker_thread = threading.Thread(
            target=self._process_all, daemon=True
        )
        self._worker_thread.start()

    def _process_all(self):
        pending = [
            (i, item) for i, item in enumerate(self._items)
            if item.status == "pending"
        ]
        total = len(pending)

        for done_count, (idx, item) in enumerate(pending, start=1):
            if self._cancel:
                break

            self.after(0, lambda i=idx: self._set_row_status(
                i, "⚙️ procesando…", "#f59e0b"
            ))

            tmp_in = tmp_out = None
            try:
                audio, sr = load_audio(item.path)

                ref_info = sf.info(self._ref_path)
                if ref_info.samplerate != sr:
                    raise ValueError(
                        f"Sample rate mismatch: track={sr} Hz, "
                        f"ref={ref_info.samplerate} Hz"
                    )

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_in = f.name
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_out = f.name

                import numpy as np
                sf.write(tmp_in, audio.T, sr, subtype="PCM_24")
                apply_automaster(tmp_in, self._ref_path, tmp_out)

                mastered, _ = load_audio(tmp_out)
                out_path = _remastered_path(item.path)
                sf.write(out_path, mastered.T, sr, subtype="PCM_24")

                item.status = "done"
                self.after(0, lambda i=idx: self._set_row_status(
                    i, "✅ listo", "#4ade80"
                ))

            except Exception as e:
                msg = str(e)[:60]
                item.status = "error"
                item.message = msg
                self.after(0, lambda i=idx, m=msg: self._set_row_status(
                    i, f"❌ {m}", "#ef4444"
                ))

            finally:
                for p in (tmp_in, tmp_out):
                    if p and os.path.exists(p):
                        try:
                            os.unlink(p)
                        except OSError:
                            pass

            self.after(0, lambda n=done_count, t=total: self._status_label.configure(
                text=f"{n}/{t} procesados", text_color="#888888"
            ))

        if not self._cancel:
            done = sum(1 for item in self._items if item.status == "done")
            errors = sum(1 for item in self._items if item.status == "error")
            self.after(0, lambda d=done, e=errors: self._on_batch_done(d, e))

    def _set_row_status(self, idx: int, text: str, color: str):
        if idx < len(self._rows):
            self._rows[idx]["status"].configure(text=text, text_color=color)

    def _on_batch_done(self, done: int, errors: int):
        self._process_btn.configure(state="normal", text="⚡ Procesar todos")
        if errors == 0:
            self._status_label.configure(
                text=f"✅ {done} track(s) exportados exitosamente",
                text_color="#4ade80",
            )
        else:
            self._status_label.configure(
                text=f"✅ {done} listo(s) — ❌ {errors} con error",
                text_color="#f59e0b",
            )
```

- [ ] **Step 2: Add `import numpy as np` at the top of `ui/batch_window.py`**

The `import numpy as np` inside `_process_all` was intentional to show where it's used, but move it to the top-level imports:

At the top of `ui/batch_window.py`, add:

```python
import numpy as np
```

And remove the `import numpy as np` line from inside `_process_all`.

- [ ] **Step 3: Commit**

```
git add ui/batch_window.py
git commit -m "feat: implement sequential batch processing engine in BatchWindow"
```

---

### Task 6: Wire batch button in Step 1

**Files:**
- Modify: `ui/steps/step1_load.py`

Add a secondary button below the existing track picker that opens `BatchWindow`.

- [ ] **Step 1: Add the import to `step1_load.py`**

At the top of `ui/steps/step1_load.py`, after the existing imports, add:

```python
from ui.batch_window import BatchWindow
```

- [ ] **Step 2: Add the batch button in `_build_ui`**

In `Step1Load._build_ui`, after the `self._pick_btn.pack(pady=(0, 12))` line (line 63), add:

```python
        ctk.CTkButton(
            track_frame,
            text="Procesar múltiples tracks (batch)",
            command=self._open_batch,
            width=220,
            fg_color="#1e1e2e",
            hover_color="#2d2d3e",
            font=ctk.CTkFont(size=12),
        ).pack(pady=(0, 8))
```

- [ ] **Step 3: Add `_open_batch` method to `Step1Load`**

After the `_advance` method, add:

```python
    def _open_batch(self):
        BatchWindow(self.winfo_toplevel())
```

- [ ] **Step 4: Run the app and test the full batch flow manually**

```
python main.py
```

Test steps:
1. Click "Procesar múltiples tracks (batch)" — BatchWindow opens
2. Click "Elegir" — pick any audio file as reference
3. Click "+ Agregar tracks" — pick 2+ audio files
4. Verify rows appear with "⏳ en cola" status
5. Verify "⚡ Procesar todos" becomes enabled
6. Click "⚡ Procesar todos"
7. Verify rows update: "⚙️ procesando…" → "✅ listo" (or "❌ …" on error)
8. Verify `_remastered.wav` files appear next to the source files
9. Close window mid-batch — verify no crash

- [ ] **Step 5: Run the full test suite**

```
pytest tests/ -v
```

Expected: all existing tests still pass, new `test_batch_window.py` tests pass.

- [ ] **Step 6: Commit**

```
git add ui/steps/step1_load.py
git commit -m "feat: wire batch processing button in Step 1"
```

---

## Self-Review

**Spec coverage:**
- ✅ New `BatchWindow` (CTkToplevel) launched from Step 1
- ✅ Secondary button in Step 1 — existing flow unchanged
- ✅ Track list with status per row (pending/processing/done/error)
- ✅ Reference selector shared across all tracks
- ✅ Sequential processing (one thread, no parallelism)
- ✅ Export to `<stem>_remastered.wav` in same folder as source
- ✅ Sample rate mismatch → error on that item, continue
- ✅ matchering exception → error on that item, continue
- ✅ File write error → error on that item, continue
- ✅ Cancel on window close via `_cancel` flag
- ✅ "Procesar todos" disabled until tracks + reference loaded
- ✅ Duplicates ignored silently in `_add_tracks`
- ✅ WAV 24-bit output always (matchering requirement)

**Type consistency:**
- `BatchItem.path`, `.status`, `.message` used consistently across all tasks
- `_remastered_path(source_path: str) -> str` consistent across tasks 1 and 5
- `_set_row_status(idx, text, color)` defined in Task 5 and called from Task 5
- `self._rows` is `list[dict]` with keys `"name"` and `"status"` — consistent
