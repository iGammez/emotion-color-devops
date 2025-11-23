"""
Sistema de Encriptación para Datos Sensibles
Cifra/descifra datos personales antes de guardar en BD
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import os

# Obtener clave de encriptación desde variable de entorno
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "encriptacion-key-32-caracteres-largo").encode()

def generate_key_from_password(password: str, salt: bytes = b'salt_') -> bytes:
    """Generar clave de encriptación desde password"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

# Inicializar Fernet con la clave
try:
    key = generate_key_from_password(ENCRYPTION_KEY.decode())
    cipher_suite = Fernet(key)
except Exception as e:
    print(f"Error inicializando encriptación: {e}")
    # Generar una clave temporal para desarrollo
    key = Fernet.generate_key()
    cipher_suite = Fernet(key)

def encrypt_data(data: str) -> str:
    """
    Encriptar datos sensibles
    
    Args:
        data: Texto plano a encriptar
    
    Returns:
        Texto encriptado en base64
    """
    if not data:
        return data
    
    try:
        encrypted = cipher_suite.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    except Exception as e:
        print(f"Error encriptando datos: {e}")
        return data

def decrypt_data(encrypted_data: str) -> str:
    """
    Desencriptar datos sensibles
    
    Args:
        encrypted_data: Texto encriptado en base64
    
    Returns:
        Texto plano desencriptado
    """
    if not encrypted_data:
        return encrypted_data
    
    try:
        decoded = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = cipher_suite.decrypt(decoded)
        return decrypted.decode()
    except Exception as e:
        print(f"Error desencriptando datos: {e}")
        return encrypted_data

def encrypt_dict(data: dict, fields_to_encrypt: list) -> dict:
    """
    Encriptar campos específicos de un diccionario
    
    Args:
        data: Diccionario con datos
        fields_to_encrypt: Lista de campos a encriptar
    
    Returns:
        Diccionario con campos encriptados
    """
    encrypted_data = data.copy()
    for field in fields_to_encrypt:
        if field in encrypted_data and encrypted_data[field]:
            encrypted_data[field] = encrypt_data(str(encrypted_data[field]))
    return encrypted_data

def decrypt_dict(data: dict, fields_to_decrypt: list) -> dict:
    """
    Desencriptar campos específicos de un diccionario
    
    Args:
        data: Diccionario con datos encriptados
        fields_to_decrypt: Lista de campos a desencriptar
    
    Returns:
        Diccionario con campos desencriptados
    """
    decrypted_data = data.copy()
    for field in fields_to_decrypt:
        if field in decrypted_data and decrypted_data[field]:
            decrypted_data[field] = decrypt_data(str(decrypted_data[field]))
    return decrypted_data

# Ejemplo de uso
if __name__ == "__main__":
    # Datos sensibles de prueba
    datos_personales = {
        "nombre": "Juan Pérez",
        "email": "juan@example.com",
        "telefono": "555-1234",
        "direccion": "Calle Falsa 123"
    }
    
    print("Datos originales:")
    print(datos_personales)
    
    # Encriptar
    datos_encriptados = encrypt_dict(datos_personales, ["email", "telefono", "direccion"])
    print("\n Datos encriptados:")
    print(datos_encriptados)
    
    # Desencriptar
    datos_desencriptados = decrypt_dict(datos_encriptados, ["email", "telefono", "direccion"])
    print("\nDatos desencriptados:")
    print(datos_desencriptados)