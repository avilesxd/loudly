import customtkinter as ctk
import numpy as np
import threading
from audio.eq import apply_eq
from audio.limiter import apply_limiter, measure_lufs
from ui.components.waveform import WaveformCanvas
from ui.components.player import AudioPlayer

LUFS_PRESETS = {"Spotify": -14.0, "YouTube": -13.0, "CD": -9.0}


class Step2Edit(ctk.CTkFrame):
    """
    Paso 2 del wizard: EQ de 4 bandas y normalización LUFS con preview en tiempo real.

    Cada vez que el usuario mueve un slider, se programa un reprocess con 300 ms
    de debounce (_schedule_reprocess). El reprocess ejecuta apply_eq + apply_limiter
    en un hilo daemon y actualiza session["processed_audio"] con el resultado.

    Para evitar condiciones de carrera cuando el usuario sigue ajustando mientras
    el hilo anterior aún procesa, se usa un contador de generación (_process_gen).
    El hilo toma una snapshot de su número de generación al arrancar, y descarta
    el resultado si el contador ya avanzó (es decir, llegó un reprocess más reciente).
    """

    def __init__(self, parent, session: dict, on_back, on_next):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.session = session
        self.on_back = on_back
        self.on_next = on_next
        self._debounce_id = None
        self._process_gen = 0
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

        # Limiter
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
                command=lambda v=val: self._apply_preset(v)
            ).pack(side="left", padx=4)

        self._lufs_current = ctk.CTkLabel(lim_inner, text="",
                                           text_color="#888888",
                                           font=ctk.CTkFont(size=11))
        self._lufs_current.pack(side="left", padx=10)

        # Navigation
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(nav, text="← Atrás", command=self.on_back, width=100,
                      fg_color="#2d2d3e", hover_color="#3d3d4e").pack(side="left")
        ctk.CTkButton(nav, text="Siguiente →", command=self.on_next,
                      width=140).pack(side="right")

    def on_enter(self):
        """
        Se llama al navegar hacia este paso (desde el paso 1 o al volver del paso 3).

        Renderiza siempre la waveform del audio original (no del procesado), y carga
        el reproductor con el estado actual del session — el processed_audio puede
        haber sido generado en una visita anterior al paso 2, por lo que se muestra
        como buffer DESPUÉS si existe.
        """
        audio = self.session.get("audio_data")
        if audio is None:
            return
        self._waveform.render(audio)
        self._player.load(audio, self.session["sample_rate"],
                          self.session.get("processed_audio"))
        self._lufs_current.configure(text="", text_color="#888888")
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
        """
        Cancela el timer anterior y programa _reprocess con 300 ms de delay.

        Los sliders pueden disparar decenas de eventos por segundo. El debounce
        asegura que el procesamiento de audio solo ocurre cuando el usuario
        deja de mover el control, evitando saturar el hilo de audio.
        """
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(300, self._reprocess)

    def _reprocess(self):
        """
        Lanza EQ + limiter en un hilo daemon con protección contra resultados obsoletos.

        Toma una snapshot de eq_params y lufs_target antes de lanzar el hilo para
        evitar que el hilo lea parámetros modificados a mitad de procesamiento.
        Incrementa _process_gen; el hilo compara su generación antes de escribir
        en session y actualizar la UI — si la generación no coincide, el resultado
        se descarta silenciosamente.
        """
        self._debounce_id = None
        audio = self.session.get("audio_data")
        if audio is None:
            return
        eq_p = dict(self.session["eq_params"])
        lufs_target = self.session["lufs_target"]

        self._process_gen += 1
        gen = self._process_gen

        def _work():
            try:
                eq_out = apply_eq(audio, self.session["sample_rate"],
                                  eq_p["low"], eq_p["low_mid"],
                                  eq_p["hi_mid"], eq_p["high"])
                limited = apply_limiter(eq_out, self.session["sample_rate"], lufs_target)
                if gen != self._process_gen:
                    return
                lufs = measure_lufs(limited, self.session["sample_rate"])
                self.session["processed_audio"] = limited
                self.after(0, lambda: self._player.set_after(limited))
                self.after(0, lambda l=lufs: self._lufs_current.configure(
                    text=f"actual: {l:.1f} LUFS", text_color="#888888"
                ))
            except Exception as e:
                if gen == self._process_gen:
                    self.after(0, lambda err=str(e): self._lufs_current.configure(
                        text=f"Error al procesar: {err}", text_color="#ef4444"
                    ))

        threading.Thread(target=_work, daemon=True).start()

    def _update_lufs_display(self):
        audio = self.session.get("processed_audio")
        if audio is None:
            return
        lufs = measure_lufs(audio, self.session["sample_rate"])
        self._lufs_current.configure(text=f"actual: {lufs:.1f} LUFS", text_color="#888888")
