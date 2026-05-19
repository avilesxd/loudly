# Robustness Fixes — Design Spec

**Date:** 2026-05-19  
**Scope:** Threading race conditions, error handling, Matchering UX feedback

---

## 1. Threading — Generation counter (`step2_edit.py`)

**Problem:** `_reprocess` spawns a background thread on every debounce fire. If the user moves sliders rapidly, multiple threads can finish out-of-order and overwrite `session["processed_audio"]` with a stale result.

**Fix:** Add `_process_gen: int = 0` to `Step2Edit`. Each call to `_reprocess` increments it and captures the current value in the thread closure. Before writing results back, the thread checks that its captured generation still matches — if not, it discards the result silently.

```python
self._process_gen += 1
gen = self._process_gen

def _work():
    try:
        ...compute limited...
        if gen != self._process_gen:
            return
        self.session["processed_audio"] = limited
        self.after(0, lambda: self._player.set_after(limited))
        self.after(0, self._update_lufs_display)
    except Exception as e:
        if gen == self._process_gen:
            self.after(0, lambda: self._lufs_current.configure(
                text=f"Error: {e}", text_color="#ef4444"
            ))
```

**Why this works:** The generation counter is only written on the main thread (inside `_reprocess`, which is called via `self.after()`). The threads only read it. No lock needed.

---

## 2. Error Handling

### 2a. `step2_edit.py` — `_reprocess._work`

Wrap the `_work` body in try/except. On failure, post error text to `_lufs_current` via `self.after(0, ...)` only if generation still matches (avoids showing an error from an already-superseded request).

### 2b. `step3_master.py` — `_export`

Wrap `sf.write` in try/except. On failure, show the error message in `_status_label` with red color. The export button stays enabled so the user can retry.

```python
try:
    sf.write(path, audio.T, sr, subtype=subtype)
    self._status_label.configure(text=f"💾 Guardado: {filename}", text_color="#4ade80")
except Exception as e:
    self._status_label.configure(text=f"Error al guardar: {e}", text_color="#ef4444")
```

### 2c. `step3_master.py` — `_run_automaster` (existing)

Already has try/except. No changes needed beyond verifying the error message is clear (already shows `f"Error: {error}"`).

---

## 3. Matchering — Indeterminate Progress Bar (`step3_master.py`)

**Problem:** Auto-master can take 10–30 seconds. The only feedback is a static label "puede tardar unos segundos…" which looks frozen.

**Fix:** Add a `ctk.CTkProgressBar` in `indeterminate` mode below the status label in the left column.

- `_run_automaster`: call `_progress.start()` before spawning the thread
- `_on_automaster_done`: call `_progress.stop()` and `_progress.set(0)`
- `_on_automaster_error`: same stop/reset

The progress bar is hidden (`pack_forget`) when not in use and shown (`pack`) only during processing.

---

## Files Changed

| File | Changes |
|---|---|
| `ui/steps/step2_edit.py` | Add `_process_gen`, generation check in `_reprocess`, try/except in `_work` |
| `ui/steps/step3_master.py` | Add `CTkProgressBar`, wrap `_export` in try/except |
