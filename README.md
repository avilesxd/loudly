# Loudly — Masterizador de Audio

Aplicación de escritorio para masterizar temas musicales. Wizard de 3 pasos: carga tu track, ajusta EQ y loudness, y aplica auto-masterización por referencia.

## Características

- **EQ de 4 bandas** — Low (80 Hz), Low-Mid (250 Hz), Hi-Mid (2.5 kHz), High (8 kHz)
- **Limitador con control LUFS** — normaliza a estándares de streaming (Spotify −14, YouTube −13, CD −9)
- **Auto-Master por referencia** — iguala automáticamente el EQ, loudness y dinámica de un track de referencia usando [matchering](https://github.com/sergree/matchering)
- **Reproductor con toggle Antes/Después** — escucha la diferencia en tiempo real
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

## Stack

- **UI**: CustomTkinter
- **EQ / Limiter**: [pedalboard](https://github.com/spotify/pedalboard) (Spotify)
- **Auto-Master**: [matchering](https://github.com/sergree/matchering)
- **LUFS**: pyloudnorm
- **Playback**: sounddevice
- **Build**: PyInstaller
