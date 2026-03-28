import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

class VaultProtector:
    def __init__(self, password):
        # Usiamo un "Salt" fisso per questo esercizio (in produzione dovrebbe essere unico)
        salt = b'caveau_secret_salt_2026' 
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        self.key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self.fernet = Fernet(self.key)

    def encrypt_file(self, file_path):
        with open(file_path, "rb") as f:
            data = f.read()
        encrypted = self.fernet.encrypt(data)
        with open(file_path + ".locked", "wb") as f:
            f.write(encrypted)
        os.remove(file_path) 

    def decrypt_file(self, locked_path):
        with open(locked_path, "rb") as f:
            data = f.read()
        decrypted = self.fernet.decrypt(data)
        original_path = locked_path.replace(".locked", "")
        with open(original_path, "wb") as f:
            f.write(decrypted)
        os.remove(locked_path)