# Batch Processing — Design Spec

**Date:** 2026-05-19  
**Status:** Approved

## Overview

Add a batch processing mode that lets the user select multiple main tracks, choose a single reference, and auto-master + export all of them sequentially. Exports are saved automatically to the same folder as each source file with a `_remastered` suffix.

## Scope

- New `BatchWindow` class (CTkToplevel) launched from Step 1
- Step 1 gets a secondary "Procesar múltiples tracks (batch)" button
- No changes to the existing single-track wizard flow

## Architecture

### New file: `ui/batch_window.py`

`BatchWindow` is a self-contained `CTkToplevel` that owns its entire lifecycle:
- Holds its own list of `BatchItem` dataclass instances (path, status, message)
- Runs matchering sequentially in a single daemon thread
- Updates the UI via `self.after(0, ...)` calls from that thread

```
BatchWindow
  ├── _items: list[BatchItem]        # mutable state
  ├── _ref_path: str | None
  ├── _rows: list[BatchRow]          # one CTkFrame per item (label + status label)
  └── _worker_thread: Thread | None
```

`BatchItem` is a simple dataclass:

```python
@dataclass
class BatchItem:
    path: str
    status: Literal["pending", "processing", "done", "error"]
    message: str = ""
```

### Step 1 change

Add a second button below the existing "Seleccionar track principal" button:

```
[ Seleccionar track principal      ]
[ Procesar múltiples tracks (batch)]
```

The batch button calls `BatchWindow(self)` — no session involvement.

## UI Layout (BatchWindow)

```
┌─────────────────────────────────────────────┐
│  Batch Processing                           │
│                                             │
│  Referencia: [ no seleccionada ] [Elegir]   │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │ track_a.wav            ⏳ en cola     │  │
│  │ track_b.flac           ⏳ en cola     │  │
│  │ track_c.wav            ⏳ en cola     │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  [ + Agregar tracks ]  [ ⚡ Procesar todos ]│
└─────────────────────────────────────────────┘
```

Status column values:
- `⏳ en cola` — grey
- `⚙️ procesando…` — yellow `#f59e0b`
- `✅ listo` — green `#4ade80`
- `❌ <error corto>` — red `#ef4444`

The "Procesar todos" button is disabled until at least one track and a reference are loaded. It becomes disabled again while processing is running.

## Processing Logic

Sequential processing in one daemon thread:

```
for each item in _items where status == "pending":
    update item.status → "processing"
    load audio from item.path → numpy array
    write temp WAV (PCM_24)
    check sample rates match (ref vs track) → error if not
    apply_automaster(tmp_in, ref_path, tmp_out)
    load result → numpy array
    determine output path:
        stem, ext = splitext(item.path)
        out_path = stem + "_remastered.wav"
    sf.write(out_path, mastered.T, sr, subtype="PCM_24")
    update item.status → "done"
    clean up temp files
```

Output format is always **WAV 24-bit**, regardless of input format (consistent with matchering's output).

Output path rule: `<original_dir>/<stem>_remastered.wav`  
Example: `/music/track_a.flac` → `/music/track_a_remastered.wav`

## Error Handling

- Sample rate mismatch between any track and reference → that item marked error, processing continues with next
- matchering exception → item marked error with truncated message (max 60 chars), continue
- File write error → item marked error, continue
- The reference path is validated (file exists) before starting the batch run

## Constraints

- No parallelism — one track at a time to avoid saturating CPU/RAM
- BatchWindow does not share `session` with the main wizard (fully independent)
- "Agregar tracks" can be called multiple times to append more files; duplicates (same path) are silently ignored
- The window can be closed mid-batch; the daemon thread will finish the current track then stop (checked via a `_cancel` flag)

## Files Changed

| File | Change |
|------|--------|
| `ui/batch_window.py` | **New** — BatchWindow + BatchItem |
| `ui/steps/step1_load.py` | Add batch button → launch BatchWindow |
