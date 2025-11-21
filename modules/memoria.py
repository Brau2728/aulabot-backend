# ---------------------------------------------------------
# Memoria de sesión en RAM (Soporte Multi-usuario)
# ---------------------------------------------------------

# Diccionario global para almacenar las sesiones
# Estructura: { "usuario_1": {...datos...}, "usuario_2": {...datos...} }
_memorias_usuarios = {}

def obtener_memoria(user_id: str) -> dict:
    """
    Devuelve la memoria actual de un usuario específico.
    Si no existe, devuelve un diccionario vacío.
    """
    global _memorias_usuarios
    # Usamos .get() para evitar errores si el usuario es nuevo
    return _memorias_usuarios.get(user_id, {}).copy()

def guardar_memoria(user_id: str, datos: dict):
    """
    Guarda o actualiza los datos de sesión de un usuario.
    """
    global _memorias_usuarios
    _memorias_usuarios[user_id] = datos

def reset_memoria(user_id: str):
    """
    Borra la memoria de un usuario (ej. cuando dice 'menu' o 'salir').
    """
    global _memorias_usuarios