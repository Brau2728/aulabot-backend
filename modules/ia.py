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
FRASES_SALUDO = [
    "¡Hola, {nombre}! 👋 Soy AulaBot. ¿En qué te puedo echar la mano hoy?",
    "¡Qué tal, {nombre}! 🤖 Tu asistente del ITSCH listo. ¿Qué necesitas saber?",
    "¡Hola, hola, {nombre}! 😊 Aquí estoy para resolver tus dudas sobre el Tec.",
    "¡Buenas, {nombre}! 🎓 ¿Buscas información de alguna carrera o trámite?",
    "¡Hey, {nombre}! 👋 Cuéntame, ¿qué te interesa consultar?"
]

FRASES_MATERIAS = [
    "📂 ¡Listo, {nombre}! Aquí tienes el plan de estudios de **{carrera}**:",
    "📘 Checa las materias que se llevan en **{carrera}**, {nombre}:",
    "🎓 Estas son las asignaturas para **{carrera}**:",
    "📚 Desplegando la retícula de **{carrera}**. ¡Mira esto!:"
]

FRASES_NO_ENTENDI = [
    "Mmm, esa no me la sé ni yo, {nombre}. 😅 Pero ya anoté tu duda.",
    "¡Órale! Me corchaste con esa pregunta, {nombre}. 🤔",
    "Ese dato específico se me escapa por ahora. 🧐",
    "¡Vaya! No encontré eso en mi base de datos oficial ni en internet."
]

FRASES_REINICIO = [
    "🔄 Conversación reiniciada. ¡Empecemos de cero! ¿Cómo te llamas?",
    "🧹 Memoria borrada. Hola de nuevo, ¿me recuerdas tu nombre?",
    "Listo, borrón y cuenta nueva. 🔄 ¿Cuál es tu nombre?"
]

# =========================================================
# 1. MAPA DE CONOCIMIENTO
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
    # AQUÍ AGREGUÉ 'NORMATIVAS' y 'REGLAMENTO' 👇
    "institucional": ["mision", "vision", "objetivos", "historia", "fundacion", "normativas", "reglamento", "normas", "reglas"],
    "vida_estudiantil": ["deportes", "futbol", "cafeteria", "ingles", "centro de idiomas", "psicologia"],
    "afirmacion": ["si", "claro", "por favor", "yes", "simon", "ok", "va", "me parece"],
    "negacion": ["no", "nel", "asi dejalo", "gracias"]
}

# =========================================================
# 2. FUNCIONES DE INTELIGENCIA
# =========================================================
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

def consultar_gemini_oficial(contexto, pregunta_usuario):
    """RAG: Responde usando SOLO datos oficiales del CSV."""
    if not USAR_GEMINI: return contexto 
    
    prompt = f"""
    Actúa como AulaBot del ITSCH.
    Usa esta INFORMACIÓN OFICIAL para responder: "{contexto}"
    El usuario pregunta: "{pregunta_usuario}"
    Respuesta breve, amable y directa.
    """
    try:
        return model.generate_content(prompt).text
    except: return contexto 

def consultar_gemini_general(pregunta_usuario):
    """
    CEREBRO GENERAL: Responde cualquier duda del mundo.
    """
    if not USAR_GEMINI: return None
    
    prompt = f"""
    Eres un asistente útil y educativo.
    El usuario pregunta: "{pregunta_usuario}"
    Responde de forma clara, breve (máximo 3 párrafos) y amable.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return None

# =========================================================
# 3. LÓGICA PRINCIPAL (CEREBRO FINAL)
# =========================================================
def generar_respuesta(mensaje, user_id, general, carreras, materias):
    mensaje_limpio = limpiar_texto(mensaje)
    memoria = obtener_memoria(user_id)
    intencion = detectar_mejor_coincidencia(mensaje_limpio, INTENCIONES)

    # --- 0. REINICIO ---
    if 'reiniciar' in mensaje_limpio or 'salir' in mensaje_limpio:
        reset_memoria(user_id)
        return random.choice(FRASES_REINICIO)

    # --- 1. FLUJO DE NOMBRE (PRIORIDAD MÁXIMA) ---
    nombre_usuario = memoria.get('nombre_usuario', '')

    if memoria.get('esperando_nombre'):
        nombre_capturado = mensaje.strip().title()
        memoria['nombre_usuario'] = nombre_capturado
        memoria['esperando_nombre'] = False
        guardar_memoria(user_id, memoria)
        return f"¡Mucho gusto, **{nombre_capturado}**! 🎓 Ya guardé tu nombre. Ahora sí, ¿en qué te ayudo? (Carreras, Materias, Costos...)"

    if not nombre_usuario:
        memoria['esperando_nombre'] = True
        guardar_memoria(user_id, memoria)
        return "¡Hola! 👋 Soy AulaBot, tu asistente del ITSCH. Antes de empezar, ¿cómo te llamas?"

    # --- 2. MEMORIA ADQUIRIDA (AUTODIDACTA) ---
    conocimiento_json = cargar_conocimiento_adquirido()
    if conocimiento_json:
        mejor_pregunta_guardada, score = process.extractOne(mensaje, list(conocimiento_json.keys()), scorer=fuzz.token_sort_ratio) or (None, 0)
        if score > 85:
            return f"{conocimiento_json[mejor_pregunta_guardada]}"

    # --- 3. SALUDO / AYUDA ---
    if intencion == "ayuda" or intencion == "saludo":
        saludo_inicial = ""
        if intencion == "saludo":
            frase = random.choice(FRASES_SALUDO).format(nombre=nombre_usuario)
            saludo_inicial = f"{frase}\n\n"

        menu_completo = (
            "🤖 **Menú de Capacidades**\n\n"
            "🎓 **Académico:** Carreras, Materias (ej: 'Materias de Sistemas').\n"
            "🏛️ **Institución:** Misión, Historia, Normativas.\n"
            "💵 **Admin:** Costos, Inscripción, Titulación, Becas.\n"
            "⚽ **Vida:** Deportes, Cafetería, Inglés.\n"
            "🧠 **Preguntas Generales:** ¡Pregúntame lo que sea! Si no sé, lo investigo.\n\n"
            f"👇 **¡Dime qué necesitas, {nombre_usuario}!**"
        )
        return saludo_inicial + menu_completo
    
    # --- 4. LISTADO DE CARRERAS ---
    if intencion == "carreras_lista":
        lista = listar_carreras(carreras)
        return consultar_gemini_oficial(f"Las carreras son:\n{lista}", f"Dile a {nombre_usuario} la lista amablemente.")

    # --- 5. JEFES ---
    if intencion == "jefes":
        posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
        if posible_carrera:
            info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
            if info and info.get('jefe_division'):
                return consultar_gemini_oficial(f"Jefe de {info['nombre']}: {info['jefe_division']}", f"Dile a {nombre_usuario} quién es.")
        return f"Para decirte el Jefe, dime de qué carrera, {nombre_usuario} (ej: 'Jefe de Sistemas')."

    # --- 6. MATERIAS ---
    if intencion == "materias":
        posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
        if posible_carrera:
            memoria['carrera_seleccionada'] = posible_carrera
            memoria['modo_materias'] = True 
            guardar_memoria(user_id, memoria)
            res = materias_todas(posible_carrera, materias)
            
            frase = random.choice(FRASES_MATERIAS).format(nombre=nombre_usuario, carrera=posible_carrera)
            return f"{frase}\n\n{res}\n\n(Filtra escribiendo el número de semestre)."
        return f"Para ver las materias, dime la carrera, {nombre_usuario}. (Ej: 'Materias de Industrial')."

    # --- 7. INFO CARRERA ---
    posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
    if posible_carrera:
        memoria['carrera_seleccionada'] = posible_carrera
        memoria['modo_materias'] = False
        guardar_memoria(user_id, memoria)
        info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
        if info:
            ctx = f"Carrera: {info['nombre']} ({info['clave']}). Jefe: {info.get('jefe_division','N/A')}. Descripción: {info['descripcion']}. Perfil: {info.get('perfil_ingreso','')}. Campo: {info.get('perfil_egreso','')}."
            return consultar_gemini_oficial(ctx, f"Presenta esta carrera a {nombre_usuario} y pregunta si quiere ver materias.")

    # --- 8. CONTEXTO ACTIVO ---
    if memoria.get('carrera_seleccionada'):
        carrera_sel = memoria['carrera_seleccionada']
        
        if intencion == "afirmacion" and not memoria.get('modo_materias'):
             memoria['modo_materias'] = True
             guardar_memoria(user_id, memoria)
             res = materias_todas(carrera_sel, materias)
             frase = random.choice(FRASES_MATERIAS).format(nombre=nombre_usuario, carrera=carrera_sel)
             return f"{frase}\n\n{res}"
        
        if intencion == "negacion":
            del memoria['carrera_seleccionada']
            if 'modo_materias' in memoria: del memoria['modo_materias']
            guardar_memoria(user_id, memoria)
            return f"Entendido, {nombre_usuario}. ¿Qué más deseas consultar?"

        if memoria.get('modo_materias'):
            nums = re.findall(r'\d+', mensaje_limpio)
            if nums: return materias_por_semestre(carrera_sel, int(nums[0]), materias)
            
            nombres = [m['materia'] for m in materias if m['carrera'] == carrera_sel]
            match, score = process.extractOne(mensaje_limpio, nombres, scorer=fuzz.token_set_ratio) if nombres else (None, 0)
            if score > 75:
                m = next(x for x in materias if x['materia'] == match and x['carrera'] == carrera_sel)
                datos = f"Materia: {m['materia']}, Semestre: {m['semestre']}, Créditos: {m.get('horas','N/A')}."
                return consultar_gemini_oficial(datos, f"Explícale la materia a {nombre_usuario}.")

    # --- 9. GENERAL (CSV) ---
    mejor_match, mejor_score = None, 0
    for item in general:
        score = fuzz.partial_ratio(limpiar_texto(item['palabra_clave']), mensaje_limpio)
        if score > mejor_score:
            mejor_score = score
            mejor_match = item['respuesta']
    if mejor_score > 85:
        return consultar_gemini_oficial(mejor_match, mensaje)

    # --- 10. APRENDIZAJE AUTOMÁTICO ---
    respuesta_inteligente = consultar_gemini_general(mensaje)
    if respuesta_inteligente:
        guardar_nuevo_conocimiento(mensaje, respuesta_inteligente)
        return respuesta_inteligente

    # --- 11. FALLBACK TOTAL ---
    registrar_ignorancia(mensaje_limpio) 
    frase_error = random.choice(FRASES_NO_ENTENDI).format(nombre=nombre_usuario)
    return f"{frase_error}"