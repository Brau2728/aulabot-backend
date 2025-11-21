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
# ¡SUSTITUYE ESTO CON TU CLAVE REAL!
API_KEY = "AIzaSyDPDnvS1JJNfXvJUQyTYGTSu9kIEAgkjyo" 

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    USAR_GEMINI = True
except Exception as e:
    print(f"⚠️ Error Gemini: {e}")
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
    prompt = f"""Eres AulaBot del ITSCH. INFORMACIÓN: "{contexto}". USUARIO: "{pregunta_usuario}". Responde amable, usa emojis, resume si es largo. NO inventes."""
    try:
        return model.generate_content(prompt).text
    except:
        return contexto

# Lógica Principal
def generar_respuesta(mensaje, user_id, general, carreras, materias):
    mensaje_limpio = limpiar_texto(mensaje)
    memoria = obtener_memoria(user_id)

    if 'reiniciar' in mensaje_limpio:
        reset_memoria(user_id)
        return "🔄 Conversación reiniciada."

    intencion = detectar_mejor_coincidencia(mensaje_limpio, INTENCIONES)

    # 1. Ayuda
    if intencion == "ayuda":
        return "🤖 **Menú AulaBot**\n🎓 Carreras\n📘 Materias\n💵 Costos\n🏛 Directorio\n⚽ Deportes\n📅 Trámites\n¡Pregúntame!"

    # 2. Contexto Activo (Carreras)
    if memoria.get('carrera_seleccionada'):
        carrera_sel = memoria['carrera_seleccionada']
        if intencion == "materias" or intencion == "afirmacion" or "ver" in mensaje_limpio:
            memoria['modo_materias'] = True
            guardar_memoria(user_id, memoria)
            return f"📂 Viendo materias de **{carrera_sel}**. Escribe 'todas' o el semestre."

        if memoria.get('modo_materias'):
            if 'todas' in mensaje_limpio: return materias_todas(carrera_sel, materias)
            nums = re.findall(r'\d+', mensaje_limpio)
            if nums: return materias_por_semestre(carrera_sel, int(nums[0]), materias)
            
            nombres = [m['materia'] for m in materias if m['carrera'] == carrera_sel]
            match, score = process.extractOne(mensaje_limpio, nombres, scorer=fuzz.token_set_ratio) if nombres else (None, 0)
            if score > 75:
                m = next(x for x in materias if x['materia'] == match and x['carrera'] == carrera_sel)
                datos = f"Materia: {m['materia']}, Semestre: {m['semestre']}, Créditos: {m.get('creditos','N/A')}."
                return consultar_gemini(datos, "¿Qué onda con esta materia?")

    # 3. General (CSV)
    mejor_match, mejor_score = None, 0
    for item in general:
        score = fuzz.partial_ratio(limpiar_texto(item['palabra_clave']), mensaje_limpio)
        if score > mejor_score:
            mejor_score = score
            mejor_match = item['respuesta']
    if mejor_score > 85:
        return consultar_gemini(mejor_match, mensaje)

    # 4. Nueva Carrera
    posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
    if posible_carrera:
        memoria['carrera_seleccionada'] = posible_carrera
        memoria['modo_materias'] = False
        guardar_memoria(user_id, memoria)
        info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
        if info:
            datos = f"Carrera: {info['nombre']}. Descripción: {info['descripcion']}. Jefe: {info.get('jefe_division','N/A')}."
            return consultar_gemini(datos, "Háblame de esta carrera.")

    # 5. Fallback (Gemini Puro)
    registrar_ignorancia(mensaje_limpio)
    prompt_fallback = f"Eres AulaBot. Usuario dice: '{mensaje}'. No hay dato oficial. Responde amable si es saludo. Si es técnico di que no sabes."
    try:
        if USAR_GEMINI: return model.generate_content(prompt_fallback).text
    except: pass
    return "Mmm, no tengo ese dato a la mano. 😅"