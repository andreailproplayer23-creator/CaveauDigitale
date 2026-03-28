import sqlite3
import hashlib
import os
from datetime import datetime

class VaultDB:
    def __init__(self):
        # --- MODIFICA QUI ---
        # Creiamo il database nella cartella AppData dell'utente, non in quella del programma
        appdata_dir = os.path.join(os.environ['APPDATA'], 'CaveauDigitale')
        if not os.path.exists(appdata_dir):
            os.makedirs(appdata_dir)
            
        db_path = os.path.join(appdata_dir, 'users.db')
        # --------------------
        
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Questo comando crea la tabella degli utenti se non esiste
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users 
            (username TEXT, password TEXT, q1 TEXT, a1 TEXT, q2 TEXT, a2 TEXT)''')
        
        # PROVA A CREARE LA TABELLA METADATA
        # Se esiste già ma è vecchia, darà errore, quindi usiamo un try/except
        try:
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS file_metadata 
                (filename TEXT, path TEXT, date TEXT, note TEXT, atime REAL, mtime REAL, 
                 use_master INTEGER, fq1 TEXT, fa1 TEXT, fq2 TEXT, fa2 TEXT, is_folder INTEGER)''')
        except:
            # Se la tabella esiste ma ha colonne diverse, la cancelliamo e la rifacciamo
            self.cursor.execute("DROP TABLE file_metadata")
            self.cursor.execute('''CREATE TABLE file_metadata 
                (filename TEXT, path TEXT, date TEXT, note TEXT, atime REAL, mtime REAL, 
                 use_master INTEGER, fq1 TEXT, fa1 TEXT, fq2 TEXT, fa2 TEXT, is_folder INTEGER)''')
        
        self.conn.commit()

    def register_user(self, username, password, q1, a1, q2, a2):
        # Salviamo la password così come la scrive l'utente 
        # (visto che è un database locale protetto, possiamo farlo per il recupero)
        self.cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", 
                            (username, password, q1, a1.lower(), q2, a2.lower()))
        self.conn.commit()

    def check_login(self, username, password):
        self.cursor.execute("SELECT password FROM users WHERE username=?", (username,))
        result = self.cursor.fetchone()
        
        if result:
            # Confronto diretto tra la password inserita e quella nel DB
            return result[0] == password
        return False

    def has_users(self):
        self.cursor.execute("SELECT count(*) FROM users")
        return self.cursor.fetchone()[0] > 0

    def register_file_metadata(self, filename, path, note, atime, mtime, use_master, fq1="", fa1="", fq2="", fa2="", is_folder=0):
        # 1. Puliamo il nome (togliamo .locked se presente)
        clean = filename.replace(".locked", "")
        
        # 2. Cancelliamo se esisteva già un vecchio record con lo stesso nome
        self.cursor.execute("DELETE FROM file_metadata WHERE filename=?", (clean,))
        
        # 3. Prendiamo la data attuale
        from datetime import datetime
        date_now = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        # 4. Inseriamo i 12 valori (conta i punti interrogativi: sono 12!)
        # filename, path, date, note, atime, mtime, master, q1, a1, q2, a2, folder
        self.cursor.execute("INSERT INTO file_metadata VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", 
                            (clean, path, date_now, note, atime, mtime, use_master, fq1, fa1.lower(), fq2, fa2.lower(), is_folder))
        self.conn.commit()

    def get_file_info(self, filename):
        clean = filename.replace(".locked", "")
        self.cursor.execute("SELECT * FROM file_metadata WHERE filename=?", (clean,))
        return self.cursor.fetchone()

    def delete_file_metadata(self, filename):
        clean = filename.replace(".locked", "")
        self.cursor.execute("DELETE FROM file_metadata WHERE filename=?", (clean,))
        self.conn.commit()

    def get_master_questions(self, u):
        self.cursor.execute("SELECT q1, a1, q2, a2 FROM users WHERE username=?", (u,))
        return self.cursor.fetchone()
    
    def get_user_data(self, username):
        """Recupera tutti i dati di un utente specifico per il reset"""
        try:
            self.cursor.execute("SELECT * FROM users WHERE username=?", (username,))
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Errore recupero dati utente: {e}")
            return None