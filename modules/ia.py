from modules.funciones import listar_carreras, materias_por_semestre, materias_todas, registrar_ignorancia
from modules.memoria import obtener_memoria, guardar_memoria, reset_memoria
from thefuzz import process, fuzz 
import unicodedata
import re

# ---------------------------------------------------------
# 1. Mapa de Conocimiento (Sinónimos y Errores Comunes)
# ---------------------------------------------------------
SINONIMOS_CARRERAS = {
    "Ingeniería en Sistemas Computacionales": [
        "sistemas", "systemas", "sistemaz", "programacion", "computacion", "desarrollo", "software", "codigo", "isc"
    ],
    "Ingeniería en Gestión Empresarial": [
        "gestion", "jestrion", "empresas", "administracion", "negocios", "ige", "gerencia"
    ],
    "Ingeniería Industrial": [
        "industrial", "industria", "procesos", "fabrica", "produccion", "logistica", "ii"
    ],
    "Ingeniería Mecatrónica": [
        "mecatronica", "meca", "robotica", "automatizacion", "mecanica", "electronica", "im"
    ]
    # ¡Agrega más carreras aquí si quieres!
}

INTENCIONES = {
    "materias": ["materias", "materia", "clases", "asignaturas", "plan", "reticula", "que llevan"],
    "costos": ["cuanto cuesta", "precio", "costo", "pagar", "inscripcion", "mensualidad", "dinero"],
    "ubicacion": ["donde estan", "ubicacion", "mapa", "direccion", "llegar", "localizacion"],
    "saludo": ["hola", "buenos dias", "buenas", "que tal", "hey", "hi"]
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
    Detecta qué quiso decir el usuario incluso si escribe mal.
    Ej: 'systemaz' -> Detecta 'sistemas' con un score alto.
    """
    texto_usuario = limpiar_texto(texto_usuario)
    mejor_score = 0
    mejor_opcion = None

    for clave, sinonimos in diccionario_opciones.items():
        # token_set_ratio es muy bueno ignorando palabras extra y detectando typos
        match, score = process.extractOne(texto_usuario, sinonimos, scorer=fuzz.token_set_ratio)
        
        if score > mejor_score:
            mejor_score = score
            mejor_opcion = clave
    
    # Umbral de 70: Suficientemente flexible para typos
    return mejor_opcion if mejor_score >= 70 else None

# -----------------------------
# Lógica Principal
# -----------------------------
def generar_respuesta(mensaje, user_id, general, carreras, materias):
    mensaje_limpio = limpiar_texto(mensaje)
    memoria = obtener_memoria(user_id)

    # --- 1. Comandos Globales ---
    if 'menu' in mensaje_limpio or 'inicio' in mensaje_limpio:
        reset_memoria(user_id)
        return "🔄 Reiniciado. ¿En qué puedo ayudarte?"

    # --- 2. Detectar Intención General ---
    intencion = detectar_mejor_coincidencia(mensaje_limpio, INTENCIONES)
    
    if intencion == "saludo":
        return "¡Hola! 👋 Soy AulaBot. Pregúntame por alguna carrera (ej. 'Sistemas') o ubicación."

    # Buscamos en CSV General (Respuestas fijas)
    for item in general:
        if fuzz.partial_ratio(limpiar_texto(item['palabra_clave']), mensaje_limpio) > 85:
            return item['respuesta']

    # --- 3. Detección Inteligente de Carrera ---
    posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)

    # Si encontramos una carrera (incluso mal escrita)
    if posible_carrera:
        memoria['carrera_seleccionada'] = posible_carrera
        memoria['modo_materias'] = False 
        guardar_memoria(user_id, memoria)
        
        info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
        if info:
            # Confirmamos sutilmente lo que entendimos
            return f"🔍 Entendí que buscas sobre **{info['nombre']}**.\n\n📝 **Descripción:** {info['descripcion']}\n⏱ **Duración:** {info['duracion']}\n\n¿Te gustaría ver las **materias**?"

    # --- 4. Contexto Activo (Ya eligió carrera) ---
    if memoria.get('carrera_seleccionada'):
        carrera_sel = memoria['carrera_seleccionada']

        # Detectar si pide materias (ej. "si", "cuales son", "materias")
        if intencion == "materias" or "si" in mensaje_limpio or "ver" in mensaje_limpio:
            memoria['modo_materias'] = True
            guardar_memoria(user_id, memoria)
            return f"📂 Abriendo plan de estudios de **{carrera_sel}**.\nPuedes escribir:\n1️⃣ 'Todas'\n2️⃣ Un semestre (ej. '5')\n3️⃣ Nombre de materia (ej. 'programacion')"

        if memoria.get('modo_materias'):
            # Caso A: Todas
            if 'todas' in mensaje_limpio:
                return materias_todas(carrera_sel, materias)

            # Caso B: Semestre
            nums = re.findall(r'\d+', mensaje_limpio)
            if nums:
                return materias_por_semestre(carrera_sel, int(nums[0]), materias)

            # Caso C: Búsqueda Difusa de Materia (Corregir typos en materias)
            nombres_materias = [m['materia'] for m in materias if m['carrera'] == carrera_sel]
            if nombres_materias:
                match, score = process.extractOne(mensaje_limpio, nombres_materias, scorer=fuzz.token_set_ratio)
                
                if score > 75:
                    m = next((x for x in materias if x['materia'] == match and x['carrera'] == carrera_sel), None)
                    return f"📘 **{m['materia']}**\nClave: {m['clave']} | Semestre: {m['semestre']} | Horas: {m['horas']}"
            
            return f"🤔 No encontré una materia que suene a '{mensaje}'. Intenta escribir solo el número de semestre."

    # --- 5. Fallback (No entendió nada) ---
    registrar_ignorancia(mensaje_limpio)
    return "No estoy seguro de qué carrera o tema hablas. 😅\nPrueba escribiendo palabras clave como 'Sistemas', 'Industrial' o 'Ubicación'."