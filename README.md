# Loudly — Masterizador de Audio

Aplicación de escritorio para masterizar temas musicales. Wizard de 3 pasos: carga tu track, ajusta EQ y loudness, y aplica auto-masterización por referencia.

## Características

- **EQ de 4 bandas** — Low (80 Hz), Low-Mid (250 Hz), Hi-Mid (2.5 kHz), High (8 kHz)
- **Limitador con control LUFS** — normaliza a estándares de streaming (Spotify −14, YouTube −13, CD −9)
- **Auto-Master por referencia** — iguala automáticamente el EQ, loudness y dinámica de un track de referencia usando [matchering](https://github.com/sergree/matchering)
- **Reproductor con toggle Antes/Después** — escucha la diferencia en tiempo real
- **Análisis comparativo** — muestra LUFS, True Peak y Dinámica antes y después del procesado
- **Exporta a WAV 24-bit o FLAC**

## Formatos soportados

| Entrada | Salida |
|---------|--------|
| WAV, MP3, FLAC, AIFF | WAV 24-bit, FLAC |

## Instalación (desarrollo)

Requiere Python 3.13.

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Uso

```bash
.venv\Scripts\python main.py
```

## Compilar a .exe

```bash
.venv\Scripts\pyinstaller loudly.spec --clean
```

El ejecutable queda en `dist\Loudly.exe`. Es standalone — no requiere Python instalado.

## Tests

```bash
.venv\Scripts\pytest tests/ -v
```

## Arquitectura

```
loudly/
├── main.py              # Punto de entrada
├── app.py               # LoudlyApp — ventana principal, sesión compartida
├── audio/
│   ├── loader.py        # Carga WAV/MP3/FLAC/AIFF → (channels, samples) float32
│   ├── eq.py            # EQ de 4 bandas con pedalboard
│   ├── limiter.py       # Normalización LUFS + true-peak limiter
│   └── automaster.py    # Auto-masterización con matchering
└── ui/
    ├── steps/
    │   ├── step1_load.py    # Paso 1: carga de archivos
    │   ├── step2_edit.py    # Paso 2: EQ + limiter interactivos
    │   └── step3_master.py  # Paso 3: auto-master + análisis + exportar
    └── components/
        ├── player.py        # Reproductor ANTES/DESPUÉS
        └── waveform.py      # Visualización de forma de onda
```

El estado de la sesión se mantiene en un diccionario `session` en `LoudlyApp` y se comparte por referencia con los tres pasos. Las operaciones de audio se ejecutan en hilos daemon para no bloquear la UI.

### Convención de datos de audio

Todos los arrays internos son `(channels, samples)` en `float32`. Las bibliotecas externas (soundfile, pyloudnorm) usan `(samples, channels)` y se transponen en los puntos de integración.

### Modelo de hilos

- **Step2Edit**: un hilo por reprocess; un contador de generación descarta resultados obsoletos si llegan tras un ajuste posterior.
- **Step3Master**: un hilo único para matchering; el botón se deshabilita mientras procesa.
- Comunicación de vuelta al hilo UI vía `widget.after(0, callback)`.

## Stack

- **UI**: CustomTkinter
- **EQ / Limiter**: [pedalboard](https://github.com/spotify/pedalboard) (Spotify)
- **Auto-Master**: [matchering](https://github.com/sergree/matchering)
- **LUFS**: pyloudnorm
- **Playback**: sounddevice
- **Waveform**: matplotlib (backend TkAgg)
- **MP3**: miniaudio (compatible con Python 3.13)
- **Build**: PyInstaller

## Documentación adicional

- [Guía de usuario](docs/user-guide.md) — cómo usar la aplicación paso a paso
- [Arquitectura](docs/architecture.md) — detalles técnicos del diseño
