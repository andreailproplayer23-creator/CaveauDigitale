import customtkinter as ctk
import os
from tkinter import filedialog, messagebox

class VaultDashboard(ctk.CTkToplevel):
    def __init__(self, master_password):
        super().__init__()
        self.title("CAVEAU ATTIVO")
        self.geometry("800x600")
        self.configure(fg_color="#0A0B10")
        
        from encryption import VaultProtector
        self.protector = VaultProtector(master_password)
        self.vault_dir = "ARCHIVIO_CRIPTATO"
        
        if not os.path.exists(self.vault_dir):
            os.makedirs(self.vault_dir)

        self.setup_ui()

    def setup_ui(self):
        # Header
        head = ctk.CTkFrame(self, fg_color="#161B22", height=60, corner_radius=0)
        head.pack(fill="x")
        ctk.CTkLabel(head, text="🔒 FILE PROTETTI", font=("Bahnschrift", 18, "bold"), text_color="#238636").pack(side="left", padx=20)
        
        # Area Lista File
        self.file_list = ctk.CTkTextbox(self, fg_color="#0D1117", border_color="#30363D", border_width=1)
        self.file_list.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Bottoni Azione
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", pady=20)
        
        ctk.CTkButton(btn_bar, text="+ AGGIUNGI FILE", fg_color="#238636", command=self.import_file).pack(side="left", padx=20)
        ctk.CTkButton(btn_bar, text="🔓 SBLOCCA SELEZIONATO", fg_color="#1F6AA5", command=self.export_file).pack(side="left", padx=10)
        
        self.refresh_files()

    def import_file(self):
        path = filedialog.askopenfilename()
        if path:
            import shutil
            filename = os.path.basename(path)
            dest = os.path.join(self.vault_dir, filename)
            shutil.copy(path, dest)
            self.protector.encrypt(dest)
            self.refresh_files()
            messagebox.showinfo("Sicurezza", "File criptato con successo!")

    def export_file(self):
        # Logica per selezionare e decriptare il file (da rifinire con selezione riga)
        messagebox.showinfo("Info", "Seleziona il file dal testo per sbloccarlo (Logica in sviluppo)")

    def refresh_files(self):
        self.file_list.delete("1.0", "end")
        for f in os.listdir(self.vault_dir):
            self.file_list.insert("end", f"FILE CRIPTATO -> {f}\n")