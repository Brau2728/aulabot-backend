# Memoria de sesión simple en memoria
_memoria = {}

def guardar_memoria(datos):
    global _memoria
    _memoria = datos

def obtener_memoria():
    global _memoria
    return _memoria.copy()

def reset_memoria():
    global _memoria
    _memoria = {}
