"""Contraseñas PBKDF2-HMAC-SHA256 con compatibilidad temporal SHA-256."""
import hashlib
import hmac
import os

ITERACIONES = 600_000


def crear_hash(contrasena):
    if len(contrasena) < 10:
        raise ValueError('La contraseña debe tener al menos 10 caracteres.')
    sal = os.urandom(16)
    clave = hashlib.pbkdf2_hmac('sha256', contrasena.encode('utf-8'), sal, ITERACIONES)
    return f'pbkdf2_sha256${ITERACIONES}${sal.hex()}${clave.hex()}'


def verificar_contrasena(contrasena, almacenada):
    """Devuelve (válida, requiere_migración)."""
    if not almacenada:
        return False, False
    if almacenada.startswith('pbkdf2_sha256$'):
        try:
            algoritmo, rondas, sal_hex, clave_hex = almacenada.split('$')
            rondas = int(rondas)
            if rondas < 1 or rondas > 2_000_000:
                return False, False
            sal = bytes.fromhex(sal_hex)
            esperado = bytes.fromhex(clave_hex)
            obtenido = hashlib.pbkdf2_hmac('sha256', contrasena.encode('utf-8'), sal, rondas)
            return hmac.compare_digest(obtenido, esperado), False
        except (ValueError, TypeError):
            return False, False
    if len(almacenada) == 64:
        anterior = hashlib.sha256(contrasena.encode('utf-8')).hexdigest()
        correcto = hmac.compare_digest(anterior, almacenada.lower())
        return correcto, correcto
    return False, False
