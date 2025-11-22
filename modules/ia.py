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
# 1. MAPA DE CONOCIMIENTO
# =========================================================
# (Tus diccionarios se mantienen igual para dar prioridad a la escuela)
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
    Eres AulaBot del ITSCH.
    INFORMACIÓN OFICIAL: "{contexto}"
    USUARIO: "{pregunta_usuario}"
    TAREA: Responde amable y profesionalmente usando SOLO la info oficial. 
    """
    try:
        return model.generate_content(prompt).text
    except: return contexto 

def consultar_gemini_general(pregunta_usuario):
    """
    LIBRE: Responde cualquier duda del mundo y la prepara para guardarse en memoria.
    """
    if not USAR_GEMINI: return None
    
    prompt = f"""
    Eres AulaBot, un asistente inteligente y útil.
    El usuario te pregunta: "{pregunta_usuario}"
    Esta pregunta NO es sobre datos específicos de la escuela, así que usa tu conocimiento general.
    Responde de forma breve, educativa y amable (máximo 3 párrafos).
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return None

# =========================================================
# 3. CEREBRO PRINCIPAL (AUTODIDACTA)
# =========================================================
def generar_respuesta(mensaje, user_id, general, carreras, materias):
    mensaje_limpio = limpiar_texto(mensaje)
    memoria = obtener_memoria(user_id)
    intencion = detectar_mejor_coincidencia(mensaje_limpio, INTENCIONES)

    # --- 0. REINICIO ---
    if 'reiniciar' in mensaje_limpio or 'salir' in mensaje_limpio:
        reset_memoria(user_id)
        return "🔄 Conversación reiniciada. ¿En qué te ayudo ahora?"

    # --- 1. MEMORIA ADQUIRIDA (LO QUE YA APRENDIÓ) ---
    # Antes de procesar nada, revisamos si ya aprendió esto antes
    conocimiento_json = cargar_conocimiento_adquirido()
    if conocimiento_json:
        # Buscamos si la pregunta actual se parece a algo que ya respondió Gemini antes
        mejor_pregunta_guardada, score = process.extractOne(mensaje, list(conocimiento_json.keys()), scorer=fuzz.token_sort_ratio) or (None, 0)
        if score > 85:
            return f"{conocimiento_json[mejor_pregunta_guardada]}"

    # --- 2. INTENCIÓN DE AYUDA / SALUDO ---
    if intencion == "ayuda" or intencion == "saludo":
        saludo_inicial = ""
        if intencion == "saludo":
            saludo_inicial = "¡Hola! 👋 Soy AulaBot.\n\n"

        menu_completo = (
            "🤖 **Menú de Capacidades**\n\n"
            "🎓 **Académico:** Carreras, Materias (ej: 'Materias de Sistemas').\n"
            "🏛️ **Institución:** Misión, Historia, Directorio.\n"
            "💵 **Admin:** Costos, Inscripción, Titulación, Becas.\n"
            "⚽ **Vida:** Deportes, Cafetería, Inglés.\n"
            "🧠 **Preguntas Generales:** ¡Pregúntame lo que sea! Si no sé, lo investigo y lo aprendo.\n\n"
            "👇 **¡Dime qué necesitas!**"
        )
        return saludo_inicial + menu_completo
    
    # --- 3. FLUJOS INSTITUCIONALES (PRIORIDAD ALTA) ---
    # (Aquí mantenemos tu lógica escolar perfecta que ya tenías)
    
    # Lista Carreras
    if intencion == "carreras_lista":
        lista = listar_carreras(carreras)
        return consultar_gemini_oficial(f"Las carreras son:\n{lista}", "Da la lista amablemente.")

    # Jefes
    if intencion == "jefes":
        posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
        if posible_carrera:
            info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
            if info and info.get('jefe_division'):
                return consultar_gemini_oficial(f"Jefe de {info['nombre']}: {info['jefe_division']}", "Dilo amable.")
        return "Para decirte el Jefe, necesito la carrera (ej: 'Jefe de Sistemas')."

    # Materias
    if intencion == "materias":
        posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
        if posible_carrera:
            memoria['carrera_seleccionada'] = posible_carrera
            memoria['modo_materias'] = True 
            guardar_memoria(user_id, memoria)
            res = materias_todas(posible_carrera, materias)
            return f"📂 **Plan de Estudios: {posible_carrera}**\n\n{res}\n\n(Filtra escribiendo el número de semestre)."
        return "Para ver las materias, dime de qué carrera (ej: 'Materias de Industrial')."

    # Info Carrera
    posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
    if posible_carrera:
        memoria['carrera_seleccionada'] = posible_carrera
        memoria['modo_materias'] = False
        guardar_memoria(user_id, memoria)
        info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
        if info:
            ctx = f"Carrera: {info['nombre']} ({info['clave']}). Jefe: {info.get('jefe_division','N/A')}. Descripción: {info['descripcion']}. Perfil: {info.get('perfil_ingreso','')}. Campo: {info.get('perfil_egreso','')}."
            return consultar_gemini_oficial(ctx, "Presenta esta carrera y pregunta si quiere ver materias.")

    # Contexto Activo
    if memoria.get('carrera_seleccionada'):
        carrera_sel = memoria['carrera_seleccionada']
        if intencion == "afirmacion" and not memoria.get('modo_materias'):
             memoria['modo_materias'] = True
             guardar_memoria(user_id, memoria)
             res = materias_todas(carrera_sel, materias)
             return f"📂 **Materias de {carrera_sel}:**\n\n{res}"
        
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
                return consultar_gemini_oficial(datos, "¿Qué onda con esta materia?")

    # General CSV
    mejor_match, mejor_score = None, 0
    for item in general:
        score = fuzz.partial_ratio(limpiar_texto(item['palabra_clave']), mensaje_limpio)
        if score > mejor_score:
            mejor_score = score
            mejor_match = item['respuesta']
    if mejor_score > 85:
        return consultar_gemini_oficial(mejor_match, mensaje)

    # --- 4. APRENDIZAJE AUTOMÁTICO (EL GRAN FINAL) ---
    # Si llegamos aquí, NO está en el CSV. Le preguntamos a Gemini General.
    
    respuesta_inteligente = consultar_gemini_general(mensaje)
    
    if respuesta_inteligente:
        # ¡ÉXITO! Gemini sabía la respuesta.
        # 1. Guardamos lo que aprendió en aprendido.json para que sea permanente
        guardar_nuevo_conocimiento(mensaje, respuesta_inteligente)
        
        # 2. Respondemos al usuario
        return respuesta_inteligente

    # --- 5. FALLBACK TOTAL (Si Gemini tampoco sabe) ---
    registrar_ignorancia(mensaje_limpio) 
    return "Mmm, esa no me la sé ni yo. 😅 Pero ya anoté tu duda para investigarla."