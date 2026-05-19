# Robustness Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix threading race conditions, add error handling to three unprotected code paths, and add a progress bar for the Matchering auto-master flow.

**Architecture:** Two files are modified. `step2_edit.py` gets a generation counter that prevents stale thread results from overwriting session state. `step3_master.py` gets try/except around the export write and an indeterminate `CTkProgressBar` that animates during auto-master processing.

**Tech Stack:** Python 3.13, CustomTkinter, soundfile, threading (stdlib)

---

### Task 1: Generation counter + error handling in `step2_edit.py`

**Files:**
- Modify: `ui/steps/step2_edit.py`

**What this fixes:** Multiple rapid slider moves spawn multiple threads. Without a generation counter the last-to-finish thread wins, which can be a stale result. The try/except ensures processing errors surface in the UI instead of dying silently.

- [ ] **Step 1: Add `_process_gen` attribute**

In `Step2Edit.__init__`, after `self._debounce_id = None`, add:

```python
self._process_gen = 0
```

Full `__init__` after change:
```python
def __init__(self, parent, session: dict, on_back, on_next):
    super().__init__(parent, corner_radius=0, fg_color="transparent")
    self.session = session
    self.on_back = on_back
    self.on_next = on_next
    self._debounce_id = None
    self._process_gen = 0
    self._build_ui()
```

- [ ] **Step 2: Replace `_reprocess` with generation-aware version**

Replace the entire `_reprocess` method (lines 137–153) with:

```python
def _reprocess(self):
    audio = self.session.get("audio_data")
    if audio is None:
        return
    eq_p = self.session["eq_params"]
    lufs_target = self.session["lufs_target"]

    self._process_gen += 1
    gen = self._process_gen

    def _work():
        try:
            eq_out = apply_eq(audio, self.session["sample_rate"],
                              eq_p["low"], eq_p["low_mid"],
                              eq_p["hi_mid"], eq_p["high"])
            limited = apply_limiter(eq_out, self.session["sample_rate"], lufs_target)
            if gen != self._process_gen:
                return
            self.session["processed_audio"] = limited
            self.after(0, lambda: self._player.set_after(limited))
            self.after(0, self._update_lufs_display)
        except Exception as e:
            if gen == self._process_gen:
                self.after(0, lambda err=str(e): self._lufs_current.configure(
                    text=f"Error al procesar: {err}", text_color="#ef4444"
                ))

    threading.Thread(target=_work, daemon=True).start()
```

- [ ] **Step 3: Also reset error text on successful LUFS display**

In `_update_lufs_display`, reset the text color to neutral so a previous error doesn't linger:

```python
def _update_lufs_display(self):
    audio = self.session.get("processed_audio")
    if audio is None:
        return
    lufs = measure_lufs(audio, self.session["sample_rate"])
    self._lufs_current.configure(text=f"actual: {lufs:.1f} LUFS", text_color="#888888")
```

- [ ] **Step 4: Verify the app still launches**

```bash
python main.py
```

Expected: window opens, EQ sliders work, no crash.

- [ ] **Step 5: Commit**

```bash
git add ui/steps/step2_edit.py
git commit -m "fix: generation counter prevents stale EQ results; add error handling to reprocess thread"
```

---

### Task 2: Error handling for export in `step3_master.py`

**Files:**
- Modify: `ui/steps/step3_master.py`

**What this fixes:** If `sf.write` fails (disk full, bad path, permissions), the exception propagates uncaught and the user sees nothing. This wraps it in try/except and shows the error in `_status_label`.

- [ ] **Step 1: Replace `_export` with error-safe version**

Replace the entire `_export` method (lines 231–259) with:

```python
def _export(self):
    audio = self.session.get("mastered_audio")
    if audio is None:
        audio = self.session.get("processed_audio")
    if audio is None:
        return
    sr = self.session["sample_rate"]
    fmt = self._fmt_var.get()

    ext = ".wav" if "WAV" in fmt else ".flac"
    path = filedialog.asksaveasfilename(
        parent=self.winfo_toplevel(),
        defaultextension=ext,
        filetypes=(
            [("WAV", "*.wav"), ("FLAC", "*.flac")]
            if ext == ".wav"
            else [("FLAC", "*.flac"), ("WAV", "*.wav")]
        ),
        initialfile="mastered" + ext,
    )
    if not path:
        return

    subtype = "PCM_24" if "WAV" in fmt else None
    try:
        sf.write(path, audio.T, sr, subtype=subtype)
        filename = path.split("/")[-1].split("\\")[-1]
        self._status_label.configure(
            text=f"💾 Guardado: {filename}", text_color="#4ade80"
        )
    except Exception as e:
        self._status_label.configure(
            text=f"Error al guardar: {e}", text_color="#ef4444"
        )
```

- [ ] **Step 2: Verify the app launches and export button works**

```bash
python main.py
```

Expected: load a file, go to Step 3, click "Guardar archivo", choose a path — file saves and green label appears.

- [ ] **Step 3: Commit**

```bash
git add ui/steps/step3_master.py
git commit -m "fix: catch export errors and show message in status label"
```

---

### Task 3: Indeterminate progress bar for Matchering in `step3_master.py`

**Files:**
- Modify: `ui/steps/step3_master.py`

**What this fixes:** Auto-master runs 10–30 seconds with only a static label for feedback. An animated progress bar makes it clear the app is working.

- [ ] **Step 1: Add the progress bar widget in `_build_ui`**

In `_build_ui`, after the `self._status_label` definition and its `.pack()` call, add:

```python
self._progress = ctk.CTkProgressBar(left, mode="indeterminate", width=260)
# not packed yet — shown only during processing
```

The `self._status_label` block currently looks like:
```python
self._status_label = ctk.CTkLabel(
    left, text="", font=ctk.CTkFont(size=12), wraplength=300
)
self._status_label.pack(padx=14, pady=4)
```

Add the progress bar line immediately after `.pack(padx=14, pady=4)`:
```python
self._status_label = ctk.CTkLabel(
    left, text="", font=ctk.CTkFont(size=12), wraplength=300
)
self._status_label.pack(padx=14, pady=4)
self._progress = ctk.CTkProgressBar(left, mode="indeterminate", width=260)
```

- [ ] **Step 2: Show progress bar when auto-master starts**

In `_run_automaster`, after setting the status label text, add:

```python
self._progress.pack(padx=14, pady=(0, 8))
self._progress.start()
```

Full `_run_automaster` start block after change:
```python
def _run_automaster(self):
    self._automaster_btn.configure(state="disabled", text="⏳ Procesando…")
    self._status_label.configure(
        text="Aplicando matchering, puede tardar unos segundos…",
        text_color="#888888",
    )
    self._progress.pack(padx=14, pady=(0, 8))
    self._progress.start()
    ...
```

- [ ] **Step 3: Stop and hide progress bar on completion**

In `_on_automaster_done`, add before any other configure call:

```python
self._progress.stop()
self._progress.pack_forget()
```

Full method after change:
```python
def _on_automaster_done(self, mastered: np.ndarray, sr: int):
    self._progress.stop()
    self._progress.pack_forget()
    self._automaster_btn.configure(state="normal", text="⚡ Aplicar Auto-Master")
    self._status_label.configure(text="✅ Auto-master aplicado", text_color="#4ade80")
    self._player.set_after(mastered)
    self._update_analysis(self.session.get("processed_audio"), mastered, sr)
```

- [ ] **Step 4: Stop and hide progress bar on error**

In `_on_automaster_error`, add the same two lines:

```python
def _on_automaster_error(self, error: str):
    self._progress.stop()
    self._progress.pack_forget()
    self._automaster_btn.configure(state="normal", text="⚡ Aplicar Auto-Master")
    self._status_label.configure(text=f"Error: {error}", text_color="#ef4444")
```

- [ ] **Step 5: Verify visually**

```bash
python main.py
```

Expected: load a track + reference, go to Step 3, click "Aplicar Auto-Master" — animated bar appears below the status label and disappears when done.

- [ ] **Step 6: Commit**

```bash
git add ui/steps/step3_master.py
git commit -m "feat: indeterminate progress bar during auto-master processing"
```
