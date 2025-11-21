from modules.funciones import listar_carreras, materias_por_semestre, materias_todas
from modules.memoria import obtener_memoria, guardar_memoria, reset_memoria
from thefuzz import process, fuzz 
import unicodedata
import re

# ---------------------------------------------------------
# 1. Mapa de Conocimiento (El Cerebro Semántico)
# ---------------------------------------------------------
SINONIMOS_CARRERAS = {
    "Ingeniería en Sistemas Computacionales": [
        "sistemas", "programacion", "computacion", "desarrollo", "software", "codigo", "app", "web", "isc"
    ],
    "Ingeniería en Gestión Empresarial": [
        "gestion", "empresas", "administracion", "negocios", "ige", "gerencia"
    ],
    "Ingeniería Industrial": [
        "industrial", "procesos", "fabrica", "produccion", "logistica", "ii"
    ],
    "Ingeniería Mecatrónica": [
        "mecatronica", "robotica", "automatizacion", "mecanica", "electronica", "im"
    ]
    # Puedes agregar más carreras aquí siguiendo el formato
}

INTENCIONES = {
    "materias": ["materias", "clases", "asignaturas", "plan de estudios", "reticula", "que llevan"],
    "costos": ["cuanto cuesta", "precio", "costo", "pagar", "inscripcion", "mensualidad"],
    "ubicacion": ["donde estan", "ubicacion", "mapa", "direccion", "llegar"],
    "saludo": ["hola", "buenos dias", "buenas", "que tal", "hey"]
}

# -----------------------------
# Funciones Auxiliares
# -----------------------------
def limpiar_texto(texto):
    texto = texto.lower()
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

def detectar_mejor_coincidencia(texto_usuario, diccionario_opciones):
    """
    Usa lógica difusa para encontrar qué quiso decir el usuario.
    Devuelve la clave principal si la coincidencia es mayor al 75%.
    """
    texto_usuario = limpiar_texto(texto_usuario)
    mejor_score = 0
    mejor_opcion = None

    for clave, sinonimos in diccionario_opciones.items():
        match, score = process.extractOne(texto_usuario, sinonimos, scorer=fuzz.partial_ratio)
        if score > mejor_score:
            mejor_score = score
            mejor_opcion = clave
    
    return mejor_opcion if mejor_score >= 75 else None

# -----------------------------
# Lógica Principal
# -----------------------------
def generar_respuesta(mensaje, user_id, general, carreras, materias):
    mensaje_limpio = limpiar_texto(mensaje)
    memoria = obtener_memoria(user_id)

    # --- 1. Comandos Globales ---
    if 'menu' in mensaje_limpio or 'inicio' in mensaje_limpio:
        reset_memoria(user_id)
        return "🔄 Volvemos al inicio. ¿En qué puedo ayudarte hoy?"

    # --- 2. Detectar Intención General ---
    intencion_detectada = detectar_mejor_coincidencia(mensaje_limpio, INTENCIONES)
    
    if intencion_detectada == "saludo":
        return "¡Hola! 👋 Soy AulaBot. Puedo ayudarte a encontrar tu carrera ideal o darte información sobre materias. ¿Qué te interesa?"
    
    # Buscar respuestas generales en el CSV (fallback)
    for item in general:
        if fuzz.partial_ratio(limpiar_texto(item['palabra_clave']), mensaje_limpio) > 85:
            return item['respuesta']

    # --- 3. Detección Inteligente de Carrera ---
    posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)

    if posible_carrera:
        memoria['carrera_seleccionada'] = posible_carrera
        memoria['modo_materias'] = False 
        guardar_memoria(user_id, memoria)
        
        info_carrera = next((c for c in carreras if c['nombre'] == posible_carrera), None)
        if info_carrera:
            return f"🎓 **{info_carrera['nombre']}** ({info_carrera['clave']})\n⏱ Duración: {info_carrera['duracion']}\n\n{info_carrera['descripcion']}\n\n¿Te gustaría ver las materias de esta carrera?"

    # --- 4. Contexto Activo (El usuario ya eligió carrera) ---
    if memoria.get('carrera_seleccionada'):
        carrera_sel = memoria['carrera_seleccionada']

        if intencion_detectada == "materias" or "si" in mensaje_limpio:
            memoria['modo_materias'] = True
            guardar_memoria(user_id, memoria)
            return f"📂 Estás viendo las materias de **{carrera_sel}**. \n¿Quieres ver 'todas', un semestre específico (ej. 'semestre 5') o buscar una materia por nombre?"

        if memoria.get('modo_materias'):
            # Caso A: Todas
            if 'todas' in mensaje_limpio:
                return materias_todas(carrera_sel, materias)

            # Caso B: Semestre
            nums = re.findall(r'\d+', mensaje_limpio)
            if nums:
                semestre = int(nums[0])
                return materias_por_semestre(carrera_sel, semestre, materias)

            # Caso C: Búsqueda Difusa de Materia
            nombres_materias = [m['materia'] for m in materias if m['carrera'] == carrera_sel]
            if nombres_materias:
                mejor_match, score = process.extractOne(mensaje_limpio, nombres_materias, scorer=fuzz.partial_ratio)
                
                if score > 80:
                    materia_found = next((m for m in materias if m['materia'] == mejor_match and m['carrera'] == carrera_sel), None)
                    if materia_found:
                        return f"📘 **{materia_found['materia']}**\nClave: {materia_found['clave']}\nSemestre: {materia_found['semestre']}\nHoras: {materia_found['horas']}"
            
            return "🤔 No encontré esa materia exacta. Intenta escribir el semestre (ej. '5') o 'todas'."

    # --- 5. Si no entendimos nada ---
    return "No estoy seguro de qué necesitas. 😅 Intenta mencionar una carrera (ej. 'programación', 'negocios') o pregunta por 'ubicación'."