import threading

import customtkinter as ctk
import numpy as np
import sounddevice as sd


class AudioPlayer(ctk.CTkFrame):
    """
    Reproductor de audio con toggle ANTES / DESPUÉS.

    Mantiene dos buffers en memoria (before y after) y reproduce el activo
    según el modo seleccionado. Usa un OutputStream de sounddevice con callback
    para reproducción no bloqueante; el hilo de audio y el hilo de UI pueden
    acceder al buffer simultáneamente, por lo que se protege el cursor de
    posición y el buffer activo con un threading.Lock.

    El buffer ANTES es obligatorio (se carga con load()); el buffer DESPUÉS
    es opcional y puede actualizarse en cualquier momento con set_after()
    sin interrumpir la reproducción del buffer ANTES.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._before: np.ndarray | None = None  # (channels, samples)
        self._after: np.ndarray | None = None
        self._sample_rate: int = 44100
        self._stream: sd.OutputStream | None = None
        self._playing = False
        self._mode = "before"  # "before" | "after"
        self._position = 0
        self._lock = threading.Lock()

        self._build_ui()

    def _build_ui(self):
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=6)

        self._play_btn = ctk.CTkButton(
            btn_frame, text="▶ Play", width=80, command=self._toggle_play
        )
        self._play_btn.pack(side="left", padx=(0, 8))

        self._before_btn = ctk.CTkButton(
            btn_frame,
            text="Original",
            width=75,
            fg_color="#1e3a5f",
            hover_color="#2d5a8f",
            command=lambda: self._set_mode("before"),
        )
        self._before_btn.pack(side="left", padx=2)

        self._after_btn = ctk.CTkButton(
            btn_frame,
            text="Procesado",
            width=90,
            fg_color="#2d1b69",
            hover_color="#3d2b89",
            state="disabled",
            command=lambda: self._set_mode("after"),
        )
        self._after_btn.pack(side="left", padx=2)

        self._update_mode_buttons()

    def load(
        self, before: np.ndarray, sample_rate: int, after: np.ndarray | None = None
    ):
        """Load audio buffers. before/after: (channels, samples) float32."""
        self.stop()
        self._before = before
        self._after = after
        self._sample_rate = sample_rate
        self._position = 0
        if after is not None:
            self._after_btn.configure(state="normal")
        else:
            self._after_btn.configure(state="disabled")
            if self._mode == "after":
                self._mode = "before"
                self._update_mode_buttons()

    def set_after(self, after: np.ndarray):
        """Update AFTER buffer without stopping BEFORE playback."""
        self._after = after
        self._after_btn.configure(state="normal")

    def _current_buffer(self) -> np.ndarray | None:
        if self._mode == "after" and self._after is not None:
            return self._after
        return self._before

    def _set_mode(self, mode: str):
        """
        Cambia entre los buffers ANTES y DESPUÉS.

        Si el audio está reproduciéndose, lo detiene, cambia el modo y reanuda
        desde el principio del nuevo buffer. Ignora el cambio a "after" si no
        hay buffer DESPUÉS cargado aún (evita reproducir silencio o crashear).
        """
        if mode == "after" and self._after is None:
            return
        was_playing = self._playing
        if was_playing:
            self.stop()
        self._mode = mode
        self._update_mode_buttons()
        if was_playing:
            self._start_playback()

    def _update_mode_buttons(self):
        before_active = self._mode == "before"
        self._before_btn.configure(
            fg_color="#1e6a9f" if before_active else "#1e3a5f",
        )
        self._after_btn.configure(
            fg_color="#5b1b9f" if not before_active else "#2d1b69",
        )

    def _toggle_play(self):
        if self._playing:
            self.stop()
        else:
            self._start_playback()

    def _start_playback(self):
        """
        Abre un OutputStream de sounddevice y comienza la reproducción
        mediante callback.

        El callback se ejecuta en el hilo de audio de sounddevice (no en el hilo UI).
        Lee chunks del buffer activo usando _position como cursor. Cuando se llega
        al final, rellena outdata con ceros y marca _playing = False para indicar
        que terminó. El lock protege _position y la lectura del buffer activo porque
        _set_mode() puede cambiar el buffer desde el hilo UI mientras el callback corre.
        """
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
                chunk = buf_now[:, self._position : self._position + frames]
                # sounddevice expects (frames, channels)
                chunk_t = chunk.T
                if chunk_t.shape[0] < frames:
                    pad = np.zeros(
                        (frames - chunk_t.shape[0], chunk_t.shape[1]), dtype=np.float32
                    )
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
