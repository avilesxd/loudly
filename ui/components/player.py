import numpy as np
import sounddevice as sd
import customtkinter as ctk
import threading


class AudioPlayer(ctk.CTkFrame):
    """
    Audio player with BEFORE / AFTER toggle.
    Uses sounddevice OutputStream with callback for non-blocking playback.
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
            text="ANTES",
            width=70,
            fg_color="#1e3a5f",
            hover_color="#2d5a8f",
            command=lambda: self._set_mode("before"),
        )
        self._before_btn.pack(side="left", padx=2)

        self._after_btn = ctk.CTkButton(
            btn_frame,
            text="DESPUÉS",
            width=80,
            fg_color="#2d1b69",
            hover_color="#3d2b89",
            command=lambda: self._set_mode("after"),
        )
        self._after_btn.pack(side="left", padx=2)

    def load(
        self, before: np.ndarray, sample_rate: int, after: np.ndarray | None = None
    ):
        """Load audio buffers. before/after: (channels, samples) float32."""
        self.stop()
        self._before = before
        self._after = after
        self._sample_rate = sample_rate
        self._position = 0

    def set_after(self, after: np.ndarray):
        """Update AFTER buffer without stopping BEFORE playback."""
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
