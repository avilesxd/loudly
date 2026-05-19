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
