import google.generativeai as genai
from modules.funciones import listar_carreras, materias_por_semestre, materias_todas, registrar_ignorancia, cargar_conocimiento_adquirido, guardar_nuevo_conocimiento
from modules.memoria import obtener_memoria, guardar_memoria, reset_memoria
from thefuzz import process, fuzz 
import unicodedata
import re
import random
import os

# =========================================================
# 🤖 CONFIGURACIÓN DE GEMINI
# =========================================================
API_KEY = os.getenv("GEMINI_API_KEY") 

try:
    if API_KEY:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        USAR_GEMINI = True
    else:
        USAR_GEMINI = False
except Exception as e:
    USAR_GEMINI = False

# =========================================================
# 🧱 BANCO DE FRASES
# =========================================================
FRASES_SALUDO_CON_NOMBRE = [
    "¡Hola, {nombre}! 👋 Soy AulaBot. ¿En qué te puedo ayudar?",
    "¡Qué tal, {nombre}! 🤖 Aquí tu asistente listo. ¿Qué necesitas?",
    "¡Hola, {nombre}! 😊 Un gusto saludarte de nuevo.",
    "¡Buenas, {nombre}! 🎓 ¿Buscas información de alguna carrera?",
]

FRASES_MATERIAS = [
    "📂 ¡Listo, {nombre}! Aquí tienes el plan de estudios de **{carrera}**:",
    "📘 {nombre}, checa las materias que se llevan en **{carrera}**:",
    "🎓 Estas son las asignaturas para **{carrera}**, {nombre}:",
    "📚 Desplegando la retícula de **{carrera}**. ¡Mira esto, {nombre}!:"
]

FRASES_NO_ENTENDI = [
    "Mmm, esa no me la sé, {nombre}. 😅 Pero ya anoté tu duda.",
    "¡Órale, {nombre}! Me corchaste con esa pregunta. 🤔 Intenta con otra cosa.",
    "No estoy seguro de qué hablas, {nombre}. 🤷‍♂️ Prueba con 'Costos' o 'Sistemas'.",
    "Ese dato se me escapa. 🧐 ¿Podrías ser más específico?",
]

FRASES_REINICIO = [
    "🔄 Conversación reiniciada. ¡Empecemos de cero! ¿Cuál es tu nombre?", # Vuelve a pedir nombre al reiniciar
    "🧹 Memoria borrada. Hola de nuevo, ¿cómo te llamas?",
    "Listo, borrón y cuenta nueva. 🔄 ¿Me recuerdas tu nombre?"
]

# =========================================================
# 1. MAPAS DE CONOCIMIENTO (Sin cambios)
# =========================================================
SINONIMOS_CARRERAS = {
    "Ingeniería en Sistemas Computacionales": ["sistemas", "systemas", "programacion", "computacion", "desarrollo", "software", "codigo", "isc"],
    "Ingeniería en Gestión Empresarial": ["gestion", "empresas", "administracion", "negocios", "ige", "gerencia"],
    "Ingeniería Industrial": ["industrial", "industria", "procesos", "fabrica", "produccion", "ii"],
    "Ingeniería Mecatrónica": ["mecatronica", "meca", "robotica", "automatizacion", "im"],
    "Ingeniería Bioquímica": ["bioquimica", "biologia", "alimentos", "ibq"],
    "Ingeniería en Nanotecnología": ["nanotecnologia", "nano", "materiales", "ina"],
    "Ingeniería en Innovación Agrícola Sustentable": ["agricola", "agronomia", "campo", "cultivos", "iias"],
    "Ingeniería en Tecnologías de la Información y Comunicaciones": ["tics", "tic", "redes", "telecom", "itic"],
    "Ingeniería en Animación Digital y Efectos Visuales": ["animacion", "digital", "3d", "visuales", "iadev"],
    "Ingeniería en Sistemas Automotrices": ["automotriz", "autos", "coches", "mecanica automotriz", "isau"]
}

INTENCIONES = {
    "materias": ["materias", "materia", "clases", "asignaturas", "reticula", "plan", "curricula"],
    "carreras_lista": ["carreras", "programas academicos", "que carreras tienen", "cuales son las carreras"],
    "jefes": ["jefe de carrera", "jefe de division", "quien es el jefe"], 
    "costos": ["cuanto cuesta", "precio", "costo", "pagar", "inscripcion", "mensualidad", "dinero", "ficha", "pago"],
    "ubicacion": ["donde estan", "ubicacion", "mapa", "direccion", "llegar", "localizacion", "domicilio"],
    "saludo": ["hola", "buenos dias", "buenas", "que tal", "hey", "hi", "inicio", "comenzar"],
    "directorio": ["director", "jefe", "coordinador", "quien es", "encargado", "subdirector"],
    "tramites": ["admision", "propedeutico", "examen", "becas", "servicio social", "residencias", "titulacion", "fechas", "convocatoria"],
    "ayuda": ["que sabes hacer", "que puedes hacer", "ayuda", "instrucciones", "para que sirves", "menu", "opciones", "temas"],
    "institucional": ["mision", "vision", "objetivos", "historia", "fundacion"],
    "vida_estudiantil": ["deportes", "futbol", "cafeteria", "ingles", "centro de idiomas", "psicologia"],
    "afirmacion": ["si", "claro", "por favor", "yes", "simon", "ok", "va", "me parece"],
    "negacion": ["no", "nel", "asi dejalo", "gracias"]
}

# Funciones Auxiliares
def limpiar_texto(texto):
    texto = texto.lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def detectar_mejor_coincidencia(texto_usuario, diccionario):
    texto_usuario = limpiar_texto(texto_usuario)
    mejor_opcion, mejor_score = None, 0
    for clave, sinonimos in diccionario.items():
        match, score = process.extractOne(texto_usuario, sinonimos, scorer=fuzz.token_set_ratio)
        if score > mejor_score:
            mejor_score = score
            mejor_opcion = clave
    return mejor_opcion if mejor_score >= 70 else None

def consultar_gemini(contexto, pregunta_usuario):
    if not USAR_GEMINI: return contexto 
    prompt = f"""
    Eres AulaBot del ITSCH.
    INFORMACIÓN OFICIAL: "{contexto}"
    USUARIO: "{pregunta_usuario}"
    TAREA: Responde amable y profesionalmente usando SOLO la info oficial. 
    """
    try:
        response = genai.GenerativeModel('gemini-pro').generate_content(prompt)
        return response.text
    except: return contexto 

# =========================================================
# 3. LÓGICA PRINCIPAL (CEREBRO CON NOMBRE)
# =========================================================
def generar_respuesta(mensaje, user_id, general, carreras, materias):
    mensaje_limpio = limpiar_texto(mensaje)
    memoria = obtener_memoria(user_id)
    intencion = detectar_mejor_coincidencia(mensaje_limpio, INTENCIONES)

    # --- 0. REINICIO ---
    if 'reiniciar' in mensaje_limpio or 'salir' in mensaje_limpio:
        reset_memoria(user_id)
        return random.choice(FRASES_REINICIO)

    # --- 1. FLUJO DE NOMBRE (NUEVO) ---
    # Si no tenemos nombre guardado, preguntamos o capturamos
    nombre_usuario = memoria.get('nombre_usuario', '')

    # Caso A: Estamos esperando el nombre (paso 2)
    if memoria.get('esperando_nombre'):
        # Asumimos que el mensaje actual ES el nombre
        nombre_capturado = mensaje.strip().title() # Capitalizar (Juan Perez)
        # Guardamos en memoria
        memoria['nombre_usuario'] = nombre_capturado
        memoria['esperando_nombre'] = False # Ya no esperamos
        guardar_memoria(user_id, memoria)
        
        return f"¡Mucho gusto, **{nombre_capturado}**! 🎓 Ahora sí, ¿en qué te puedo ayudar? (Carreras, Costos, Ubicación...)"

    # Caso B: No tenemos nombre y es el primer mensaje (paso 1)
    if not nombre_usuario:
        # Activamos la espera
        memoria['esperando_nombre'] = True
        guardar_memoria(user_id, memoria)
        return "¡Hola! 👋 Soy AulaBot, tu asistente del ITSCH. Antes de empezar, ¿cómo te llamas?"

    # --- 2. SALUDO / AYUDA (Ya con nombre) ---
    if intencion == "ayuda" or intencion == "saludo":
        saludo_inicial = ""
        if intencion == "saludo":
            saludo_inicial = random.choice(FRASES_SALUDO_CON_NOMBRE).format(nombre=nombre_usuario) + "\n\n"

        menu_completo = (
            "🤖 **Menú de Capacidades**\n\n"
            "🎓 **Académico:** Carreras, Materias (ej: 'Materias de Sistemas').\n"
            "🏛️ **Institución:** Misión, Historia, Directorio.\n"
            "💵 **Admin:** Costos, Inscripción, Titulación, Becas.\n"
            "⚽ **Vida:** Deportes, Cafetería, Inglés.\n\n"
            "👇 **¡Dime qué necesitas, {nombre}!**".format(nombre=nombre_usuario)
        )
        return saludo_inicial + menu_completo
    
    # --- 3. LISTADO DE CARRERAS ---
    if intencion == "carreras_lista":
        lista = listar_carreras(carreras)
        return consultar_gemini(f"Las carreras son:\n{lista}", f"Dile a {nombre_usuario} la lista amablemente.")

    # --- 4. JEFE DE CARRERA ---
    if intencion == "jefes":
        posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
        if posible_carrera:
            info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
            if info and info.get('jefe_division'):
                return consultar_gemini(f"Jefe de {info['nombre']}: {info['jefe_division']}", f"Dile a {nombre_usuario} quién es el jefe.")
        return f"Para decirte el Jefe, necesito la carrera, {nombre_usuario} (ej: 'Jefe de Sistemas')."

    # --- 5. MATERIAS ---
    if intencion == "materias":
        posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
        if posible_carrera:
            memoria['carrera_seleccionada'] = posible_carrera
            memoria['modo_materias'] = True 
            guardar_memoria(user_id, memoria)
            
            res = materias_todas(posible_carrera, materias)
            frase = random.choice(FRASES_MATERIAS).format(carrera=posible_carrera, nombre=nombre_usuario) 
            return f"{frase}\n\n{res}\n\n(Filtra escribiendo el número de semestre)."
        
        return f"Para ver las materias, necesito la carrera, {nombre_usuario}. Ejemplo: **'Materias de Industrial'**."

    # --- 6. INFO DE CARRERA ---
    posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
    if posible_carrera:
        memoria['carrera_seleccionada'] = posible_carrera
        memoria['modo_materias'] = False
        guardar_memoria(user_id, memoria)
        
        info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
        if info:
            ctx = f"Carrera: {info['nombre']} ({info['clave']}). Jefe: {info.get('jefe_division','N/A')}. Descripción: {info['descripcion']}. Perfil: {info.get('perfil_ingreso','')}. Campo: {info.get('perfil_egreso','')}."
            return consultar_gemini(ctx, f"Presenta esta carrera a {nombre_usuario} y pregunta si quiere ver materias.")

    # --- 7. CONTEXTO ACTIVO ---
    if memoria.get('carrera_seleccionada'):
        carrera_sel = memoria['carrera_seleccionada']
        
        if intencion == "afirmacion" and not memoria.get('modo_materias'):
             memoria['modo_materias'] = True
             guardar_memoria(user_id, memoria)
             res = materias_todas(carrera_sel, materias)
             frase = random.choice(FRASES_MATERIAS).format(carrera=carrera_sel, nombre=nombre_usuario)
             return f"{frase}\n\n{res}"
        
        if intencion == "negacion":
            # No borramos el nombre, solo el contexto de la carrera
            del memoria['carrera_seleccionada']
            if 'modo_materias' in memoria: del memoria['modo_materias']
            guardar_memoria(user_id, memoria)
            return f"Entendido, {nombre_usuario}. Volvemos al inicio. ¿Qué más deseas consultar?"

        if memoria.get('modo_materias'):
            nums = re.findall(r'\d+', mensaje_limpio)
            if nums: return materias_por_semestre(carrera_sel, int(nums[0]), materias)
            
            nombres = [m['materia'] for m in materias if m['carrera'] == carrera_sel]
            match, score = process.extractOne(mensaje_limpio, nombres, scorer=fuzz.token_set_ratio) if nombres else (None, 0)
            if score > 75:
                m = next(x for x in materias if x['materia'] == match and x['carrera'] == carrera_sel)
                datos = f"Materia: {m['materia']}, Semestre: {m['semestre']}, Créditos: {m.get('horas','N/A')}."
                return consultar_gemini(datos, f"Explícale la materia a {nombre_usuario}.")

    # --- 8. GENERAL ---
    mejor_match, mejor_score = None, 0
    for item in general:
        score = fuzz.partial_ratio(limpiar_texto(item['palabra_clave']), mensaje_limpio)
        if score > mejor_score:
            mejor_score = score
            mejor_match = item['respuesta']
    
    if mejor_score > 85:
        return consultar_gemini(mejor_match, mensaje)

    # --- 9. FALLBACK ---
    registrar_ignorancia(mensaje_limpio) 
    prompt_fallback = f"Usuario {nombre_usuario} dice: '{mensaje}'. No hay dato oficial. Responde amable."
    try:
        if USAR_GEMINI: return consultar_gemini(prompt_fallback, mensaje)
    except: pass
    
    return random.choice(FRASES_NO_ENTENDI).format(nombre=nombre_usuario)