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
    ],
    "Ingeniería Bioquímica": [
        "bioquimica", "biologia", "laboratorio", "alimentos", "ibq", "quimica"
    ],
    "Ingeniería en Nanotecnología": [
        "nanotecnologia", "nano", "materiales", "particulas", "ina"
    ],
    "Ingeniería en Innovación Agrícola Sustentable": [
        "agricola", "agronomia", "campo", "cultivos", "invernaderos", "iias"
    ],
    "Ingeniería en Tecnologías de la Información y Comunicaciones": [
        "tics", "tic", "redes", "telecomunicaciones", "conectividad", "itic"
    ],
    "Ingeniería en Animación Digital y Efectos Visuales": [
        "animacion", "digital", "videojuegos", "3d", "efectos", "arte", "iadev"
    ],
    "Ingeniería en Sistemas Automotrices": [
        "automotriz", "autos", "coches", "motores", "mecanica automotriz", "isau"
    ]
}

INTENCIONES = {
    "materias": ["materias", "materia", "clases", "asignaturas", "plan", "reticula", "que llevan", "curricula"],
    "costos": ["cuanto cuesta", "precio", "costo", "pagar", "inscripcion", "mensualidad", "dinero", "ficha", "pago"],
    "ubicacion": ["donde estan", "ubicacion", "mapa", "direccion", "llegar", "localizacion", "domicilio"],
    "saludo": ["hola", "buenos dias", "buenas", "que tal", "hey", "hi", "inicio", "comenzar"],
    "directorio": ["director", "jefe", "coordinador", "quien es", "encargado", "subdirector"],
    "tramites": ["admision", "propedeutico", "examen", "becas", "servicio social", "residencias", "titulacion"]
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
    texto_usuario = limpiar_texto(texto_usuario)
    mejor_score = 0
    mejor_opcion = None

    for clave, sinonimos in diccionario_opciones.items():
        match, score = process.extractOne(texto_usuario, sinonimos, scorer=fuzz.token_set_ratio)
        if score > mejor_score:
            mejor_score = score
            mejor_opcion = clave
    
    return mejor_opcion if mejor_score >= 70 else None

# -----------------------------
# Lógica Principal
# -----------------------------
def generar_respuesta(mensaje, user_id, general, carreras, materias):
    mensaje_limpio = limpiar_texto(mensaje)
    memoria = obtener_memoria(user_id)

    # --- 1. Comandos Globales ---
    if 'menu' in mensaje_limpio or 'reiniciar' in mensaje_limpio:
        reset_memoria(user_id)
        return "🔄 Reiniciado. ¿En qué puedo ayudarte ahora?"

    # --- 2. Detectar Intención General ---
    intencion = detectar_mejor_coincidencia(mensaje_limpio, INTENCIONES)
    
    # --- AQUÍ ESTÁ EL CAMBIO: SALUDO EXTENSO ---
    if intencion == "saludo":
        return (
            "¡Hola! 👋 Soy **AulaBot**, tu Asistente Estratégico del ITSCH.\n\n"
            "Estoy capacitado para informarte sobre:\n"
            "🏛 **Institución:** Historia, Misión, Directores y Jefes de División.\n"
            "🎓 **Académico:** Detalles de las 10 Ingenierías, Retículas y Especialidades.\n"
            "💵 **Trámites:** Costos, Proceso de Admisión, Becas y Titulación.\n"
            "⚽ **Vida Estudiantil:** Deportes, Inglés, Cafetería y Servicios.\n\n"
            "¿Qué te gustaría consultar hoy?"
        )

    # Buscamos en CSV General (Respuestas fijas)
    for item in general:
        if fuzz.partial_ratio(limpiar_texto(item['palabra_clave']), mensaje_limpio) > 85:
            return item['respuesta']

    # --- 3. Detección Inteligente de Carrera ---
    posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)

    if posible_carrera:
        memoria['carrera_seleccionada'] = posible_carrera
        memoria['modo_materias'] = False 
        guardar_memoria(user_id, memoria)
        
        info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
        if info:
            # Respuesta enriquecida con datos del nuevo CSV
            respuesta = f"🔍 **{info['nombre']}** ({info['clave']})\n\n"
            respuesta += f"📝 **Descripción:** {info['descripcion']}\n"
            respuesta += f"🎯 **Perfil de Ingreso:** {info['perfil_ingreso']}\n"
            respuesta += f"💼 **Campo Laboral:** {info['perfil_egreso']}\n"
            respuesta += f"⭐ **Especialidad:** {info['especialidad']}\n\n"
            
            if info.get('jefe_division') and info['jefe_division'] != "N/A":
                 respuesta += f"👤 **Jefe de División:** {info['jefe_division']}\n\n"

            respuesta += "¿Te gustaría ver las **materias** de esta carrera?"
            return respuesta

    # --- 4. Contexto Activo (Ya eligió carrera) ---
    if memoria.get('carrera_seleccionada'):
        carrera_sel = memoria['carrera_seleccionada']

        if intencion == "materias" or "si" in mensaje_limpio or "ver" in mensaje_limpio or "cuales" in mensaje_limpio:
            memoria['modo_materias'] = True
            guardar_memoria(user_id, memoria)
            return f"📂 **Plan de Estudios: {carrera_sel}**\n\nPuedes pedirme:\n1️⃣ 'Todas las materias'\n2️⃣ Un semestre (ej. '5')\n3️⃣ Una materia específica (ej. 'Cálculo')"

        if memoria.get('modo_materias'):
            if 'todas' in mensaje_limpio:
                return materias_todas(carrera_sel, materias)

            nums = re.findall(r'\d+', mensaje_limpio)
            if nums:
                return materias_por_semestre(carrera_sel, int(nums[0]), materias)

            nombres_materias = [m['materia'] for m in materias if m['carrera'] == carrera_sel]
            if nombres_materias:
                match, score = process.extractOne(mensaje_limpio, nombres_materias, scorer=fuzz.token_set_ratio)
                
                if score > 75:
                    m = next((x for x in materias if x['materia'] == match and x['carrera'] == carrera_sel), None)
                    return f"📘 **{m['materia']}**\nClave: {m['clave']}\nSemestre: {m['semestre']}\nCréditos: {m.get('creditos', 'N/A')}\nPrerrequisito: {m.get('prerrequisito', 'Ninguno')}"
            
            return f"🤔 No encontré esa materia en {carrera_sel}. Intenta escribir solo el número de semestre."

    # --- 5. Fallback ---
    registrar_ignorancia(mensaje_limpio)
    return (
        "No estoy seguro de qué tema hablas. 😅\n\n"
        "Prueba preguntando por:\n"
        "🔹 Una carrera (ej. 'Sistemas', 'Industrial')\n"
        "🔹 Un trámite (ej. 'Costos', 'Admisión')\n"
        "🔹 Un directivo (ej. 'Director', 'Jefe de Sistemas')"
    )