import customtkinter as ctk
from tkinter import messagebox, filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD
import os, shutil, zipfile
import locale
from database import VaultDB
from encryption import VaultProtector
from translations import LANGUAGES

# --- GESTIONE LINGUE ---
def get_system_lang():
    try:
        # Metodo moderno per ottenere la lingua (evita il warning)
        lang_info = locale.getlocale()[0] 
        if not lang_info:
            # Fallback se getlocale() fallisce su alcuni sistemi
            lang_info = locale.getdefaultlocale()[0]
            
        if lang_info:
            code = lang_info[:2].upper()
            if code in LANGUAGES:
                return LANGUAGES[code]
    except:
        pass
    return LANGUAGES["IT"] # Default Italiano

TR = get_system_lang() # Variabile globale per i testi

# --- CONFIGURAZIONE ESTETICA ---
CLR_BG, CLR_PANEL, CLR_ACCENT = "#0A0B10", "#161B22", "#238636"
CLR_INFO, CLR_ERR = "#1F6AA5", "#DA3633"
FONT_BOLD, FONT_SMALL = ("Bahnschrift", 14, "bold"), ("Bahnschrift", 11)

# --- FINESTRA PASSWORD OSCURATA ---
class PasswordDialog(ctk.CTkToplevel):
    def __init__(self, title, text):
        super().__init__()
        self.title(title)
        self.geometry("350x200")
        self.resizable(False, False)
        self.result = None
        self.configure(fg_color=CLR_PANEL)
        
        ctk.CTkLabel(self, text=text, font=FONT_SMALL, wraplength=300).pack(pady=20)
        self.entry = ctk.CTkEntry(self, show="*", width=250)
        self.entry.pack(pady=10)
        self.entry.focus()
        
        btn = ctk.CTkButton(self, text="OK", fg_color=CLR_ACCENT, command=self.set_res)
        btn.pack(pady=10)
        
        self.bind("<Return>", lambda e: self.set_res())
        self.grab_set() 

    def set_res(self):
        self.result = self.entry.get()
        self.destroy()

    def get_input(self):
        self.master.wait_window(self)
        return self.result

# --- DASHBOARD PRINCIPALE ---
class VaultDashboard(ctk.CTkToplevel):
    def __init__(self, master_app, master_pass, username):
        super().__init__(master_app)
        self.master_app, self.master_pass, self.username = master_app, master_pass, username
        self.db = VaultDB()
        self.vault_dir = os.path.join(os.path.expanduser("~"), "Documents", "CaveauDigitale_Archivio")
        if not os.path.exists(self.vault_dir): 
            os.makedirs(self.vault_dir)

        self.title(f"{TR['title']} - {username.upper()}")
        self.geometry("1100x800")
        self.configure(fg_color=CLR_BG)
        self.protocol("WM_DELETE_WINDOW", self.master_app.quit)
        
        self.search_var = ctk.StringVar()
        self.setup_ui()

    def setup_ui(self):
        # Header
        head = ctk.CTkFrame(self, fg_color=CLR_PANEL, height=80, corner_radius=0)
        head.pack(fill="x")
        ctk.CTkLabel(head, text=f"🛡️ {TR['title']}", font=("Bahnschrift", 18, "bold"), text_color=CLR_ACCENT).pack(side="left", padx=30)
        
        # Barra di Ricerca Real-Time
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=30, pady=(20, 0))
        self.search_bar = ctk.CTkEntry(search_frame, placeholder_text=TR["search_ph"], 
                                      textvariable=self.search_var, height=40)
        self.search_bar.pack(fill="x")
        self.search_bar.bind("<KeyRelease>", lambda e: self.refresh_files())
        
        # Container Lista File
        self.file_container = ctk.CTkScrollableFrame(self, fg_color="#0D1117", border_width=1, border_color="#30363D")
        self.file_container.pack(fill="both", expand=True, padx=30, pady=20)

        # Drag & Drop
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', lambda e: [self.process_new_item(f) for f in self.tk.splitlist(e.data)])

        # Footer con tasti separati
        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.pack(fill="x", pady=20)
        
        ctk.CTkButton(foot, text=TR["btn_file"], fg_color=CLR_ACCENT, font=FONT_BOLD, 
                      width=140, height=45, command=self.add_file_manual).pack(side="left", padx=(30, 10))
        
        ctk.CTkButton(foot, text=TR["btn_folder"], fg_color=CLR_INFO, font=FONT_BOLD, 
                      width=140, height=45, command=self.add_folder_manual).pack(side="left")
        
        ctk.CTkButton(foot, text=TR["btn_close"], fg_color=CLR_ERR, font=FONT_BOLD, 
                      width=120, height=45, command=self.destroy).pack(side="right", padx=30)
        
        self.refresh_files()

    def add_file_manual(self):
        p = filedialog.askopenfilename()
        if p: self.process_new_item(p)

    def add_folder_manual(self):
        p = filedialog.askdirectory()
        if p: self.process_new_item(p)

    def process_new_item(self, source_path):
        is_folder = 1 if os.path.isdir(source_path) else 0
        name = os.path.basename(source_path)
        stat = os.stat(source_path)
        
        # 1. Chiediamo la Password (con il trucco del nome file)
        msg_pwd = TR["prompt_pwd"].replace("{name}", name)
        pwd = PasswordDialog(TR["title"], msg_pwd).get_input()
        if pwd is None: return # L'utente ha chiuso la finestra
        
        use_master = 1 if pwd == "" else 0
        file_pass = self.master_pass if use_master else pwd
        
        # --- 2. GESTIONE DOMANDE DI SICUREZZA ---
        fq1, fa1, fq2, fa2 = "", "", "", ""
        if not use_master:
            # Chiediamo le domande solo se NON si usa la Master Password
            fq1 = ctk.CTkInputDialog(text="Domanda di sicurezza 1 per questo file:", title="Reset Setup").get_input() or "Domanda 1"
            fa1 = ctk.CTkInputDialog(text="Risposta 1:", title="Reset Setup").get_input() or "reset"
            fq2 = ctk.CTkInputDialog(text="Domanda di sicurezza 2 per questo file:", title="Reset Setup").get_input() or "Domanda 2"
            fa2 = ctk.CTkInputDialog(text="Risposta 2:", title="Reset Setup").get_input() or "reset"

        # 3. Chiediamo la Nota
        note = ctk.CTkInputDialog(text=TR["prompt_note"], title="Info").get_input() or "Nessuna nota"

        # --- 4. LOGICA DI CRITTOGRAFIA (rimane uguale) ---
        process_path = source_path
        if is_folder:
            zip_name = shutil.make_archive(source_path, 'zip', source_path)
            process_path = zip_name

        try:
            filename_to_lock = os.path.basename(process_path)
            dest = os.path.join(self.vault_dir, filename_to_lock)
            shutil.move(process_path, dest)
            VaultProtector(file_pass).encrypt_file(dest)
            
            if is_folder and os.path.exists(source_path):
                shutil.rmtree(source_path)

            # --- 5. SALVATAGGIO NEL DATABASE ---
            # Passiamo tutti i 11 parametri (il 12esimo, la data, lo mette il DB da solo)
            self.db.register_file_metadata(
                filename_to_lock, 
                os.path.dirname(source_path), 
                note, 
                stat.st_atime, 
                stat.st_mtime, 
                use_master, 
                fq1, fa1, fq2, fa2, 
                is_folder=is_folder
            )
            self.refresh_files()
            
        except Exception as e: 
            messagebox.showerror(TR["msg_error"], str(e))

    def refresh_files(self):
        for w in self.file_container.winfo_children(): w.destroy()
        search_term = self.search_var.get().lower()
        
        files = [f for f in os.listdir(self.vault_dir) if f.endswith(".locked")]
        for f in files:
            clean = f.replace(".locked", "")
            m = self.db.get_file_info(clean)
            
            # Filtro Ricerca Nome o Nota
            if search_term:
                note = m[3].lower() if m else ""
                if search_term not in clean.lower() and search_term not in note: continue

            icon = "📁" if (m and m[11] == 1) else "📄"
            row = ctk.CTkFrame(self.file_container, fg_color="#1C2128", corner_radius=10)
            row.pack(fill="x", pady=5, padx=10)
            ctk.CTkLabel(row, text=f"{icon} {clean}", font=("Consolas", 12, "bold")).pack(side="left", padx=20)
            ctk.CTkButton(row, text=TR["btn_unlock"], width=100, command=lambda n=f: self.unlock_item(n)).pack(side="right", padx=15)

    def unlock_item(self, filename):
        clean = filename.replace(".locked", "")
        path = os.path.join(self.vault_dir, filename)
        m = self.db.get_file_info(clean) # Prende i dati dal DB

        # --- AGGIUNGI QUESTO CONTROLLO ---
        if m is None:
            messagebox.showerror("Errore", "File non censito nel database.")
            return
        # --------------------------------

        msg = TR["prompt_pwd"].replace("{name}", clean)
        pwd = PasswordDialog(TR["title"], msg).get_input()
        
        if pwd is not None:
            try:
                # Prova a sbloccare
                VaultProtector(pwd).decrypt_file(path)
                self.finalize_unlock(clean, m) # Qui m non sarà più None
            except Exception:
                # Se fallisce (password errata), chiama il reset
                self.handle_reset(m, clean, path)

    # Assicurati che accetti esattamente questi parametri
    def handle_reset(self, m, clean_name, path): 
        # Se m è None (perché il file non è nel DB), usciamo subito
        if m is None:
            messagebox.showerror("Errore", "Dati del file non trovati nel database.")
            return

        use_master = m[6] # 6 è la colonna use_master
        
        if use_master == 1:
            messagebox.showinfo("Info", "Questo file usa la Master Password. Usa il recupero nel Login.")
        else:
            q1, a1 = m[7], m[8]
            ans = ctk.CTkInputDialog(text=f"Recupero per: {clean_name}\n\nDomanda: {q1}", title="Reset").get_input()
            
            if ans and ans.lower() == a1.lower():
                messagebox.showinfo("Successo", "Risposta corretta! Ora puoi usare la tua password per sbloccare.")
            else:
                messagebox.showerror("Errore", "Risposta errata!")

    def finalize_unlock(self, clean, m):
        temp_path = os.path.join(self.vault_dir, clean)
        if m[11] == 1:
            folder_name = clean.replace(".zip", "")
            extract_path = os.path.join(m[1], folder_name)
            shutil.unpack_archive(temp_path, extract_dir=extract_path)
            os.remove(temp_path)
            final_p = extract_path
        else:
            final_p = os.path.join(m[1], clean)
            shutil.move(temp_path, final_p)
        
        os.utime(final_p, (m[4], m[5]))
        self.db.delete_file_metadata(clean)
        self.refresh_files()
        os.startfile(os.path.dirname(final_p))

class MainApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)
        self.db = VaultDB()
        self.title(TR["title"])
        self.geometry("450x700")
        self.configure(fg_color=CLR_BG)
        self.container = ctk.CTkFrame(self, fg_color=CLR_PANEL, corner_radius=25)
        self.container.pack(expand=True, padx=40, pady=40, fill="both")
        if not self.db.has_users(): self.show_reg()
        else: self.show_login()

    def show_reg(self):
        for w in self.container.winfo_children(): w.destroy()
        ctk.CTkLabel(self.container, text=TR["reg_title"], font=FONT_BOLD, text_color=CLR_ACCENT).pack(pady=20)
        
        # Campi Login
        u = ctk.CTkEntry(self.container, placeholder_text=TR["login_user"], width=250)
        p = ctk.CTkEntry(self.container, placeholder_text=TR["login_pass"], show="*", width=250)
        u.pack(pady=5); p.pack(pady=5)
        
        # --- AGGIUNGI QUESTI CAMPI PER LE DOMANDE ---
        ctk.CTkLabel(self.container, text="Sicurezza Master Password:", font=FONT_SMALL).pack(pady=(10,0))
        q1 = ctk.CTkEntry(self.container, placeholder_text="Domanda di recupero (es: Nome gatto?)", width=250)
        a1 = ctk.CTkEntry(self.container, placeholder_text="Risposta", width=250)
        q1.pack(pady=5); a1.pack(pady=5)
        
        # Pulsante Crea
        ctk.CTkButton(self.container, text=TR["reg_btn"], fg_color=CLR_ACCENT,
                      command=lambda: self.handle_registration(u.get(), p.get(), q1.get(), a1.get())).pack(pady=20)

    def handle_registration(self, u, p, q, a):
        # Controlliamo che tutti i campi siano stati compilati
        if u.strip() and p.strip() and q.strip() and a.strip():
            # Passiamo i dati direttamente al database. 
            # Inviando 'p' così com'è, verrà salvata la parola leggibile 
            # che potrai recuperare in caso di smarrimento.
            self.db.register_user(u, p, q, a, "", "")
            
            messagebox.showinfo("Successo", "Caveau creato correttamente!")
            self.show_login()
        else:
            messagebox.showwarning("Errore", "Tutti i campi sono obbligatori per la sicurezza!")

    def show_login(self):
        for w in self.container.winfo_children(): w.destroy()
        ctk.CTkLabel(self.container, text=TR["title"], font=FONT_BOLD, text_color=CLR_ACCENT).pack(pady=40)
        
        u = ctk.CTkEntry(self.container, placeholder_text=TR["login_user"], width=250)
        p = ctk.CTkEntry(self.container, placeholder_text=TR["login_pass"], show="*", width=250)
        u.pack(pady=10); p.pack(pady=10)
        
        # Tasto Login principale
        ctk.CTkButton(self.container, text=TR["login_btn"], 
                      command=lambda: self.handle_login(u.get(), p.get())).pack(pady=10)
        
        # NUOVO: Tasto per recuperare la Master Password
        ctk.CTkButton(self.container, text="Recupera Master Password", 
                      fg_color="transparent", text_color="gray", hover_color="#333333",
                      command=self.master_recovery_dialog).pack(pady=5)

    def master_recovery_dialog(self):
        user = ctk.CTkInputDialog(text="Inserisci il tuo nome utente:", title="Recupero Master").get_input()
        if not user: return
        
        data = self.db.get_user_data(user)
        if data:
            # data[2] è la domanda, data[3] è la risposta, data[1] è la password
            ans = ctk.CTkInputDialog(text=f"Domanda di sicurezza:\n{data[2]}", title="Recupero").get_input()
            if ans and ans.lower() == data[3].lower():
                messagebox.showinfo("Recupero", f"La tua Master Password è:\n\n{data[1]}")
            else:
                messagebox.showerror("Errore", "Risposta errata!")
        else:
            messagebox.showerror("Errore", "Utente non trovato.")

    def handle_login(self, u, p):
        if self.db.check_login(u, p): self.withdraw(); VaultDashboard(self, p, u)
        else: messagebox.showerror(TR["msg_error"], "Dati errati")

if __name__ == "__main__":
    MainApp().mainloop()