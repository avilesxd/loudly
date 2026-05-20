# Guía de uso — Loudly

## Paso 1: Cargar track

1. Haz clic en **Seleccionar track principal** y elige tu archivo de audio (WAV, MP3, FLAC o AIFF).
2. *(Opcional)* Haz clic en **Seleccionar referencia** para cargar un track de referencia. En el paso 3, Loudly igualará el EQ, loudness y dinámica de tu track al de esa referencia.
3. Haz clic en **Siguiente →**.

> **Consejo:** la referencia ideal es una canción comercial del mismo género, bien masterizada, que represente el sonido que buscas.

---

## Paso 2: Ajustar EQ y loudness

### EQ — 4 Bandas

Cada slider va de **−12 dB** a **+12 dB**. El audio se reprocesa automáticamente 300 ms después de soltar el control.

| Control | Frecuencia | Tipo de filtro | Casos de uso comunes |
|---------|-----------|----------------|----------------------|
| Low | 80 Hz | Shelf | Controla el peso del bajo. Baja si hay boominess o exceso de ruido de sala. |
| Low-Mid | 250 Hz | Peak | Zona de calor o barro. Baja para limpiar mezclas densas o con mucho cuerpo. |
| Hi-Mid | 2.5 kHz | Peak | Presencia y ataque. Sube para que el vocal o guitarra se destaquen en la mezcla. |
| High | 8 kHz | Shelf | Aire y brillo. Sube con cuidado para no añadir harshness o saturación alta. |

### Limitador — Target LUFS

Ajusta el slider de **Target LUFS** o usa uno de los presets rápidos:

| Preset | Valor | Plataforma objetivo |
|--------|-------|---------------------|
| Spotify | −14 LUFS | Streaming estándar |
| YouTube | −13 LUFS | YouTube Music, videos |
| CD | −9 LUFS | Máster físico / descarga |

El medidor **actual: X LUFS** muestra el loudness del audio ya procesado.

### Reproductor ANTES / DESPUÉS

- **▶ Play** — inicia la reproducción desde el principio.
- **ANTES** — reproduce el audio original sin procesar.
- **DESPUÉS** — reproduce el audio con EQ y limitador aplicados.

Puedes cambiar entre ANTES y DESPUÉS mientras el audio está reproduciéndose.

---

## Paso 3: Masterizar y exportar

### Auto-Master (requiere referencia del paso 1)

Si cargaste una referencia, el botón **⚡ Aplicar Auto-Master** estará disponible.

Al presionarlo, Loudly analiza la referencia y ajusta automáticamente el espectro, loudness y dinámica de tu track para que coincidan. El proceso puede tardar entre 5 y 30 segundos dependiendo de la duración del track.

> **Nota:** el Auto-Master opera sobre el audio ya procesado del paso 2. Si ajustaste el EQ o el LUFS, esos cambios se aplican primero.

### Panel de análisis

Compara las métricas **ANTES** (audio con EQ/limiter del paso 2) y **DESPUÉS** (tras Auto-Master):

| Métrica | Qué mide |
|---------|----------|
| LUFS | Loudness integrado (percibido). |
| True Peak | Pico máximo en dBTP. Aparece en rojo si supera −0.1 dBTP, lo que puede causar clipping en la conversión a formatos lossy. |
| Dinámica | Desviación estándar del audio; indicador aproximado de rango dinámico. |

### Exportar

1. Elige el formato en el menú desplegable:
   - **WAV 24-bit** — máxima calidad, sin pérdida, tamaño mayor.
   - **FLAC** — sin pérdida, comprimido (~50-60% del tamaño del WAV).
2. Haz clic en **💾 Guardar archivo** y elige la ubicación.

> Si no aplicaste Auto-Master, se exporta el audio del paso 2 (EQ + limitador).

---

---

## Procesamiento batch (múltiples tracks)

El modo batch permite auto-masterizar varios tracks contra una misma referencia sin pasar por el wizard principal.

### Abrir la ventana batch

En el **Paso 1**, hacé clic en **Procesar múltiples tracks (batch)**.

### Flujo de trabajo

1. Hacé clic en **Elegir** y seleccioná el track de referencia (WAV, MP3, FLAC o AIFF).
2. Hacé clic en **+ Agregar tracks** y seleccioná uno o varios archivos a procesar (podés seleccionar varios a la vez). Los duplicados se ignoran automáticamente.
3. Cuando haya al menos un track y una referencia cargados, el botón **⚡ Procesar todos** se habilita.
4. Hacé clic en **⚡ Procesar todos** — cada track se procesa de forma secuencial. El estado de cada fila se actualiza en tiempo real:

   | Estado | Significado |
   |--------|-------------|
   | ⏳ en cola | Esperando procesamiento |
   | ⚙️ procesando… | matchering en curso |
   | ✅ listo | Exportado con éxito |
   | ❌ mensaje | Error — el detalle aparece en la fila |

5. El archivo exportado se guarda en la misma carpeta que el original con el sufijo `_remastered.wav`. Por ejemplo: `mi_cancion.mp3` → `mi_cancion_remastered.wav`.

> **Nota:** el batch aplica únicamente Auto-Master (matchering). No incluye el EQ ni el limitador del wizard principal.

> **Nota:** si el sample rate del track no coincide con el de la referencia, ese item falla pero el resto continúa procesándose.

Cerrar la ventana durante el procesamiento cancela los items pendientes; los que ya finalizaron conservan su archivo exportado.

---

## Flujos de trabajo comunes

### Normalización rápida a streaming

1. Carga tu track → Siguiente.
2. Paso 2: ajusta el LUFS al preset **Spotify** (−14).
3. Paso 3: exporta en WAV 24-bit.

### Masterización con referencia

1. Carga tu track + una canción de referencia → Siguiente.
2. Paso 2: haz ajustes opcionales de EQ si la mezcla necesita corrección.
3. Paso 3: aplica **Auto-Master** y compara el análisis → exporta.

### Solo corrección de EQ (sin cambiar loudness)

1. Carga tu track → Siguiente.
2. Paso 2: ajusta las bandas de EQ; deja el LUFS en el valor deseado.
3. Paso 3: exporta directamente sin usar Auto-Master.
