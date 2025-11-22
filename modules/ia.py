import google.generativeai as genai
from modules.funciones import listar_carreras, materias_por_semestre, materias_todas, registrar_ignorancia
from modules.memoria import obtener_memoria, guardar_memoria, reset_memoria
from thefuzz import process, fuzz 
import unicodedata
import re
import os

# =========================================================
# 🤖 CONFIGURACIÓN DE GEMINI (GOOGLE AI)
# =========================================================
# Asegúrate de que GEMINI_API_KEY esté configurada en Render
API_KEY = os.getenv("GEMINI_API_KEY") 

try:
    if API_KEY:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        USAR_GEMINI = True
    else:
        USAR_GEMINI = False
except Exception as e:
    # Captura cualquier error de conexión a la API
    USAR_GEMINI = False

# =========================================================
# 1. Mapa de Conocimiento (Sinónimos de Carreras e Intenciones)
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
    "afirmacion": ["si", "claro", "por favor", "yes", "simon", "ok", "va", "me parece"], # Corrección: Añadir "si" y "no"
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
    """
    Función RAG: Pasa el contexto recuperado del CSV a Gemini para generar una respuesta amable.
    """
    if not USAR_GEMINI:
        return contexto 

    prompt = f"""
    Eres AulaBot, el asistente virtual amigable del Instituto Tecnológico Superior de Ciudad Hidalgo (ITSCH).
    INFORMACIÓN OFICIAL (Contexto):
    "{contexto}"
    USUARIO DICE:
    "{pregunta_usuario}"
    TU TAREA:
    Responde al usuario basándote EXCLUSIVAMENTE en la Información Oficial. 
    - Sé amable, usa emojis 🎓✨. Si es una lista o info crítica (costos, trámites), mantenla muy clara y legible.
    """
    try:
        response = genai.GenerativeModel('gemini-pro').generate_content(prompt)
        return response.text
    except Exception as e:
        return contexto 

# =========================================================
# 3. Lógica Principal (Función generar_respuesta)
# =========================================================
def generar_respuesta(mensaje, user_id, general, carreras, materias):
    mensaje_limpio = limpiar_texto(mensaje)
    memoria = obtener_memoria(user_id)
    intencion = detectar_mejor_coincidencia(mensaje_limpio, INTENCIONES)

    # --- Comandos de Reinicio ---
    if 'reiniciar' in mensaje_limpio or 'salir' in mensaje_limpio:
        reset_memoria(user_id)
        return "🔄 Conversación reiniciada. ¿En qué te ayudo ahora?"
        
    # --- 1. INTENCIÓN DE AYUDA / SALUDO ---
    if intencion == "ayuda" or intencion == "saludo": 
        if intencion == "saludo":
            saludo = "¡Hola! Soy AulaBot, tu asistente del ITSCH. ¿En qué te puedo ayudar hoy? 😊"
        else:
            saludo = ""
            
        menu = (
            "🤖 **Menú de Capacidades AulaBot**\n\n"
            # ... (menú omitido por brevedad, usa la estructura del último mensaje) ...
            "¡Dime cuál es tu duda!"
        )
        return saludo + ("\n" if saludo else "") + menu
    
    # --- 2. LISTADO DE CARRERAS ---
    if intencion == "carreras_lista":
        lista = listar_carreras(carreras)
        respuesta = f"¡Claro! El ITSCH ofrece las siguientes carreras:\n\n{lista}\n\nEscribe el **nombre de la carrera** (ej: 'Sistemas', 'Nano') para conocer sus detalles."
        return consultar_gemini(respuesta, "Responde la lista de carreras de forma amable.")


    # --- 3. BÚSQUEDA DE JEFE DE CARRERA ESPECÍFICO ---
    if intencion == "jefes":
        posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
        
        if posible_carrera:
            info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
            if info and info.get('jefe_division'):
                respuesta_jefe = f"El Jefe de División de {info['nombre']} es: {info['jefe_division']}."
                return consultar_gemini(respuesta_jefe, "Responde este dato de Directorio de forma amable y directa.")
        
        return "Para decirte quién es el Jefe, necesito saber de qué carrera me hablas (ej: 'Jefe de Sistemas') o pregunta por el Director General. 🏛️"

    # --- 4. PREGUNTA COMPUESTA: MATERIAS + CARRERA (Inicia el flujo) ---
    if intencion == "materias":
        posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
        if posible_carrera:
            memoria['carrera_seleccionada'] = posible_carrera
            memoria['modo_materias'] = True 
            guardar_memoria(user_id, memoria)
            
            respuesta_materias = materias_todas(posible_carrera, materias)
            return f"📂 ¡Aquí tienes **TODAS** las materias de **{posible_carrera}**!:\n\n{respuesta_materias}\n\nSi quieres filtrar por semestre, solo escribe el número (ej: '5') o dime el nombre de una materia."
        
        return "Para ver las materias, dime de qué carrera hablamos (ej: 'Materias de Industrial')."


    # --- 5. Información de Carreras (Nueva Selección - Descripción y Jefe) ---
    posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
    if posible_carrera:
        memoria['carrera_seleccionada'] = posible_carrera
        memoria['modo_materias'] = False # Inicialmente no está en modo materias
        guardar_memoria(user_id, memoria)
        
        info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
        if info:
            contexto_carrera = (
                f"Carrera: {info['nombre']} ({info['clave']}). "
                f"Jefe de División: {info.get('jefe_division', 'N/A')}. "
                f"Descripción: {info['descripcion']}. "
                f"Perfil Ingreso: {info.get('perfil_ingreso', '')}. "
                f"Campo Laboral: {info.get('perfil_egreso', '')}."
            )
            # Pregunta si quiere ver todas las materias.
            return consultar_gemini(contexto_carrera, "Háblame de esta carrera (descripción, jefe y perfiles) y pregúntame si quiere ver **TODAS** sus materias.")

    # -------------------------------------------------------------------------
    # --- 6. CONTEXTO ACTIVO (Manejo de Respuestas de Seguimiento y Filtros) ---
    # -------------------------------------------------------------------------
    if memoria.get('carrera_seleccionada'):
        carrera_sel = memoria['carrera_seleccionada']
        
        # Corrección 1: Manejar 'SI' para activar modo_materias
        if intencion == "afirmacion":
            if not memoria.get('modo_materias'):
                 memoria['modo_materias'] = True
                 guardar_memoria(user_id, memoria)
                 
                 respuesta_materias = materias_todas(carrera_sel, materias)
                 return f"📂 ¡Aquí tienes **TODAS** las materias de **{carrera_sel}**!:\n\n{respuesta_materias}\n\nSi quieres filtrar por semestre, solo escribe el número (ej: '5') o dime el nombre de una materia."
            
        # Corrección 2: Manejar 'NO' para resetear
        if intencion == "negacion":
            reset_memoria(user_id)
            return "De acuerdo, volvemos al menú principal. ¿Qué más te interesa?"
            
        # Lógica de búsqueda de semestre/materia (solo si ya estamos en modo_materias)
        if memoria.get('modo_materias'):
            # Búsqueda por número de semestre
            nums = re.findall(r'\d+', mensaje_limpio)
            if nums:
                return materias_por_semestre(carrera_sel, int(nums[0]), materias)
            
            # Búsqueda materia específica por nombre
            nombres = [m['materia'] for m in materias if m['carrera'] == carrera_sel]
            match, score = process.extractOne(mensaje_limpio, nombres, scorer=fuzz.token_set_ratio) if nombres else (None, 0)
            
            if score > 75:
                m = next(x for x in materias if x['materia'] == match and x['carrera'] == carrera_sel)
                datos_crudos = f"Materia: {m['materia']}, Clave: {m['clave']}, Semestre: {m['semestre']}, Créditos: {m.get('horas','N/A')}."
                return consultar_gemini(datos_crudos, "¿Qué onda con esta materia?")
            
            # Corrección 3: Fallback específico de materias si no entiende el filtro
            return f"🤔 No encontré esa materia. ¿Qué número de semestre de {carrera_sel} quieres consultar, o dime 'todas'?" 

    # --- 7. Preguntas Generales (CSV General -> Gemini) ---
    mejor_match_general = None
    mejor_score_general = 0
    
    for item in general:
        score = fuzz.token_set_ratio(limpiar_texto(item['palabra_clave']), mensaje_limpio)
        if score > mejor_score_general:
            mejor_score_general = score
            mejor_match_general = item['respuesta']
    
    if mejor_score_general > 85:
        return consultar_gemini(mejor_match_general, mensaje)

    # --- 8. Fallback (Gemini Puro) ---
    registrar_ignorancia(mensaje_limpio) 
    
    prompt_fallback = f"Eres AulaBot del ITSCH. El usuario dijo: '{mensaje}'. No encontraste información específica en tu base de datos oficial. Responde amablemente. Si es una pregunta técnica de la escuela que NO sabes, di: 'Ese dato específico no lo tengo a la mano, pero puedo averiguarlo en Servicios Escolares.'"
    try:
        if USAR_GEMINI:
            return consultar_gemini(prompt_fallback, mensaje)
    except:
        pass

    return "Mmm, esa no me la sé todavía. 😅 Pero ya anoté tu duda para investigarla."