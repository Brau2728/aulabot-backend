# ---------------------------------------------------------
# Memoria de sesión en RAM (Soporte Multi-usuario)
# ---------------------------------------------------------

# Diccionario global para almacenar las sesiones
_memorias_usuarios = {}

def obtener_memoria(user_id: str) -> dict:
    """
    Devuelve la memoria actual de un usuario específico.
    Si no existe, devuelve un diccionario vacío con estructura completa.
    """
    global _memorias_usuarios
    if user_id not in _memorias_usuarios:
        _memorias_usuarios[user_id] = {
            'carrera_seleccionada': None,
            'modo_materias': False,
            'ultimo_tema': None,
            'conversacion': [],  # Historial de últimos mensajes
            'contexto_anterior': None
        }
    return _memorias_usuarios[user_id].copy()

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
    if user_id in _memorias_usuarios:
        del _memorias_usuarios[user_id]

def actualizar_conversacion(user_id: str, mensaje: str, respuesta: str):
    """Guarda el contexto de la conversación"""
    memoria = obtener_memoria(user_id)
    if 'conversacion' not in memoria:
        memoria['conversacion'] = []
    
    memoria['conversacion'].append({'usuario': mensaje, 'bot': respuesta})
    # Mantener solo los últimos 5 mensajes
    if len(memoria['conversacion']) > 5:
        memoria['conversacion'] = memoria['conversacion'][-5:]
    
    guardar_memoria(user_id, memoria)