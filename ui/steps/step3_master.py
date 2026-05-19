# ui/steps/step3_master.py
import customtkinter as ctk

class Step3Master(ctk.CTkFrame):
    def __init__(self, parent, session, on_back):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.session = session
        ctk.CTkLabel(self, text="Paso 3 — Masterizar (stub)").pack(pady=40)
        ctk.CTkButton(self, text="← Atrás", command=on_back).pack()

    def on_enter(self): pass
