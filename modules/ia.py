import google.generativeai as genai
from modules.funciones import listar_carreras, materias_por_semestre, materias_todas, registrar_ignorancia, cargar_conocimiento_adquirido, guardar_nuevo_conocimiento
from modules.memoria import obtener_memoria, guardar_memoria, reset_memoria, actualizar_conversacion
from thefuzz import process, fuzz 
import unicodedata
import re
import random
import os

# =========================================================
# 🤖 CONFIGURACIÓN DE GEMINI (GOOGLE AI)
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
# 1. Mapa de Conocimiento
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
    "materias": ["materias", "materia", "clases", "asignaturas", "reticula", "plan", "curricula", "qué lleva", "qué se estudia", "plan de estudios"],
    "carreras_lista": ["carreras", "programas academicos", "que carreras tienen", "cuales son las carreras", "qué ingenierías", "opciones de estudio"],
    "jefes": ["jefe de carrera", "jefe de division", "quien es el jefe", "director de carrera", "coordinador"], 
    "costos": ["cuanto cuesta", "precio", "costo", "pagar", "inscripcion", "mensualidad", "dinero", "ficha", "pago", "colegiatura"],
    "ubicacion": ["donde estan", "ubicacion", "mapa", "direccion", "llegar", "localizacion", "domicilio", "donde queda"],
    "saludo": ["hola", "buenos dias", "buenas", "que tal", "hey", "hi", "inicio", "comenzar", "buenas tardes", "buenas noches"],
    "directorio": ["director", "jefe", "coordinador", "quien es", "encargado", "subdirector", "autoridades"],
    "tramites": ["admision", "propedeutico", "examen", "becas", "servicio social", "residencias", "titulacion", "fechas", "convocatoria", "trámites"],
    "ayuda": ["que sabes hacer", "que puedes hacer", "ayuda", "instrucciones", "para que sirves", "menu", "opciones", "temas", "qué preguntar"],
    "institucional": ["mision", "vision", "objetivos", "historia", "fundacion", "valores", "filosofia"],
    "vida_estudiantil": ["deportes", "futbol", "cafeteria", "ingles", "centro de idiomas", "psicologia", "actividades", "clubes"],
    "afirmacion": ["si", "claro", "por favor", "yes", "simon", "ok", "va", "me parece", "correcto", "adelante"],
    "negacion": ["no", "nel", "asi dejalo", "gracias", "no gracias", "en otro momento"]
}

# =========================================================
# 2. Sistema de Respuestas Naturales
# =========================================================
RESPUESTAS_AFIRMATIVAS = [
    "¡Claro! Aquí tienes...",
    "Perfecto, te muestro...", 
    "¡Excelente! Aquí está...",
    "De acuerdo, aquí lo tienes...",
    "¡Genial! Esta es la información...",
    "Por supuesto, aquí está lo que necesitas...",
    "¡Listo! Te comparto la información..."
]

RESPUESTAS_NEGATIVAS = [
    "De acuerdo, ¿en qué más puedo ayudarte?",
    "Entendido, dime qué otra cosa necesitas saber",
    "¡Claro! Cambiemos de tema, ¿qué te interesa?",
    "Perfecto, ¿qué otro tema quieres consultar?",
    "No hay problema, estoy aquí para lo que necesites",
    "Como prefieras, ¿en qué otro aspecto te puedo orientar?"
]

TRANSICIONES_TEMA = [
    "\n\n¿Necesitas algo más sobre este tema?",
    "\n\n¿Te quedó claro? Puedes preguntarme más detalles.",
    "\n\n¿En qué más puedo orientarte sobre esto?",
    "\n\n¿Hay algo específico que quieras saber más?",
    "\n\n¿Te ayudo con algo más relacionado?"
]

def obtener_respuesta_afirmativa():
    return random.choice(RESPUESTAS_AFIRMATIVAS)

def obtener_respuesta_negativa():
    return random.choice(RESPUESTAS_NEGATIVAS)

def obtener_transicion():
    return random.choice(TRANSICIONES_TEMA)

# =========================================================
# 3. Funciones Auxiliares Mejoradas
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
    return mejor_opcion if mejor_score >= 65 else None  # Bajamos el threshold para mayor flexibilidad

def consultar_gemini(contexto, pregunta_usuario):
    if not USAR_GEMINI:
        return contexto 

    prompt = f"""
    Eres AulaBot, el asistente virtual amigable del ITSCH.
    INFORMACIÓN OFICIAL (Contexto):
    "{contexto}"
    USUARIO DICE:
    "{pregunta_usuario}"
    
    TU TAREA:
    Responde al usuario basándote EXCLUSIVAMENTE en la Información Oficial. 
    - Sé amable, natural y conversacional
    - Usa emojis apropiados 🎓✨🤔
    - Si es una lista o info crítica (costos, trámites), mantenla clara y legible
    - Responde como si estuvieras teniendo una conversación normal
    """
    try:
        response = genai.GenerativeModel('gemini-pro').generate_content(prompt)
        return response.text
    except Exception as e:
        return contexto

def detectar_intenciones_multiples(mensaje_limpio):
    """Detecta múltiples intenciones en un mensaje"""
    intenciones_detectadas = []
    for intencion, palabras in INTENCIONES.items():
        if any(palabra in mensaje_limpio for palabra in palabras):
            intenciones_detectadas.append(intencion)
    return intenciones_detectadas

def detectar_semestre_natural(mensaje_limpio):
    """Detecta números de semestre en texto natural"""
    numeros_texto = {
        'primero': 1, 'segundo': 2, 'tercero': 3, 'cuarto': 4, 
        'quinto': 5, 'sexto': 6, 'séptimo': 7, 'octavo': 8, 'noveno': 9,
        '1ro': 1, '2do': 2, '3ro': 3, '4to': 4, '5to': 5, '6to': 6, '7mo': 7, '8vo': 8, '9no': 9
    }
    
    # Buscar en texto
    for texto, num in numeros_texto.items():
        if texto in mensaje_limpio:
            return num
    
    # Buscar números
    nums = re.findall(r'\d+', mensaje_limpio)
    if nums:
        return int(nums[0])
    
    return None

# =========================================================
# 4. Lógica Principal Mejorada
# =========================================================
def generar_respuesta(mensaje, user_id, general, carreras, materias):
    mensaje_limpio = limpiar_texto(mensaje)
    memoria = obtener_memoria(user_id)
    intencion = detectar_mejor_coincidencia(mensaje_limpio, INTENCIONES)
    intenciones_multiples = detectar_intenciones_multiples(mensaje_limpio)

    # --- Comandos de Reinicio ---
    if any(palabra in mensaje_limpio for palabra in ['reiniciar', 'salir', 'empezar de nuevo', 'otra vez']):
        reset_memoria(user_id)
        return "🔄 Conversación reiniciada. ¿En qué te ayudo ahora?"

    # --- Manejo de Múltiples Intenciones ---
    if len(intenciones_multiples) > 1:
        if "saludo" in intenciones_multiples:
            # Quitar saludo para manejar la otra intención
            intenciones_multiples.remove("saludo")
            if intenciones_multiples:
                respuesta = "¡Hola! 👋 Veo que tienes varias preguntas. "
                respuesta += "Para darte la mejor respuesta, vamos de una a la vez. "
                respuesta += f"¿Podrías contarme más sobre lo que necesitas saber de {' o '.join(intenciones_multiples)}?"
                actualizar_conversacion(user_id, mensaje, respuesta)
                return respuesta

    # --- 1. INTENCIÓN DE AYUDA (MENÚ MEJORADO) ---
    if intencion == "ayuda":
        respuesta = (
            "¡Hola! Soy AulaBot 🤖, tu asistente del ITSCH. Puedo ayudarte con:\n\n"
            "🎓 **Información académica:**\n"
            "   - Carreras disponibles y sus detalles\n"  
            "   - Planes de estudio y materias\n"
            "   - Horarios y créditos\n\n"
            "🏛️ **Información general:**\n"
            "   - Costos y trámites\n"
            "   - Directorio de personal\n"
            "   - Misión y visión\n\n"
            "💡 **Solo pregúntame cosas como:**\n"
            "   - '¿Qué carreras tienen?'\n"
            "   - 'Cuéntame de Sistemas Computacionales'\n" 
            "   - '¿Qué materias lleva Mecatrónica?'\n"
            "   - '¿Cuánto cuesta la inscripción?'\n\n"
            "¿Por dónde quieres empezar? 😊"
        )
        actualizar_conversacion(user_id, mensaje, respuesta)
        return respuesta
    
    # --- 2. SALUDO NATURAL ---
    if intencion == "saludo":
        saludos = [
            "¡Hola! 👋 Soy AulaBot, tu asistente del ITSCH. ¿En qué puedo ayudarte hoy?",
            "¡Buenas! 🤖 ¿Qué te gustaría saber sobre el ITSCH?",
            "¡Hola! 🎓 Estoy aquí para resolver tus dudas sobre el instituto. ¿Por dónde empezamos?",
            "¡Hey! 👋 ¿En qué puedo orientarte hoy?"
        ]
        respuesta = random.choice(saludos)
        actualizar_conversacion(user_id, mensaje, respuesta)
        return respuesta
    
    # --- 3. LISTADO DE CARRERAS MEJORADO ---
    if intencion == "carreras_lista":
        lista = listar_carreras(carreras)
        respuesta_base = f"¡Claro! El ITSCH ofrece estas ingenierías:\n\n{lista}\n\n¿Te interesa conocer más sobre alguna en particular? Solo dime su nombre (ej: 'Sistemas', 'Mecatrónica')."
        respuesta_final = consultar_gemini(respuesta_base, "Responde de forma amable y entusiasta sobre las carreras disponibles.")
        actualizar_conversacion(user_id, mensaje, respuesta_final)
        return respuesta_final

    # --- 4. BÚSQUEDA DE JEFE DE CARRERA ESPECÍFICO ---
    if intencion == "jefes":
        posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
        
        if posible_carrera:
            info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
            if info and info.get('jefe_division'):
                respuesta_jefe = f"El Jefe de División de {info['nombre']} es: {info['jefe_division']}."
                respuesta_final = consultar_gemini(respuesta_jefe, "Responde este dato de Directorio de forma amable y directa.")
                actualizar_conversacion(user_id, mensaje, respuesta_final)
                return respuesta_final
        
        respuesta = "Para decirte quién es el Jefe, necesito saber de qué carrera me hablas. Por ejemplo: 'Jefe de Sistemas' o 'Quién es el jefe de Industrial' 🏛️"
        actualizar_conversacion(user_id, mensaje, respuesta)
        return respuesta

    # --- 5. INFORMACIÓN DE CARRERAS (CONVERSACIONAL) ---
    posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
    if posible_carrera:
        memoria['carrera_seleccionada'] = posible_carrera
        memoria['modo_materias'] = False
        guardar_memoria(user_id, memoria)
        
        info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
        if info:
            # Respuesta más conversacional y natural
            contexto_carrera = (
                f"¡Excelente elección! 🎓 **{info['nombre']}** ({info['clave']})\n\n"
                f"📖 **Qué aprenderás:** {info['descripcion']}\n\n"
                f"👨‍🏫 **Jefe de división:** {info.get('jefe_division', 'Por asignar')}\n"
                f"⏱️ **Duración:** {info['duracion']}\n\n"
                f"¿Te gustaría conocer las materias que llevarás durante la carrera?"
            )
            actualizar_conversacion(user_id, mensaje, contexto_carrera)
            return contexto_carrera

    # --- 6. MANEJO DE MATERIAS MEJORADO ---
    if memoria.get('carrera_seleccionada'):
        carrera_sel = memoria['carrera_seleccionada']
        
        # Detectar si quiere ver materias de forma natural
        palabras_materias = ["materias", "clases", "asignaturas", "qué lleva", "qué se estudia", "plan de estudios", "ver materias", "temas"]
        if any(palabra in mensaje_limpio for palabra in palabras_materias) or intencion in ["materias", "afirmacion"]:
            memoria['modo_materias'] = True
            guardar_memoria(user_id, memoria)
            
            respuesta_materias = materias_todas(carrera_sel, materias)
            respuesta = f"{obtener_respuesta_afirmativa()} el plan completo de **{carrera_sel}**:\n\n{respuesta_materias}\n\n¿Te interesa ver las materias de algún semestre en particular? Solo dime el número (ej: '3' o 'quinto semestre')."
            actualizar_conversacion(user_id, mensaje, respuesta)
            return respuesta
        
        # Si está en modo materias, busca por semestre
        if memoria.get('modo_materias'):
            semestre = detectar_semestre_natural(mensaje_limpio)
            
            if semestre and 1 <= semestre <= 9:
                respuesta = materias_por_semestre(carrera_sel, semestre, materias)
                respuesta += obtener_transicion()
                actualizar_conversacion(user_id, mensaje, respuesta)
                return respuesta
            
            # Búsqueda de materia específica
            nombres = [m['materia'] for m in materias if m['carrera'] == carrera_sel]
            match, score = process.extractOne(mensaje_limpio, nombres, scorer=fuzz.token_set_ratio) if nombres else (None, 0)
            
            if score > 75:
                m = next(x for x in materias if x['materia'] == match and x['carrera'] == carrera_sel)
                datos_crudos = f"Materia: {m['materia']}, Clave: {m['clave']}, Semestre: {m['semestre']}, Horas: {m.get('horas','N/A')}, Prerrequisito: {m.get('prerrequisito','Ninguno')}."
                respuesta = consultar_gemini(datos_crudos, f"Explica esta materia de forma amigable y útil para el estudiante.")
                actualizar_conversacion(user_id, mensaje, respuesta)
                return respuesta

    # --- 7. PREGUNTAS GENERALES MEJORADAS ---
    mejor_match_general = None
    mejor_score_general = 0
    
    for item in general:
        score = fuzz.partial_ratio(limpiar_texto(item['palabra_clave']), mensaje_limpio)
        if score > mejor_score_general:
            mejor_score_general = score
            mejor_match_general = item['respuesta']
    
    if mejor_score_general > 80:  # Bajamos el threshold para mayor flexibilidad
        respuesta = consultar_gemini(mejor_match_general, mensaje)
        # Agregar transición si cambió de tema
        if memoria.get('ultimo_tema') != 'general':
            respuesta += obtener_transicion()
            memoria['ultimo_tema'] = 'general'
            guardar_memoria(user_id, memoria)
        
        actualizar_conversacion(user_id, mensaje, respuesta)
        return respuesta

    # --- 8. FALLBACK MEJORADO ---
    registrar_ignorancia(mensaje_limpio)
    
    # Intentar con Gemini si está disponible
    if USAR_GEMINI:
        try:
            prompt_fallback = f"""
            Eres AulaBot, asistente virtual del ITSCH. El usuario preguntó: '{mensaje}'.
            
            Si es una pregunta sobre educación superior, ingenierías, trámites escolares, vida estudiantil o temas relacionados con educación técnica:
            - Responde de manera amable y útil
            - Si no tienes información específica, sugiere consultar en servicios escolares
            - Mantén un tono conversacional y usa emojis apropiados
            
            Si es completamente fuera de contexto, responde amablemente redirigiendo al tema académico.
            """
            respuesta = consultar_gemini(prompt_fallback, mensaje)
            actualizar_conversacion(user_id, mensaje, respuesta)
            return respuesta
        except:
            pass

    # Respuesta por defecto más amigable
    respuestas_fallback = [
        "Mmm, esa pregunta es interesante. 😅 Aún no tengo esa información específica, pero la anotaré para investigarla. ¿Puedo ayudarte con algo más del ITSCH?",
        "¡Vaya! Esa no me la sé todavía. 🤔 Pero puedo ayudarte con información sobre carreras, materias, costos y trámites del instituto.",
        "Ese dato específico no lo tengo a la mano. 😊 ¿Te puedo ayudar con información académica o sobre los servicios del ITSCH?"
    ]
    
    respuesta = random.choice(respuestas_fallback)
    actualizar_conversacion(user_id, mensaje, respuesta)
    return respuesta