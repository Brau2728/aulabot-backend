import google.generativeai as genai
from modules.funciones import listar_carreras, materias_por_semestre, materias_todas, registrar_ignorancia, cargar_conocimiento_adquirido, guardar_nuevo_conocimiento
from modules.memoria import obtener_memoria, guardar_memoria, reset_memoria
from thefuzz import process, fuzz 
import unicodedata
import re
import random
import os

# =========================================================
# 1. CONFIGURACIÓN DE GEMINI
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
# 2. BANCO DE FRASES (PERSONALIDAD)
# =========================================================
FRASES_SALUDO = [
    "¡Hola! 👋 Soy AulaBot. ¿En qué te puedo echar la mano hoy?",
    "¡Qué tal! 🤖 Tu asistente del ITSCH listo. ¿Qué necesitas saber?",
    "¡Hola, hola! 😊 Aquí estoy para resolver tus dudas sobre el Tec.",
    "¡Buenas! 🎓 ¿Buscas información de alguna carrera o trámite?",
    "¡Hey! 👋 Soy AulaBot. Cuéntame, ¿qué te interesa consultar?"
]

FRASES_MATERIAS = [
    "📂 ¡Listo! Aquí tienes el plan de estudios de **{carrera}**:",
    "📘 Checa las materias que se llevan en **{carrera}**:",
    "🎓 Estas son las asignaturas para **{carrera}**:",
    "📚 Desplegando la retícula de **{carrera}**. ¡Mira esto!:"
]

FRASES_NO_ENTENDI = [
    "Mmm, esa no me la sé todavía. 😅 Pero ya anoté tu duda para investigarla.",
    "¡Órale! Me corchaste con esa pregunta. 🤔 Intenta decirme el nombre de una carrera.",
    "No estoy seguro de qué hablas. 🤷‍♂️ Prueba preguntando por 'Costos' o 'Sistemas'.",
    "Ese dato se me escapa. 🧐 ¿Podrías ser más específico? Quizás buscas 'Ubicación' o 'Becas'."
]

FRASES_REINICIO = [
    "🔄 Conversación reiniciada. ¡Empecemos de cero! ¿Qué necesitas?",
    "🧹 Memoria borrada. ¿De qué quieres hablar ahora?",
    "Listo, borrón y cuenta nueva. 🔄 ¿En qué te ayudo?",
    "Entendido. Reiniciamos la charla. ¿Qué más te interesa?"
]

# =========================================================
# 3. MAPA DE CONOCIMIENTO
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

# =========================================================
# 4. FUNCIONES AUXILIARES
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

def consultar_gemini(contexto, pregunta_usuario):
    if not USAR_GEMINI: return contexto 
    prompt = f"""
    Eres AulaBot, el asistente virtual amigable del ITSCH.
    INFORMACIÓN OFICIAL (Contexto): "{contexto}"
    USUARIO DICE: "{pregunta_usuario}"
    TU TAREA: Responde al usuario basándote EXCLUSIVAMENTE en la Información Oficial. 
    - Sé amable, usa emojis 🎓✨. Si es una lista, mantenla ordenada.
    """
    try:
        response = genai.GenerativeModel('gemini-pro').generate_content(prompt)
        return response.text
    except: return contexto 

# =========================================================
# 5. LÓGICA PRINCIPAL (CEREBRO)
# =========================================================
def generar_respuesta(mensaje, user_id, general, carreras, materias):
    mensaje_limpio = limpiar_texto(mensaje)
    memoria = obtener_memoria(user_id)
    intencion = detectar_mejor_coincidencia(mensaje_limpio, INTENCIONES)

    # --- BLOQUE 1: Reinicio ---
    if 'reiniciar' in mensaje_limpio or 'salir' in mensaje_limpio:
        reset_memoria(user_id)
        return random.choice(FRASES_REINICIO)

    # --- BLOQUE 2: Ayuda / Saludo (Con variabilidad) ---
    if intencion == "ayuda" or intencion == "saludo":
        saludo_inicial = ""
        if intencion == "saludo":
            saludo_inicial = random.choice(FRASES_SALUDO) + "\n\n"

        menu_completo = (
            "🤖 **Menú de Capacidades**\n\n"
            "🎓 **Académico:** Carreras, Materias (ej: 'Materias de Sistemas').\n"
            "🏛️ **Institución:** Misión, Historia, Directorio.\n"
            "💵 **Admin:** Costos, Inscripción, Titulación, Becas.\n"
            "⚽ **Vida:** Deportes, Cafetería, Inglés.\n\n"
            "👇 **¡Toca una opción o escribe tu duda!**"
        )
        return saludo_inicial + menu_completo
    
    # --- BLOQUE 3: Lista de Carreras ---
    if intencion == "carreras_lista":
        lista = listar_carreras(carreras)
        return consultar_gemini(f"Las carreras son:\n{lista}", "Da la lista amablemente.")

    # --- BLOQUE 4: Jefe de Carrera ---
    if intencion == "jefes":
        posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
        if posible_carrera:
            info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
            if info and info.get('jefe_division'):
                return consultar_gemini(f"Jefe de {info['nombre']}: {info['jefe_division']}", "Dilo amable.")
        return "Para decirte el Jefe, necesito la carrera (ej: 'Jefe de Sistemas')."

    # --- BLOQUE 5: Materias (Flujo Directo) ---
    if intencion == "materias":
        posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
        if posible_carrera:
            memoria['carrera_seleccionada'] = posible_carrera
            memoria['modo_materias'] = True 
            guardar_memoria(user_id, memoria)
            
            res = materias_todas(posible_carrera, materias)
            # Aquí usamos la frase variable
            frase = random.choice(FRASES_MATERIAS).format(carrera=posible_carrera) 
            return f"{frase}\n\n{res}\n\n(Filtra escribiendo el número de semestre)."
        
        return "Para ver las materias, necesito la carrera. Ejemplo: **'Materias de Industrial'**."

    # --- BLOQUE 6: Info General de Carrera ---
    posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
    if posible_carrera:
        memoria['carrera_seleccionada'] = posible_carrera
        memoria['modo_materias'] = False
        guardar_memoria(user_id, memoria)
        
        info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
        if info:
            ctx = f"Carrera: {info['nombre']} ({info['clave']}). Jefe: {info.get('jefe_division','N/A')}. Descripción: {info['descripcion']}. Perfil: {info.get('perfil_ingreso','')}. Campo: {info.get('perfil_egreso','')}."
            return consultar_gemini(ctx, "Presenta esta carrera y pregunta si quiere ver materias.")

    # --- BLOQUE 7: Contexto Activo (Ya eligió carrera) ---
    if memoria.get('carrera_seleccionada'):
        carrera_sel = memoria['carrera_seleccionada']
        
        if intencion == "afirmacion" and not memoria.get('modo_materias'):
             memoria['modo_materias'] = True
             guardar_memoria(user_id, memoria)
             res = materias_todas(carrera_sel, materias)
             frase = random.choice(FRASES_MATERIAS).format(carrera=carrera_sel)
             return f"{frase}\n\n{res}"
        
        if intencion == "negacion":
            reset_memoria(user_id)
            return "Entendido. Volvemos al inicio. ¿Qué más deseas consultar?"

        if memoria.get('modo_materias'):
            nums = re.findall(r'\d+', mensaje_limpio)
            if nums: return materias_por_semestre(carrera_sel, int(nums[0]), materias)
            
            nombres = [m['materia'] for m in materias if m['carrera'] == carrera_sel]
            match, score = process.extractOne(mensaje_limpio, nombres, scorer=fuzz.token_set_ratio) if nombres else (None, 0)
            if score > 75:
                m = next(x for x in materias if x['materia'] == match and x['carrera'] == carrera_sel)
                datos = f"Materia: {m['materia']}, Semestre: {m['semestre']}, Créditos: {m.get('horas','N/A')}."
                return consultar_gemini(datos, "¿Qué onda con esta materia?")

    # --- BLOQUE 8: Búsqueda General (CSV) ---
    mejor_match, mejor_score = None, 0
    for item in general:
        score = fuzz.partial_ratio(limpiar_texto(item['palabra_clave']), mensaje_limpio)
        if score > mejor_score:
            mejor_score = score
            mejor_match = item['respuesta']
    
    if mejor_score > 85:
        return consultar_gemini(mejor_match, mensaje)

    # --- BLOQUE 9: Fallback (Gemini Puro + Frase Variable) ---
    registrar_ignorancia(mensaje_limpio) 
    prompt_fallback = f"Usuario dice: '{mensaje}'. No hay dato oficial. Responde amable si es saludo. Si no sabes, di que consultarás en escolares."
    try:
        if USAR_GEMINI: return consultar_gemini(prompt_fallback, mensaje)
    except: pass
    
    return random.choice(FRASES_NO_ENTENDI)