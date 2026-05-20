# Arquitectura — Loudly

## Estructura de módulos

### `app.py` — LoudlyApp

Ventana principal (CTk). Instancia los tres pasos y gestiona la navegación entre ellos. El estado compartido vive en `self.session`, un diccionario pasado por referencia a cada paso:

```python
session = {
    "audio_path":      str | None,         # ruta al track original
    "reference_path":  str | None,         # ruta al track de referencia (opcional)
    "audio_data":      np.ndarray | None,  # audio original (channels, samples) float32
    "sample_rate":     int | None,
    "processed_audio": np.ndarray | None,  # después de EQ + limiter
    "mastered_audio":  np.ndarray | None,  # después de matchering
    "eq_params":       dict,               # {"low", "low_mid", "hi_mid", "high"} en dB
    "lufs_target":     float,              # objetivo LUFS para el limitador
}
```

Al entrar a cada paso se llama `on_enter()` para que el paso lea el estado actualizado.

---

## Módulos de audio

| Módulo | Función principal | Notas |
|--------|-------------------|-------|
| `loader.py` | `load_audio(path)` | MP3 via miniaudio (soundfile no soporta MP3 con Python 3.13). El resto via soundfile. |
| `eq.py` | `apply_eq(audio, sr, ...)` | Shelf a 80 Hz y 8 kHz; peaks a 250 Hz y 2.5 kHz. Retorna el mismo array sin modificar si todos los gains son 0. |
| `limiter.py` | `apply_limiter(audio, sr, target)` | Normaliza al LUFS objetivo con pyloudnorm; luego `np.clip` a −0.3 dBFS. Usa clip (no Pedalboard Limiter) porque clip solo atenúa, nunca añade ganancia. |
| `automaster.py` | `apply_automaster(target, ref, out)` | Wrapper de `matchering.process()`. Opera sobre archivos WAV en disco. |

---

## Convención de datos

Todos los arrays internos son `np.ndarray` de forma `(channels, samples)` en `float32`.

Las bibliotecas externas usan convenciones distintas; las transposiciones ocurren en los puntos de integración:

| Biblioteca | Convención | Punto de transposición |
|------------|-----------|------------------------|
| soundfile  | `(samples, channels)` | `loader.py`, `step3_master.py._export()` |
| pyloudnorm | `(samples, channels)` float64 | `limiter.py` |
| sounddevice callback | `(frames, channels)` | `player.py` callback |

---

## Flujo de datos

```
Archivo de audio
      │
      ▼  load_audio()
 audio_data  ─────────────────────────────────────────────┐
      │                                                     │
      │  Paso 2                                             │
      ▼                                                     │
 apply_eq()  ──►  apply_limiter()  ──►  processed_audio   │  (buffer ANTES del player)
                                              │
                                              │  Paso 3 (opcional)
                                              ▼
                              WAV temporal ──► matchering.process() ──► mastered_audio
```

La exportación prioriza `mastered_audio`; si no existe, usa `processed_audio`.

---

## Modelo de hilos

La UI corre en el hilo principal de Tkinter. El audio pesado se delega a hilos daemon:

### Step2Edit — debounce + generación

Los sliders pueden disparar decenas de eventos por segundo. `_schedule_reprocess()` cancela el timer previo y reprograma con 300 ms de delay (debounce).

Cada reprocess incrementa `_process_gen`. El hilo compara su generación con la actual antes de actualizar el session y la UI; si difieren, descarta el resultado (previene condiciones de carrera cuando el usuario mueve un slider mientras el hilo anterior aún procesa).

```
slider event ──► _schedule_reprocess() ──► [300ms debounce] ──► _reprocess()
                                                                       │
                                                            gen = ++_process_gen
                                                                       │
                                                            hilo daemon ──► apply_eq + apply_limiter
                                                                                  │
                                                                         if gen == _process_gen:
                                                                             actualizar UI
```

### Step3Master — hilo único

`_run_automaster()` deshabilita el botón antes de lanzar el hilo. Esto garantiza que solo corra un proceso de matchering a la vez sin necesidad de locks adicionales.

### Comunicación hilo → UI

Siempre vía `widget.after(0, callback)`. Nunca se llama directamente a métodos CTk desde un hilo secundario.

---

## Auto-Master (matchering)

matchering no opera en memoria: requiere archivos WAV en disco. El flujo en `_run_automaster()`:

1. `sf.write(tmp_in, processed.T, sr, subtype="PCM_24")` — vuelca `processed_audio` a WAV temporal
2. `apply_automaster(tmp_in, ref_path, tmp_out)` — matchering lee ambos y escribe el resultado
3. `load_audio(tmp_out)` — recarga el resultado como ndarray
4. `os.unlink(tmp_in)`, `os.unlink(tmp_out)` — limpia los temporales

El track de referencia puede ser cualquier formato soportado porque matchering lo decodifica internamente.

---

## BatchWindow

`ui/batch_window.py` implementa procesamiento batch como ventana independiente (`CTkToplevel`) lanzada desde Step 1.

### Estructuras de datos

```python
@dataclass
class BatchItem:
    path: str
    status: Literal["pending", "processing", "done", "error"] = "pending"
    message: str = ""
```

`_remastered_path(source_path)` deriva la ruta de salida: reemplaza la extensión original con `_remastered.wav` en la misma carpeta.

### Modelo de hilos

Un único hilo daemon (`_process_all`) procesa los items secuencialmente. El flag `_cancel` se activa al cerrar la ventana (`WM_DELETE_WINDOW`) para abortar los items pendientes; los items ya completados conservan su archivo exportado.

```
_start_batch()
    │
    └── hilo daemon: _process_all()
            │
            ├── por cada BatchItem (status == "pending"):
            │       if _cancel: break
            │       load_audio(item.path)
            │       WAV temporal → apply_automaster() → WAV temporal
            │       load_audio(resultado) → sf.write(_remastered.wav)
            │       _safe_after(0, actualizar UI)
            │       limpiar temporales
            │
            └── _on_batch_done() — re-habilita botón, muestra resumen
```

La comunicación con la UI usa `_safe_after()` (wrapper de `widget.after(0, cb)` con guard `winfo_exists()`) para tolerar el caso en que la ventana se cierra mientras el hilo aún procesa.

### Habilitación del botón

`_refresh_process_btn()` habilita "⚡ Procesar todos" solo cuando hay al menos un item `pending`, hay referencia cargada, y no hay hilo activo. Se llama tras cada `_add_tracks` y `_pick_reference`, y al finalizar el batch.

---

## Compilación con PyInstaller

`loudly.spec` empaqueta todo en un único `.exe` standalone. Los hooks de PyInstaller para numpy, soundfile y matchering se incluyen implícitamente. El binario resultante en `dist\Loudly.exe` no requiere Python instalado.
