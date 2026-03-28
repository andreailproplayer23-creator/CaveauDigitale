import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

class CryptoEngine:
    def __init__(self, password):
        # Generiamo una chiave sicura partendo dalla tua password
        salt = b'sale_fisso_16byte' # In un sistema reale dovrebbe essere randomico
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self.fernet = Fernet(key)

    def encrypt_file(self, file_path):
        with open(file_path, "rb") as f:
            data = f.read()
        encrypted_data = self.fernet.encrypt(data)
        with open(file_path + ".locked", "wb") as f:
            f.write(encrypted_data)
        os.remove(file_path) # Elimina l'originale non protetto

    def decrypt_file(self, locked_path):
        with open(locked_path, "rb") as f:
            encrypted_data = f.read()
        decrypted_data = self.fernet.decrypt(encrypted_data)
        original_path = locked_path.replace(".locked", "")
        with open(original_path, "wb") as f:
            f.write(decrypted_data)
        os.remove(locked_path) # Elimina la versione criptata