# Loudly — Masterizador de Audio Desktop

**Fecha:** 2026-05-18  
**Estado:** Aprobado

---

## Contexto

El usuario necesita una herramienta de escritorio para masterizar temas musicales. El objetivo es tener un `.exe` distribuible que no requiera que el usuario instale Python, con una interfaz guiada (wizard) que permita aplicar EQ, limitador con control de LUFS, y auto-masterización basada en referencia usando `matchering`.

---

## Decisiones de diseño

| Decisión | Elección | Razón |
|---|---|---|
| Plataforma | Desktop (Windows .exe) | Sin dependencia de internet, archivos grandes, privacidad |
| UI framework | CustomTkinter | Dark theme nativo, moderno, compatible con PyInstaller |
| EQ + Limiter | pedalboard (Spotify) | Calidad profesional, Python nativo |
| Auto-master | matchering | Open-source, referencia-based, resultados profesionales |
| LUFS | pyloudnorm | Estándar de la industria, liviano |
| Playback | sounddevice + soundfile | Sin dependencias pesadas |
| Waveform | matplotlib embebido | Visualización estática de onda |
| Distribución | PyInstaller | Genera .exe standalone |

---

## Funcionalidades

### 1. Cargar audio (Paso 1)
- Drag & drop o file picker para el track principal
- Formatos soportados: WAV, MP3, FLAC, AIFF
- Campo opcional para cargar track de referencia (para auto-master)
- El botón "Siguiente" se habilita solo cuando hay un track cargado

### 2. EQ + Limitador (Paso 2)
- **EQ de 4 bandas**: Low (80 Hz), Low-Mid (250 Hz), Hi-Mid (2.5 kHz), High (8 kHz) — ±12 dB por banda
- **Limitador**: slider de target LUFS con presets (Spotify −14, YouTube −13, CD −9)
- **Waveform** del track cargado (estática, renderizada con matplotlib)
- **Reproductor** con botón toggle ANTES / DESPUÉS — escucha el efecto en tiempo real
- El procesamiento se aplica en tiempo real al cambiar los controles (debounced 300ms)

### 3. Auto-Master + Exportar (Paso 3)
- Botón **"Aplicar Auto-Master"** — llama a `matchering` con el track y la referencia
- Si no se cargó referencia en el paso 1, el botón muestra un aviso y no está disponible
- Panel de **análisis final**: LUFS integrado, True Peak, Dynamic Range
- Toggle **ANTES / DESPUÉS**: ANTES = audio original sin procesar, DESPUÉS = resultado de matchering aplicado encima de EQ+limiter del paso 2
- Exportar a **WAV 24-bit** o **FLAC** con selector de carpeta destino

---

## Arquitectura

```
loudly/
├── main.py                  # Entry point — arranca la app
├── app.py                   # CTk window principal + navegación wizard
├── ui/
│   ├── steps/
│   │   ├── step1_load.py    # Pantalla de carga de archivos
│   │   ├── step2_edit.py    # EQ + Limitador + player
│   │   └── step3_master.py  # Auto-master + exportar
│   └── components/
│       ├── waveform.py      # Widget matplotlib embebido
│       └── player.py        # Controles play/pause + toggle antes/después
├── audio/
│   ├── eq.py                # EQ 4 bandas via pedalboard
│   ├── limiter.py           # Limiter + LUFS target via pedalboard + pyloudnorm
│   └── automaster.py        # Wrapper de matchering
├── requirements.txt
└── loudly.spec              # Config PyInstaller
```

### Flujo de datos entre pasos

```
step1 → guarda: audio_path, reference_path
step2 → lee: audio_path | guarda: eq_params, lufs_target, processed_audio
step3 → lee: processed_audio, reference_path | guarda: mastered_audio
```

El estado entre pasos se pasa como un diccionario `session` que vive en `app.py` y se inyecta a cada step.

---

## Stack de dependencias

```
customtkinter>=5.2
pedalboard>=0.9
matchering>=2.0
pyloudnorm>=0.1
sounddevice>=0.4
soundfile>=0.12
numpy>=1.24
matplotlib>=3.7
pydub>=0.25          # conversión MP3/AIFF → WAV para procesamiento interno
pyinstaller>=6.0
```

---

## Comportamiento del reproductor (antes/después)

- El audio se decodifica a float32 numpy array en memoria al cargarlo
- El reproductor usa `sounddevice.OutputStream` con un callback que lee el buffer
- Toggle ANTES: reproduce el array original
- Toggle DESPUÉS: reproduce el array procesado (EQ + limiter aplicados)
- Al cambiar un control en el paso 2, se re-procesa el audio en un thread separado (debounce 300ms) y se actualiza el buffer DESPUÉS

---

## Verificación (cómo probar)

1. `pip install -r requirements.txt && python main.py` — app abre sin errores
2. Cargar un WAV en paso 1, avanzar a paso 2 — waveform visible, play funciona
3. Mover slider de EQ, presionar play DESPUÉS — se escucha el cambio
4. En paso 3: cargar referencia en paso 1, volver, aplicar auto-master — debe completar sin error y mostrar LUFS
5. Exportar WAV — archivo guardado es reproducible y tiene el LUFS objetivo
6. `pyinstaller loudly.spec` — genera `dist/loudly.exe` que corre en Windows sin Python instalado
