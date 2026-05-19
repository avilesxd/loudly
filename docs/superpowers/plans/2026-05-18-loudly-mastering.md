# Loudly — Masterizador de Audio Desktop — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir una aplicación de escritorio Windows (Python → .exe) para masterizar audio con EQ de 4 bandas, limitador con control LUFS, y auto-masterización por referencia usando matchering.

**Architecture:** Wizard de 3 pasos (cargar → editar → masterizar) con un diccionario `session` como estado compartido entre pasos. Los módulos de audio son independientes de la UI y se prueban con pytest. El reproductor usa sounddevice con buffers intercambiables para toggle antes/después.

**Tech Stack:** Python 3.11, CustomTkinter, pedalboard (Spotify), matchering, pyloudnorm, sounddevice, soundfile, pydub, matplotlib, PyInstaller

---

## Convenciones de audio (leer antes de empezar)

- **Formato interno:** `np.ndarray` shape `(channels, samples)`, dtype `float32` — coincide con lo que espera pedalboard.
- **soundfile** lee/escribe `(samples, channels)` → siempre transponer al cargar y al exportar.
- **pyloudnorm** espera `(samples, channels)` → usar `audio.T` al llamarlo.
- **sounddevice** reproduce `(samples, channels)` → usar `audio.T` al reproducir.

---

## File structure

```
loudly/
├── main.py
├── app.py
├── audio/
│   ├── __init__.py
│   ├── loader.py        # carga archivos → np.ndarray (channels, samples)
│   ├── eq.py            # EQ 4 bandas via pedalboard
│   ├── limiter.py       # Limiter + LUFS normalization via pyloudnorm + pedalboard
│   └── automaster.py    # wrapper de matchering
├── ui/
│   ├── __init__.py
│   ├── steps/
│   │   ├── __init__.py
│   │   ├── step1_load.py
│   │   ├── step2_edit.py
│   │   └── step3_master.py
│   └── components/
│       ├── __init__.py
│       ├── waveform.py   # matplotlib embedded en CTkFrame
│       └── player.py     # AudioPlayer con before/after toggle
├── tests/
│   ├── __init__.py
│   ├── conftest.py       # fixtures: generate_wav_file
│   ├── test_loader.py
│   ├── test_eq.py
│   ├── test_limiter.py
│   └── test_automaster.py
├── requirements.txt
└── loudly.spec           # PyInstaller config
```

---

## Task 1: Project setup

**Files:**
- Create: `requirements.txt`
- Create: `tests/conftest.py`
- Create: todos los `__init__.py`

- [ ] **Step 1: Crear estructura de carpetas**

```bash
cd C:/Users/inico/dev/loudly
mkdir -p audio ui/steps ui/components tests
```

- [ ] **Step 2: Crear requirements.txt**

```
customtkinter>=5.2.2
pedalboard>=0.9.9
matchering>=2.0.6
pyloudnorm>=0.1.1
sounddevice>=0.4.6
soundfile>=0.12.1
numpy>=1.24.0
matplotlib>=3.7.0
pydub>=0.25.1
pytest>=7.4.0
pyinstaller>=6.3.0
```

- [ ] **Step 3: Instalar dependencias**

```bash
pip install -r requirements.txt
```

- [ ] **Step 4: Crear conftest.py con fixture de audio de prueba**

```python
# tests/conftest.py
import numpy as np
import soundfile as sf
import pytest
import tempfile
import os

@pytest.fixture
def sine_wav(tmp_path):
    """Genera un archivo WAV de 3 segundos con un tono de 440 Hz a -18 LUFS aprox."""
    sample_rate = 44100
    duration = 3.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Señal estéreo de amplitud moderada
    signal = (np.sin(2 * np.pi * 440 * t) * 0.1).astype(np.float32)
    audio = np.stack([signal, signal])  # (2, samples)
    path = str(tmp_path / "test_sine.wav")
    sf.write(path, audio.T, sample_rate, subtype="FLOAT")
    return path, audio, sample_rate
```

- [ ] **Step 5: Crear todos los __init__.py vacíos**

```bash
touch audio/__init__.py ui/__init__.py ui/steps/__init__.py ui/components/__init__.py tests/__init__.py
```

En Windows PowerShell:
```powershell
"" | Out-File audio/__init__.py
"" | Out-File ui/__init__.py
"" | Out-File ui/steps/__init__.py
"" | Out-File ui/components/__init__.py
"" | Out-File tests/__init__.py
```

- [ ] **Step 6: Verificar que pytest corre sin errores**

```bash
pytest tests/ -v
```
Expected: `no tests ran` (0 errors, 0 failures)

- [ ] **Step 7: Commit**

```bash
git init
git add .
git commit -m "chore: project setup — structure, deps, test fixtures"
```

---

## Task 2: Audio loader

**Files:**
- Create: `audio/loader.py`
- Create: `tests/test_loader.py`

- [ ] **Step 1: Escribir el test**

```python
# tests/test_loader.py
import numpy as np
import pytest
from audio.loader import load_audio

def test_load_wav_returns_float32_channels_first(sine_wav):
    path, original_audio, sr = sine_wav
    audio, sample_rate = load_audio(path)
    assert audio.dtype == np.float32
    assert audio.ndim == 2
    assert audio.shape[0] <= 2          # channels first, max 2 (stereo)
    assert audio.shape[1] > 0           # tiene samples
    assert sample_rate == 44100

def test_load_audio_values_in_range(sine_wav):
    path, _, _ = sine_wav
    audio, _ = load_audio(path)
    assert audio.max() <= 1.0
    assert audio.min() >= -1.0

def test_load_unsupported_format_raises(tmp_path):
    bad_file = tmp_path / "file.xyz"
    bad_file.write_bytes(b"not audio")
    with pytest.raises(ValueError, match="Formato no soportado"):
        load_audio(str(bad_file))
```

- [ ] **Step 2: Verificar que el test falla**

```bash
pytest tests/test_loader.py -v
```
Expected: `ImportError` o `ModuleNotFoundError`

- [ ] **Step 3: Implementar loader.py**

```python
# audio/loader.py
import numpy as np
import soundfile as sf
from pydub import AudioSegment
import tempfile
import os

SUPPORTED_EXTENSIONS = {".wav", ".flac", ".aiff", ".aif"}
PYDUB_EXTENSIONS = {".mp3"}

def load_audio(path: str) -> tuple[np.ndarray, int]:
    """
    Carga un archivo de audio y retorna (audio, sample_rate).
    audio shape: (channels, samples), dtype float32.
    """
    ext = os.path.splitext(path)[1].lower()

    if ext in PYDUB_EXTENSIONS:
        path = _convert_to_wav(path)
        ext = ".wav"

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Formato no soportado: {ext}")

    data, sample_rate = sf.read(path, dtype="float32", always_2d=True)
    # soundfile → (samples, channels); transponemos a (channels, samples)
    audio = data.T
    return audio, sample_rate

def _convert_to_wav(path: str) -> str:
    """Convierte MP3 a WAV temporal y retorna la ruta del WAV."""
    segment = AudioSegment.from_mp3(path)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    segment.export(tmp.name, format="wav")
    return tmp.name
```

- [ ] **Step 4: Correr tests**

```bash
pytest tests/test_loader.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add audio/loader.py tests/test_loader.py
git commit -m "feat: audio loader — WAV/FLAC/AIFF/MP3 → float32 (channels, samples)"
```

---

## Task 3: EQ module

**Files:**
- Create: `audio/eq.py`
- Create: `tests/test_eq.py`

- [ ] **Step 1: Escribir el test**

```python
# tests/test_eq.py
import numpy as np
import pytest
from audio.eq import apply_eq

def test_eq_with_zero_gains_is_passthrough(sine_wav):
    path, original_audio, sr = sine_wav
    result = apply_eq(original_audio, sr, 0.0, 0.0, 0.0, 0.0)
    assert result.shape == original_audio.shape
    assert result.dtype == np.float32
    # Con ganancias 0 el resultado debe ser casi idéntico al original
    np.testing.assert_allclose(result, original_audio, atol=1e-4)

def test_eq_positive_gain_increases_rms(sine_wav):
    path, audio, sr = sine_wav
    boosted = apply_eq(audio, sr, low_gain=6.0, low_mid_gain=0.0,
                       hi_mid_gain=0.0, high_gain=0.0)
    assert boosted.std() > audio.std()

def test_eq_negative_gain_decreases_rms(sine_wav):
    path, audio, sr = sine_wav
    cut = apply_eq(audio, sr, low_gain=-6.0, low_mid_gain=0.0,
                   hi_mid_gain=0.0, high_gain=0.0)
    assert cut.std() < audio.std()

def test_eq_output_shape_matches_input(sine_wav):
    path, audio, sr = sine_wav
    result = apply_eq(audio, sr, 3.0, -2.0, 1.5, -1.0)
    assert result.shape == audio.shape
```

- [ ] **Step 2: Verificar que el test falla**

```bash
pytest tests/test_eq.py -v
```
Expected: ImportError

- [ ] **Step 3: Implementar eq.py**

```python
# audio/eq.py
import numpy as np
from pedalboard import Pedalboard, LowShelfFilter, HighShelfFilter, PeakFilter

def apply_eq(
    audio: np.ndarray,
    sample_rate: int,
    low_gain: float = 0.0,      # 80 Hz shelf
    low_mid_gain: float = 0.0,  # 250 Hz peak
    hi_mid_gain: float = 0.0,   # 2500 Hz peak
    high_gain: float = 0.0,     # 8000 Hz shelf
) -> np.ndarray:
    """
    Aplica EQ de 4 bandas.
    audio: (channels, samples) float32
    Retorna: (channels, samples) float32
    """
    if all(g == 0.0 for g in [low_gain, low_mid_gain, hi_mid_gain, high_gain]):
        return audio.copy()

    board = Pedalboard([
        LowShelfFilter(cutoff_frequency_hz=80.0, gain_db=low_gain, q=0.707),
        PeakFilter(cutoff_frequency_hz=250.0, gain_db=low_mid_gain, q=1.0),
        PeakFilter(cutoff_frequency_hz=2500.0, gain_db=hi_mid_gain, q=1.0),
        HighShelfFilter(cutoff_frequency_hz=8000.0, gain_db=high_gain, q=0.707),
    ])
    return board(audio, sample_rate)
```

- [ ] **Step 4: Correr tests**

```bash
pytest tests/test_eq.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add audio/eq.py tests/test_eq.py
git commit -m "feat: 4-band EQ module via pedalboard"
```

---

## Task 4: Limiter + LUFS module

**Files:**
- Create: `audio/limiter.py`
- Create: `tests/test_limiter.py`

- [ ] **Step 1: Escribir el test**

```python
# tests/test_limiter.py
import numpy as np
import pytest
import pyloudnorm as pyln
from audio.limiter import apply_limiter, measure_lufs

def test_measure_lufs_returns_float(sine_wav):
    path, audio, sr = sine_wav
    lufs = measure_lufs(audio, sr)
    assert isinstance(lufs, float)
    assert -60.0 < lufs < 0.0

def test_apply_limiter_reaches_target_lufs(sine_wav):
    path, audio, sr = sine_wav
    target = -14.0
    result = apply_limiter(audio, sr, target_lufs=target)
    measured = measure_lufs(result, sr)
    # Tolerancia de 0.5 LUFS
    assert abs(measured - target) < 0.5

def test_apply_limiter_no_clipping(sine_wav):
    path, audio, sr = sine_wav
    result = apply_limiter(audio, sr, target_lufs=-14.0)
    assert result.max() <= 1.0
    assert result.min() >= -1.0

def test_apply_limiter_output_shape_matches_input(sine_wav):
    path, audio, sr = sine_wav
    result = apply_limiter(audio, sr, target_lufs=-14.0)
    assert result.shape == audio.shape
    assert result.dtype == np.float32
```

- [ ] **Step 2: Verificar que el test falla**

```bash
pytest tests/test_limiter.py -v
```
Expected: ImportError

- [ ] **Step 3: Implementar limiter.py**

```python
# audio/limiter.py
import numpy as np
import pyloudnorm as pyln
from pedalboard import Pedalboard, Limiter

def measure_lufs(audio: np.ndarray, sample_rate: int) -> float:
    """
    Mide el LUFS integrado del audio.
    audio: (channels, samples) float32
    """
    meter = pyln.Meter(sample_rate)
    # pyloudnorm espera (samples, channels)
    loudness = meter.integrated_loudness(audio.T.astype(np.float64))
    return float(loudness)

def apply_limiter(
    audio: np.ndarray,
    sample_rate: int,
    target_lufs: float = -14.0,
) -> np.ndarray:
    """
    Normaliza el audio al LUFS objetivo y aplica un true-peak limiter a -0.3 dBTP.
    audio: (channels, samples) float32
    Retorna: (channels, samples) float32
    """
    current_lufs = measure_lufs(audio, sample_rate)

    # Normalizar con pyloudnorm (trabaja en float64, (samples, channels))
    meter = pyln.Meter(sample_rate)
    normalized = pyln.normalize.loudness(
        audio.T.astype(np.float64), current_lufs, target_lufs
    )
    normalized = normalized.T.astype(np.float32)  # volver a (channels, samples)

    # True-peak limiter a -0.3 dBTP para evitar clipping en conversión
    board = Pedalboard([Limiter(threshold_db=-0.3, release_ms=100.0)])
    limited = board(normalized, sample_rate)
    return limited
```

- [ ] **Step 4: Correr tests**

```bash
pytest tests/test_limiter.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add audio/limiter.py tests/test_limiter.py
git commit -m "feat: LUFS normalization + true-peak limiter module"
```

---

## Task 5: Auto-master module (matchering)

**Files:**
- Create: `audio/automaster.py`
- Create: `tests/test_automaster.py`

- [ ] **Step 1: Escribir el test**

```python
# tests/test_automaster.py
import os
import numpy as np
import soundfile as sf
import pytest
from audio.automaster import apply_automaster

@pytest.fixture
def two_wav_files(tmp_path):
    """Genera target y reference como archivos WAV."""
    sr = 44100
    t = np.linspace(0, 3.0, int(sr * 3.0), endpoint=False).astype(np.float32)
    target_audio = np.stack([np.sin(2 * np.pi * 440 * t) * 0.1] * 2)
    ref_audio    = np.stack([np.sin(2 * np.pi * 880 * t) * 0.2] * 2)

    target_path = str(tmp_path / "target.wav")
    ref_path    = str(tmp_path / "reference.wav")
    out_path    = str(tmp_path / "output.wav")

    sf.write(target_path, target_audio.T, sr, subtype="PCM_24")
    sf.write(ref_path,    ref_audio.T,    sr, subtype="PCM_24")
    return target_path, ref_path, out_path

def test_apply_automaster_creates_output_file(two_wav_files):
    target, reference, output = two_wav_files
    apply_automaster(target, reference, output)
    assert os.path.exists(output)
    assert os.path.getsize(output) > 0

def test_apply_automaster_output_is_valid_wav(two_wav_files):
    target, reference, output = two_wav_files
    apply_automaster(target, reference, output)
    data, sr = sf.read(output)
    assert data.ndim == 2   # estéreo
    assert sr > 0
```

- [ ] **Step 2: Verificar que el test falla**

```bash
pytest tests/test_automaster.py -v
```
Expected: ImportError

- [ ] **Step 3: Implementar automaster.py**

```python
# audio/automaster.py
import matchering as mg
import logging

# matchering es verboso — reducir a warnings
logging.getLogger("matchering").setLevel(logging.WARNING)

def apply_automaster(
    target_path: str,
    reference_path: str,
    output_path: str,
) -> None:
    """
    Aplica auto-master al target igualando el espectro y loudness de la referencia.
    Escribe el resultado a output_path como WAV 24-bit.
    """
    mg.process(
        target=target_path,
        reference=reference_path,
        results=[mg.pcm24(output_path)],
    )
```

- [ ] **Step 4: Correr tests (pueden tardar ~15-30s)**

```bash
pytest tests/test_automaster.py -v
```
Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add audio/automaster.py tests/test_automaster.py
git commit -m "feat: matchering-based auto-master module"
```

---

## Task 6: App skeleton + wizard navigation

**Files:**
- Create: `main.py`
- Create: `app.py`

- [ ] **Step 1: Crear main.py**

```python
# main.py
from app import LoudlyApp

if __name__ == "__main__":
    app = LoudlyApp()
    app.mainloop()
```

- [ ] **Step 2: Crear app.py con navegación wizard**

```python
# app.py
import customtkinter as ctk
from ui.steps.step1_load import Step1Load
from ui.steps.step2_edit import Step2Edit
from ui.steps.step3_master import Step3Master

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class LoudlyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Loudly — Masterizador")
        self.geometry("900x620")
        self.resizable(False, False)

        # Estado compartido entre pasos
        self.session: dict = {
            "audio_path": None,
            "reference_path": None,
            "audio_data": None,       # np.ndarray (channels, samples)
            "sample_rate": None,
            "processed_audio": None,  # después de EQ + limiter
            "mastered_audio": None,   # después de matchering
            "eq_params": {"low": 0.0, "low_mid": 0.0, "hi_mid": 0.0, "high": 0.0},
            "lufs_target": -14.0,
        }

        self._steps: list[ctk.CTkFrame] = []
        self._current_step = 0

        self._build_header()
        self._build_steps()
        self._show_step(0)

    def _build_header(self):
        header = ctk.CTkFrame(self, height=50, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="🎵  LOUDLY",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left", padx=20)

        self._step_labels = []
        steps_frame = ctk.CTkFrame(header, fg_color="transparent")
        steps_frame.pack(side="right", padx=20)

        for i, name in enumerate(["① Cargar", "② Ajustar", "③ Masterizar"]):
            lbl = ctk.CTkLabel(steps_frame, text=name, font=ctk.CTkFont(size=12))
            lbl.pack(side="left", padx=10)
            self._step_labels.append(lbl)

    def _build_steps(self):
        self._container = ctk.CTkFrame(self, corner_radius=0)
        self._container.pack(fill="both", expand=True)

        self._steps = [
            Step1Load(self._container, self.session, on_next=lambda: self._show_step(1)),
            Step2Edit(self._container, self.session, on_back=lambda: self._show_step(0),
                      on_next=lambda: self._show_step(2)),
            Step3Master(self._container, self.session, on_back=lambda: self._show_step(1)),
        ]
        for step in self._steps:
            step.place(relwidth=1, relheight=1)

    def _show_step(self, index: int):
        self._steps[self._current_step].place_forget()
        self._current_step = index
        self._steps[index].place(relwidth=1, relheight=1)
        self._steps[index].on_enter()
        self._update_step_labels(index)

    def _update_step_labels(self, active: int):
        for i, lbl in enumerate(self._step_labels):
            color = "#7C3AED" if i == active else "#555555"
            lbl.configure(text_color=color)
```

- [ ] **Step 3: Crear stubs de los 3 steps para que la app arranque**

```python
# ui/steps/step1_load.py
import customtkinter as ctk

class Step1Load(ctk.CTkFrame):
    def __init__(self, parent, session, on_next):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.session = session
        self.on_next = on_next
        ctk.CTkLabel(self, text="Paso 1 — Cargar (stub)").pack(pady=40)
        ctk.CTkButton(self, text="Siguiente →", command=on_next).pack()

    def on_enter(self): pass
```

```python
# ui/steps/step2_edit.py
import customtkinter as ctk

class Step2Edit(ctk.CTkFrame):
    def __init__(self, parent, session, on_back, on_next):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.session = session
        ctk.CTkLabel(self, text="Paso 2 — Editar (stub)").pack(pady=40)
        ctk.CTkButton(self, text="← Atrás", command=on_back).pack()
        ctk.CTkButton(self, text="Siguiente →", command=on_next).pack()

    def on_enter(self): pass
```

```python
# ui/steps/step3_master.py
import customtkinter as ctk

class Step3Master(ctk.CTkFrame):
    def __init__(self, parent, session, on_back):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.session = session
        ctk.CTkLabel(self, text="Paso 3 — Masterizar (stub)").pack(pady=40)
        ctk.CTkButton(self, text="← Atrás", command=on_back).pack()

    def on_enter(self): pass
```

- [ ] **Step 4: Verificar que la app abre**

```bash
python main.py
```
Expected: ventana de 900×620 con header "🎵 LOUDLY" y 3 steps navegables con los botones.

- [ ] **Step 5: Commit**

```bash
git add main.py app.py ui/steps/
git commit -m "feat: app skeleton — CTk window + wizard navigation + session state"
```

---

## Task 7: Waveform component

**Files:**
- Create: `ui/components/waveform.py`

- [ ] **Step 1: Implementar WaveformCanvas**

```python
# ui/components/waveform.py
import numpy as np
import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class WaveformCanvas(ctk.CTkFrame):
    """Muestra la forma de onda del audio como figura matplotlib embebida."""

    def __init__(self, parent, width=860, height=100, **kwargs):
        super().__init__(parent, width=width, height=height, **kwargs)
        self._fig = Figure(figsize=(width / 100, height / 100), dpi=100)
        self._fig.patch.set_facecolor("#0d0d0d")
        self._ax = self._fig.add_subplot(111)
        self._ax.set_facecolor("#0d0d0d")
        self._ax.axis("off")
        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

    def render(self, audio: np.ndarray, color: str = "#7C3AED"):
        """
        Dibuja la waveform del audio.
        audio: (channels, samples) float32
        """
        self._ax.clear()
        self._ax.set_facecolor("#0d0d0d")
        self._ax.axis("off")

        # Mezclar a mono y downsample para display
        mono = audio.mean(axis=0)
        downsample = max(1, len(mono) // 2000)
        display = mono[::downsample]

        self._ax.plot(display, color=color, linewidth=0.6, alpha=0.9)
        self._ax.fill_between(range(len(display)), display, alpha=0.3, color=color)
        self._fig.tight_layout(pad=0)
        self._canvas.draw()

    def clear(self):
        self._ax.clear()
        self._ax.set_facecolor("#0d0d0d")
        self._ax.axis("off")
        self._canvas.draw()
```

- [ ] **Step 2: Verificar manualmente**

Agregar temporalmente al stub de step2_edit.py (solo para verificar visual):
```python
from ui.components.waveform import WaveformCanvas
import numpy as np

# En __init__ de Step2Edit:
wf = WaveformCanvas(self)
wf.pack(padx=20, pady=10)
# Señal sintética para probar
fake = np.random.randn(2, 44100).astype(np.float32) * 0.1
wf.render(fake)
```

Correr `python main.py`, navegar a paso 2, verificar que aparece la waveform.

Quitar el código temporal después de verificar.

- [ ] **Step 3: Commit**

```bash
git add ui/components/waveform.py
git commit -m "feat: waveform canvas component — matplotlib embedded in CTkFrame"
```

---

## Task 8: Player component

**Files:**
- Create: `ui/components/player.py`

- [ ] **Step 1: Implementar AudioPlayer**

```python
# ui/components/player.py
import numpy as np
import sounddevice as sd
import customtkinter as ctk
import threading


class AudioPlayer(ctk.CTkFrame):
    """
    Reproductor de audio con toggle ANTES / DESPUÉS.
    Usa sounddevice OutputStream con callback para playback no bloqueante.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._before: np.ndarray | None = None  # (channels, samples)
        self._after: np.ndarray | None = None
        self._sample_rate: int = 44100
        self._stream: sd.OutputStream | None = None
        self._playing = False
        self._mode = "before"   # "before" | "after"
        self._position = 0
        self._lock = threading.Lock()

        self._build_ui()

    def _build_ui(self):
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=6)

        self._play_btn = ctk.CTkButton(
            btn_frame, text="▶ Play", width=80,
            command=self._toggle_play
        )
        self._play_btn.pack(side="left", padx=(0, 8))

        self._before_btn = ctk.CTkButton(
            btn_frame, text="ANTES", width=70,
            fg_color="#1e3a5f", hover_color="#2d5a8f",
            command=lambda: self._set_mode("before")
        )
        self._before_btn.pack(side="left", padx=2)

        self._after_btn = ctk.CTkButton(
            btn_frame, text="DESPUÉS", width=80,
            fg_color="#2d1b69", hover_color="#3d2b89",
            command=lambda: self._set_mode("after")
        )
        self._after_btn.pack(side="left", padx=2)

    def load(self, before: np.ndarray, sample_rate: int,
             after: np.ndarray | None = None):
        """Carga buffers de audio. before/after: (channels, samples) float32."""
        self.stop()
        self._before = before
        self._after = after
        self._sample_rate = sample_rate
        self._position = 0

    def set_after(self, after: np.ndarray):
        """Actualiza el buffer DESPUÉS sin detener la reproducción ANTES."""
        self._after = after

    def _current_buffer(self) -> np.ndarray | None:
        if self._mode == "after" and self._after is not None:
            return self._after
        return self._before

    def _set_mode(self, mode: str):
        self._mode = mode
        with self._lock:
            self._position = 0

    def _toggle_play(self):
        if self._playing:
            self.stop()
        else:
            self._start_playback()

    def _start_playback(self):
        buf = self._current_buffer()
        if buf is None:
            return
        self._playing = True
        self._position = 0
        self._play_btn.configure(text="⏹ Stop")

        def callback(outdata, frames, time, status):
            with self._lock:
                buf_now = self._current_buffer()
                if buf_now is None or self._position >= buf_now.shape[1]:
                    outdata[:] = 0
                    self._playing = False
                    return
                chunk = buf_now[:, self._position: self._position + frames]
                # sounddevice espera (frames, channels)
                chunk_t = chunk.T
                if chunk_t.shape[0] < frames:
                    pad = np.zeros((frames - chunk_t.shape[0], chunk_t.shape[1]),
                                   dtype=np.float32)
                    chunk_t = np.vstack([chunk_t, pad])
                    self._playing = False
                outdata[:] = chunk_t
                self._position += frames

        channels = buf.shape[0]
        self._stream = sd.OutputStream(
            samplerate=self._sample_rate,
            channels=channels,
            dtype="float32",
            blocksize=1024,
            callback=callback,
        )
        self._stream.start()

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._playing = False
        self._position = 0
        self._play_btn.configure(text="▶ Play")
```

- [ ] **Step 2: Commit**

```bash
git add ui/components/player.py
git commit -m "feat: audio player component — sounddevice stream + before/after toggle"
```

---

## Task 9: Step 1 — Cargar audio

**Files:**
- Modify: `ui/steps/step1_load.py` (reemplazar stub)

- [ ] **Step 1: Implementar step1_load.py**

```python
# ui/steps/step1_load.py
import customtkinter as ctk
from tkinter import filedialog
from audio.loader import load_audio

SUPPORTED = (
    ("Audio files", "*.wav *.mp3 *.flac *.aiff *.aif"),
    ("All files", "*.*"),
)


class Step1Load(ctk.CTkFrame):
    def __init__(self, parent, session: dict, on_next):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.session = session
        self.on_next = on_next

        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="Carga tu track para masterizar",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(40, 6))
        ctk.CTkLabel(
            self, text="Formatos: WAV · MP3 · FLAC · AIFF",
            text_color="#888888"
        ).pack(pady=(0, 20))

        # Track principal
        track_frame = ctk.CTkFrame(self, width=500, height=100, corner_radius=12)
        track_frame.pack(pady=8)
        track_frame.pack_propagate(False)

        self._track_label = ctk.CTkLabel(
            track_frame, text="📁  Sin archivo seleccionado",
            text_color="#666666", font=ctk.CTkFont(size=13)
        )
        self._track_label.pack(expand=True)
        ctk.CTkButton(
            track_frame, text="Seleccionar track principal",
            command=self._pick_track, width=220
        ).pack(pady=(0, 12))

        # Track de referencia (opcional)
        ref_frame = ctk.CTkFrame(self, width=500, height=80, corner_radius=12,
                                  border_width=1, border_color="#333333")
        ref_frame.pack(pady=8)
        ref_frame.pack_propagate(False)

        self._ref_label = ctk.CTkLabel(
            ref_frame, text="🎯  Referencia: no seleccionada  (opcional)",
            text_color="#555555", font=ctk.CTkFont(size=12)
        )
        self._ref_label.pack(expand=True)
        ctk.CTkButton(
            ref_frame, text="Seleccionar referencia",
            command=self._pick_reference, width=200,
            fg_color="#1e1e2e", hover_color="#2d2d3e"
        ).pack(pady=(0, 8))

        self._error_label = ctk.CTkLabel(self, text="", text_color="#ef4444")
        self._error_label.pack(pady=4)

        self._next_btn = ctk.CTkButton(
            self, text="Siguiente →", command=self._advance,
            state="disabled", width=140
        )
        self._next_btn.pack(pady=20)

    def _pick_track(self):
        path = filedialog.askopenfilename(filetypes=SUPPORTED)
        if not path:
            return
        try:
            audio, sr = load_audio(path)
            self.session["audio_path"] = path
            self.session["audio_data"] = audio
            self.session["sample_rate"] = sr
            self.session["processed_audio"] = audio.copy()
            name = path.split("/")[-1].split("\\")[-1]
            self._track_label.configure(
                text=f"✅  {name}  ({sr} Hz, {audio.shape[0]}ch)",
                text_color="#4ade80"
            )
            self._error_label.configure(text="")
            self._next_btn.configure(state="normal")
        except Exception as e:
            self._error_label.configure(text=f"Error: {e}")

    def _pick_reference(self):
        path = filedialog.askopenfilename(filetypes=SUPPORTED)
        if not path:
            return
        self.session["reference_path"] = path
        name = path.split("/")[-1].split("\\")[-1]
        self._ref_label.configure(
            text=f"✅  Referencia: {name}", text_color="#60a5fa"
        )

    def _advance(self):
        if self.session.get("audio_data") is not None:
            self.on_next()

    def on_enter(self):
        pass
```

- [ ] **Step 2: Verificar manualmente**

```bash
python main.py
```
- Clic en "Seleccionar track principal" → selecciona un WAV
- Label cambia a verde con nombre y sample rate
- Botón "Siguiente →" se habilita
- Clic en "Seleccionar referencia" → selecciona otro WAV
- Label de referencia cambia a azul

- [ ] **Step 3: Commit**

```bash
git add ui/steps/step1_load.py
git commit -m "feat: step 1 UI — file picker for track + reference"
```

---

## Task 10: Step 2 — EQ + Limitador + Player

**Files:**
- Modify: `ui/steps/step2_edit.py` (reemplazar stub)

- [ ] **Step 1: Implementar step2_edit.py**

```python
# ui/steps/step2_edit.py
import customtkinter as ctk
import numpy as np
import threading
from audio.eq import apply_eq
from audio.limiter import apply_limiter, measure_lufs
from ui.components.waveform import WaveformCanvas
from ui.components.player import AudioPlayer

LUFS_PRESETS = {"Spotify": -14.0, "YouTube": -13.0, "CD": -9.0}


class Step2Edit(ctk.CTkFrame):
    def __init__(self, parent, session: dict, on_back, on_next):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.session = session
        self.on_back = on_back
        self.on_next = on_next
        self._debounce_id = None
        self._build_ui()

    def _build_ui(self):
        # Waveform + player
        self._waveform = WaveformCanvas(self, height=80)
        self._waveform.pack(fill="x", padx=20, pady=(16, 4))

        self._player = AudioPlayer(self)
        self._player.pack(fill="x", padx=20)

        # EQ
        eq_frame = ctk.CTkFrame(self, corner_radius=10)
        eq_frame.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(eq_frame, text="EQ — 4 Bandas",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#7C3AED").pack(anchor="w", padx=14, pady=(8, 4))

        bands_frame = ctk.CTkFrame(eq_frame, fg_color="transparent")
        bands_frame.pack(fill="x", padx=14, pady=(0, 10))

        self._eq_sliders: dict[str, ctk.CTkSlider] = {}
        self._eq_labels: dict[str, ctk.CTkLabel] = {}

        for col, (key, label) in enumerate([
            ("low", "Low\n80 Hz"),
            ("low_mid", "Low-Mid\n250 Hz"),
            ("hi_mid", "Hi-Mid\n2.5 kHz"),
            ("high", "High\n8 kHz"),
        ]):
            f = ctk.CTkFrame(bands_frame, fg_color="transparent")
            f.grid(row=0, column=col, padx=16)
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=11),
                         text_color="#888888").pack()
            sl = ctk.CTkSlider(f, from_=-12, to=12, width=120,
                               command=lambda v, k=key: self._on_eq_change(k, v))
            sl.set(0.0)
            sl.pack(pady=4)
            val_lbl = ctk.CTkLabel(f, text="0.0 dB", font=ctk.CTkFont(size=11))
            val_lbl.pack()
            self._eq_sliders[key] = sl
            self._eq_labels[key] = val_lbl

        # Limitador
        lim_frame = ctk.CTkFrame(self, corner_radius=10)
        lim_frame.pack(fill="x", padx=20, pady=4)

        ctk.CTkLabel(lim_frame, text="Limitador",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#7C3AED").pack(anchor="w", padx=14, pady=(8, 4))

        lim_inner = ctk.CTkFrame(lim_frame, fg_color="transparent")
        lim_inner.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkLabel(lim_inner, text="Target LUFS:",
                     font=ctk.CTkFont(size=12)).pack(side="left")

        self._lufs_slider = ctk.CTkSlider(
            lim_inner, from_=-24, to=-6, width=200,
            command=self._on_lufs_change
        )
        self._lufs_slider.set(self.session.get("lufs_target", -14.0))
        self._lufs_slider.pack(side="left", padx=10)

        self._lufs_label = ctk.CTkLabel(lim_inner, text="-14.0 LUFS",
                                         font=ctk.CTkFont(size=12))
        self._lufs_label.pack(side="left")

        # Presets
        for name, val in LUFS_PRESETS.items():
            ctk.CTkButton(
                lim_inner, text=name, width=70, height=26,
                fg_color="#1e1e2e", hover_color="#2d2d3e",
                font=ctk.CTkFont(size=11),
                command=lambda v=val, n=name: self._apply_preset(v)
            ).pack(side="left", padx=4)

        self._lufs_current = ctk.CTkLabel(lim_inner, text="",
                                           text_color="#888888",
                                           font=ctk.CTkFont(size=11))
        self._lufs_current.pack(side="left", padx=10)

        # Navegación
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(nav, text="← Atrás", command=self.on_back, width=100,
                      fg_color="#2d2d3e", hover_color="#3d3d4e").pack(side="left")
        ctk.CTkButton(nav, text="Siguiente →", command=self.on_next,
                      width=140).pack(side="right")

    def on_enter(self):
        audio = self.session.get("audio_data")
        if audio is None:
            return
        self._waveform.render(audio)
        self._player.load(audio, self.session["sample_rate"],
                          self.session.get("processed_audio"))
        self._update_lufs_display()

    def _on_eq_change(self, key: str, value: float):
        self._eq_labels[key].configure(text=f"{value:+.1f} dB")
        self.session["eq_params"][key] = value
        self._schedule_reprocess()

    def _on_lufs_change(self, value: float):
        self._lufs_label.configure(text=f"{value:.1f} LUFS")
        self.session["lufs_target"] = value
        self._schedule_reprocess()

    def _apply_preset(self, value: float):
        self._lufs_slider.set(value)
        self._on_lufs_change(value)

    def _schedule_reprocess(self):
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(300, self._reprocess)

    def _reprocess(self):
        audio = self.session.get("audio_data")
        if audio is None:
            return
        eq_p = self.session["eq_params"]
        lufs_target = self.session["lufs_target"]

        def _work():
            eq_out = apply_eq(audio, self.session["sample_rate"],
                              eq_p["low"], eq_p["low_mid"],
                              eq_p["hi_mid"], eq_p["high"])
            limited = apply_limiter(eq_out, self.session["sample_rate"], lufs_target)
            self.session["processed_audio"] = limited
            self.after(0, lambda: self._player.set_after(limited))
            self.after(0, self._update_lufs_display)

        threading.Thread(target=_work, daemon=True).start()

    def _update_lufs_display(self):
        audio = self.session.get("processed_audio")
        if audio is None:
            return
        lufs = measure_lufs(audio, self.session["sample_rate"])
        self._lufs_current.configure(text=f"actual: {lufs:.1f} LUFS")
```

- [ ] **Step 2: Verificar manualmente**

```bash
python main.py
```
- Cargar un WAV en paso 1, avanzar
- Waveform visible en paso 2
- Mover slider EQ → valor actualiza en tiempo real
- Botón Play → se escucha el audio
- Toggle ANTES/DESPUÉS → diferencia audible después de cambiar EQ
- Preset "Spotify" → slider salta a -14

- [ ] **Step 3: Commit**

```bash
git add ui/steps/step2_edit.py
git commit -m "feat: step 2 UI — 4-band EQ + LUFS limiter + waveform + before/after player"
```

---

## Task 11: Step 3 — Auto-master + Exportar

**Files:**
- Modify: `ui/steps/step3_master.py` (reemplazar stub)

- [ ] **Step 1: Implementar step3_master.py**

```python
# ui/steps/step3_master.py
import customtkinter as ctk
import threading
import tempfile
import os
import numpy as np
import soundfile as sf
from tkinter import filedialog
from audio.automaster import apply_automaster
from audio.limiter import measure_lufs
from audio.loader import load_audio
from ui.components.player import AudioPlayer


class Step3Master(ctk.CTkFrame):
    def __init__(self, parent, session: dict, on_back):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.session = session
        self.on_back = on_back
        self._build_ui()

    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="both", expand=True, padx=20, pady=16)
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=1)

        # Columna izquierda: auto-master + export
        left = ctk.CTkFrame(top, corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(left, text="Auto-Master",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#7C3AED").pack(anchor="w", padx=14, pady=(12, 4))

        self._ref_info = ctk.CTkLabel(
            left, text="Sin referencia cargada",
            text_color="#888888", font=ctk.CTkFont(size=12)
        )
        self._ref_info.pack(padx=14, pady=4, anchor="w")

        self._automaster_btn = ctk.CTkButton(
            left, text="⚡ Aplicar Auto-Master",
            command=self._run_automaster, state="disabled"
        )
        self._automaster_btn.pack(padx=14, pady=8)

        self._status_label = ctk.CTkLabel(
            left, text="", font=ctk.CTkFont(size=12),
            wraplength=300
        )
        self._status_label.pack(padx=14, pady=4)

        # Exportar
        export_frame = ctk.CTkFrame(left, corner_radius=8, fg_color="#111111")
        export_frame.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(export_frame, text="Exportar",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#7C3AED").pack(anchor="w", padx=10, pady=(8, 4))

        fmt_row = ctk.CTkFrame(export_frame, fg_color="transparent")
        fmt_row.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(fmt_row, text="Formato:", font=ctk.CTkFont(size=12)).pack(side="left")
        self._fmt_var = ctk.StringVar(value="WAV 24-bit")
        ctk.CTkOptionMenu(fmt_row, values=["WAV 24-bit", "FLAC"],
                          variable=self._fmt_var, width=120).pack(side="left", padx=8)

        ctk.CTkButton(
            export_frame, text="💾 Guardar archivo",
            command=self._export, fg_color="#22c55e", hover_color="#16a34a",
            text_color="#000000"
        ).pack(padx=10, pady=(4, 12))

        # Columna derecha: análisis + player
        right = ctk.CTkFrame(top, corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ctk.CTkLabel(right, text="Análisis",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#7C3AED").pack(anchor="w", padx=14, pady=(12, 8))

        self._analysis_labels: dict[str, ctk.CTkLabel] = {}
        for key, label in [("lufs", "LUFS integrado"), ("peak", "True Peak"),
                            ("dr", "Dynamic Range")]:
            row = ctk.CTkFrame(right, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=3)
            ctk.CTkLabel(row, text=label + ":",
                         font=ctk.CTkFont(size=12),
                         text_color="#888888", width=130).pack(side="left")
            val = ctk.CTkLabel(row, text="—", font=ctk.CTkFont(size=12))
            val.pack(side="left")
            self._analysis_labels[key] = val

        self._player = AudioPlayer(right)
        self._player.pack(fill="x", padx=14, pady=16)

        # Navegación
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(nav, text="← Atrás", command=self.on_back, width=100,
                      fg_color="#2d2d3e", hover_color="#3d3d4e").pack(side="left")

    def on_enter(self):
        ref = self.session.get("reference_path")
        if ref:
            name = ref.split("/")[-1].split("\\")[-1]
            self._ref_info.configure(
                text=f"Referencia: {name}", text_color="#60a5fa"
            )
            self._automaster_btn.configure(state="normal")
        else:
            self._ref_info.configure(
                text="Sin referencia — carga una en el paso 1 para usar Auto-Master",
                text_color="#f59e0b"
            )
            self._automaster_btn.configure(state="disabled")

        processed = self.session.get("processed_audio")
        if processed is not None:
            sr = self.session["sample_rate"]
            self._player.load(
                before=self.session["audio_data"],
                sample_rate=sr,
                after=self.session.get("mastered_audio"),
            )
            self._update_analysis(processed, sr)

    def _run_automaster(self):
        self._automaster_btn.configure(state="disabled",
                                        text="⏳ Procesando…")
        self._status_label.configure(text="Aplicando matchering, puede tardar unos segundos…",
                                      text_color="#888888")

        def _work():
            try:
                processed = self.session["processed_audio"]
                sr = self.session["sample_rate"]
                ref_path = self.session["reference_path"]

                # Escribir processed a temp WAV
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_in = f.name
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_out = f.name

                sf.write(tmp_in, processed.T, sr, subtype="PCM_24")
                apply_automaster(tmp_in, ref_path, tmp_out)

                mastered, _ = load_audio(tmp_out)
                self.session["mastered_audio"] = mastered
                os.unlink(tmp_in)
                os.unlink(tmp_out)

                self.after(0, lambda: self._on_automaster_done(mastered, sr))
            except Exception as e:
                self.after(0, lambda: self._on_automaster_error(str(e)))

        threading.Thread(target=_work, daemon=True).start()

    def _on_automaster_done(self, mastered: np.ndarray, sr: int):
        self._automaster_btn.configure(state="normal", text="⚡ Aplicar Auto-Master")
        self._status_label.configure(text="✅ Auto-master aplicado", text_color="#4ade80")
        self._player.set_after(mastered)
        self._update_analysis(mastered, sr)

    def _on_automaster_error(self, error: str):
        self._automaster_btn.configure(state="normal", text="⚡ Aplicar Auto-Master")
        self._status_label.configure(text=f"Error: {error}", text_color="#ef4444")

    def _update_analysis(self, audio: np.ndarray, sr: int):
        lufs = measure_lufs(audio, sr)
        peak = float(np.max(np.abs(audio)))
        peak_db = 20 * np.log10(peak) if peak > 0 else -np.inf
        dr = float(audio.std())

        self._analysis_labels["lufs"].configure(
            text=f"{lufs:.1f} LUFS", text_color="#4ade80")
        self._analysis_labels["peak"].configure(
            text=f"{peak_db:.1f} dBTP",
            text_color="#4ade80" if peak_db < -0.1 else "#ef4444")
        self._analysis_labels["dr"].configure(
            text=f"{dr * 100:.1f} DR", text_color="#aaaaaa")

    def _export(self):
        audio = self.session.get("mastered_audio") or self.session.get("processed_audio")
        if audio is None:
            return
        sr = self.session["sample_rate"]
        fmt = self._fmt_var.get()

        ext = ".wav" if "WAV" in fmt else ".flac"
        path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[("WAV", "*.wav"), ("FLAC", "*.flac")] if ext == ".wav"
                      else [("FLAC", "*.flac"), ("WAV", "*.wav")],
            initialfile="mastered" + ext,
        )
        if not path:
            return

        subtype = "PCM_24" if "WAV" in fmt else None
        sf.write(path, audio.T, sr, subtype=subtype)
        self._status_label.configure(
            text=f"💾 Guardado: {path.split('/')[-1].split(chr(92))[-1]}",
            text_color="#4ade80"
        )
```

- [ ] **Step 2: Verificar manualmente**

```bash
python main.py
```
- Flujo completo: cargar track + referencia → ajustar EQ/LUFS → paso 3
- Panel de análisis muestra LUFS del processed_audio
- Clic "Auto-Master" → indicador de progreso → "✅ Auto-master aplicado"
- Toggle ANTES/DESPUÉS en el player — diferencia audible
- Exportar → archivo guardado correctamente

- [ ] **Step 3: Commit**

```bash
git add ui/steps/step3_master.py
git commit -m "feat: step 3 UI — auto-master (matchering) + analysis panel + export"
```

---

## Task 12: PyInstaller build

**Files:**
- Create: `loudly.spec`

- [ ] **Step 1: Crear loudly.spec**

```python
# loudly.spec
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
import sys

block_cipher = None

# matchering necesita sus archivos de datos
datas = []
datas += collect_data_files("matchering")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=collect_dynamic_libs("sounddevice"),
    datas=datas,
    hiddenimports=[
        "customtkinter",
        "pedalboard",
        "matchering",
        "pyloudnorm",
        "sounddevice",
        "soundfile",
        "matplotlib",
        "matplotlib.backends.backend_tkagg",
        "pydub",
        "scipy",
        "scipy.signal",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="Loudly",
    debug=False,
    console=False,          # sin ventana de consola
    icon=None,              # agregar .ico aquí si tienes uno
    onefile=True,
)
```

- [ ] **Step 2: Compilar**

```bash
pyinstaller loudly.spec --clean
```
Expected: `dist/Loudly.exe` generado (~100–200 MB es normal)

- [ ] **Step 3: Probar el .exe**

Doble clic en `dist/Loudly.exe` — debe abrir la app sin errores y sin Python instalado.
Repetir el flujo completo: cargar → ajustar → auto-master → exportar.

- [ ] **Step 4: Commit final**

```bash
git add loudly.spec
git commit -m "chore: PyInstaller spec — compila a Loudly.exe standalone"
```

---

## Verification checklist

- [ ] `pytest tests/ -v` → todos los tests pasan
- [ ] `python main.py` → flujo completo sin errores de consola
- [ ] EQ slider → audio cambia al presionar DESPUÉS
- [ ] Preset Spotify → slider salta a -14, audio se normaliza
- [ ] Auto-master (con referencia) → completa y muestra LUFS
- [ ] Exportar WAV → archivo abrable en cualquier reproductor
- [ ] `pyinstaller loudly.spec` → `dist/Loudly.exe` corre sin Python
