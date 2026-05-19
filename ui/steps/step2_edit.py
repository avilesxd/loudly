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
