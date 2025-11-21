import google.generativeai as genai
from modules.funciones import listar_carreras, materias_por_semestre, materias_todas, registrar_ignorancia
from modules.memoria import obtener_memoria, guardar_memoria, reset_memoria
from thefuzz import process, fuzz 
import unicodedata
import re
import random
import os

# =========================================================
# 🤖 CONFIGURACIÓN DE GEMINI (GOOGLE AI)
# =========================================================
# ¡PEGA TU API KEY AQUÍ ABAJO! (Dentro de las comillas)
API_KEY = "AIzaSyCq5_N4rebajcW-eTn8FDcITrRnfSOa_Ho" 

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    USAR_GEMINI = True
except Exception as e:
    print(f"⚠️ Error configurando Gemini: {e}")
    USAR_GEMINI = False

# =========================================================
# 1. Mapa de Conocimiento (Sinónimos y Errores Comunes)
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
    "costos": ["cuanto cuesta", "precio", "costo", "pagar", "inscripcion", "mensualidad", "dinero", "ficha", "pago"],
    "ubicacion": ["donde estan", "ubicacion", "mapa", "direccion", "llegar", "localizacion", "domicilio"],
    "saludo": ["hola", "buenos dias", "buenas", "que tal", "hey", "hi", "inicio", "comenzar"],
    "directorio": ["director", "jefe", "coordinador", "quien es", "encargado", "subdirector"],
    "tramites": ["admision", "propedeutico", "examen", "becas", "servicio social", "residencias", "titulacion"],
    "ayuda": ["que sabes hacer", "que puedes hacer", "ayuda", "instrucciones", "para que sirves", "menu", "opciones", "temas"],
    "vida_estudiantil": ["deportes", "futbol", "cafeteria", "ingles", "centro de idiomas", "psicologia"],
    "afirmacion": ["si", "claro", "por favor", "yes", "simon", "ok", "va", "me parece"],
    "negacion": ["no", "nel", "asi dejalo", "gracias"]
}

# =========================================================
# 2. Funciones Auxiliares
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
    """
    Toma datos duros (contexto) y le pide a Gemini que redacte una respuesta bonita.
    """
    if not USAR_GEMINI:
        return contexto # Fallback si no hay internet/key

    prompt = f"""
    Eres AulaBot, el asistente virtual amigable del Instituto Tecnológico Superior de Ciudad Hidalgo (ITSCH).
    
    INFORMACIÓN OFICIAL (Contexto):
    "{contexto}"
    
    USUARIO DICE:
    "{pregunta_usuario}"
    
    TU TAREA:
    Responde al usuario basándote EXCLUSIVAMENTE en la Información Oficial.
    - Sé amable, usa emojis 🎓✨.
    - Si la información es una lista larga, resúmela o dales formato bonito.
    - NO inventes datos que no estén en la Información Oficial.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return contexto 

# =========================================================
# 3. Lógica Principal (Híbrida)
# =========================================================
def generar_respuesta(mensaje, user_id, general, carreras, materias):
    mensaje_limpio = limpiar_texto(mensaje)
    memoria = obtener_memoria(user_id)

    # --- Comandos de Reinicio ---
    if 'reiniciar' in mensaje_limpio or 'salir' in mensaje_limpio:
        reset_memoria(user_id)
        return "🔄 Conversación reiniciada. ¿En qué te ayudo ahora?"

    # --- Detección de Intención ---
    intencion = detectar_mejor_coincidencia(mensaje_limpio, INTENCIONES)

    # --- 1. INTENCIÓN DE AYUDA (MENÚ) ---
    if intencion == "ayuda":
        return (
            "🤖 **Menú de Capacidades AulaBot**\n\n"
            "Puedo informarte sobre todo esto:\n\n"
            "🎓 **Carreras:** Escribe 'Sistemas', 'Mecatrónica', 'Gestión'...\n"
            "📘 **Materias:** Dentro de una carrera, pide 'ver materias'.\n"
            "💵 **Pagos:** Pregunta por 'Costos', 'Inscripción' o 'Ficha'.\n"
            "🏛 **Directorio:** '¿Quién es el director?', 'Jefe de Industrial'.\n"
            "⚽ **Vida Estudiantil:** 'Deportes', 'Cafetería', 'Inglés'.\n"
            "📅 **Trámites:** 'Fechas de admisión', 'Propedéutico', 'Becas'.\n\n"
            "¡Toca un tema o escribe tu duda!"
        )

    # --- 2. CONTEXTO ACTIVO (Prioridad Alta) ---
    if memoria.get('carrera_seleccionada'):
        carrera_sel = memoria['carrera_seleccionada']
        
        # Si pide materias explícitamente o afirma
        if intencion == "materias" or intencion == "afirmacion" or "ver" in mensaje_limpio:
            memoria['modo_materias'] = True
            guardar_memoria(user_id, memoria)
            return f"📂 Entendido. ¿Quieres ver las materias de **{carrera_sel}**? Escribe 'todas' o un semestre (ej. '5')."

        if memoria.get('modo_materias'):
            if 'todas' in mensaje_limpio:
                return materias_todas(carrera_sel, materias)
            
            nums = re.findall(r'\d+', mensaje_limpio)
            if nums:
                return materias_por_semestre(carrera_sel, int(nums[0]), materias)
            
            # Búsqueda materia específica
            nombres = [m['materia'] for m in materias if m['carrera'] == carrera_sel]
            match, score = process.extractOne(mensaje_limpio, nombres, scorer=fuzz.token_set_ratio) if nombres else (None, 0)
            
            if score > 75:
                m = next(x for x in materias if x['materia'] == match and x['carrera'] == carrera_sel)
                # Usamos Gemini para explicar la materia bonito
                datos_crudos = f"Materia: {m['materia']}, Clave: {m['clave']}, Semestre: {m['semestre']}, Créditos: {m.get('creditos','N/A')}, Prerrequisito: {m.get('prerrequisito','Ninguno')}."
                return consultar_gemini(datos_crudos, "¿Qué onda con esta materia?")

    # --- 3. Preguntas Generales (CSV -> Gemini) ---
    mejor_match_general = None
    mejor_score_general = 0
    
    for item in general:
        score = fuzz.partial_ratio(limpiar_texto(item['palabra_clave']), mensaje_limpio)
        if score > mejor_score_general:
            mejor_score_general = score
            mejor_match_general = item['respuesta']
    
    if mejor_score_general > 85:
        return consultar_gemini(mejor_match_general, mensaje)

    # --- 4. Información de Carreras (CSV -> Gemini) ---
    posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
    if posible_carrera:
        memoria['carrera_seleccionada'] = posible_carrera
        memoria['modo_materias'] = False
        guardar_memoria(user_id, memoria)
        
        info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
        if info:
            contexto_carrera = (
                f"Carrera: {info['nombre']} ({info['clave']}). "
                f"Descripción: {info['descripcion']}. "
                f"Jefe de División: {info.get('jefe_division', 'N/A')}. "
                f"Perfil Ingreso: {info.get('perfil_ingreso', '')}. "
                f"Campo Laboral: {info.get('perfil_egreso', '')}. "
                f"Especialidad: {info.get('especialidad', '')}."
            )
            return consultar_gemini(contexto_carrera, "Háblame de esta carrera y pregúntame si quiero ver materias.")

    # --- 5. Chat Casual (Gemini Puro - Fallback) ---
    registrar_ignorancia(mensaje_limpio) 
    
    prompt_fallback = f"""
    Eres AulaBot del ITSCH. El usuario dijo: "{mensaje}".
    No encontraste información específica en tu base de datos oficial sobre esto.
    Responde amablemente.
    Si es un saludo o charla casual, conversa brevemente.
    Si es una pregunta técnica de la escuela que NO sabes, di: "Ese dato específico no lo tengo a la mano, pero puedo averiguarlo en Servicios Escolares."
    """
    try:
        if USAR_GEMINI:
            return model.generate_content(prompt_fallback).text
    except:
        pass

    return "Mmm, esa no me la sé todavía. 😅 Pero ya anoté tu duda para investigarla."
# Cambio forzado para Render