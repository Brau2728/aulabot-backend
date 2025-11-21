from modules.funciones import (
    listar_carreras, materias_por_semestre, materias_todas, 
    registrar_ignorancia, cargar_conocimiento_adquirido, guardar_nuevo_conocimiento
)
from modules.memoria import obtener_memoria, guardar_memoria, reset_memoria
from thefuzz import process, fuzz 
import unicodedata
import re

# ... (Mantén aquí tus diccionarios SINONIMOS_CARRERAS e INTENCIONES igual que antes) ...
# Copia tus diccionarios SINONIMOS_CARRERAS e INTENCIONES aquí arriba
# (Para ahorrar espacio no los repito, pero NO LOS BORRES)
SINONIMOS_CARRERAS = {
    "Ingeniería en Sistemas Computacionales": ["sistemas", "programacion", "computacion", "desarrollo", "software", "codigo", "app", "web", "isc"],
    "Ingeniería en Gestión Empresarial": ["gestion", "empresas", "administracion", "negocios", "ige", "gerencia"],
    "Ingeniería Industrial": ["industrial", "procesos", "fabrica", "produccion", "logistica", "ii"],
    "Ingeniería Mecatrónica": ["mecatronica", "robotica", "automatizacion", "mecanica", "electronica", "im"]
}

INTENCIONES = {
    "materias": ["materias", "clases", "asignaturas", "plan de estudios", "reticula", "que llevan"],
    "costos": ["cuanto cuesta", "precio", "costo", "pagar", "inscripcion", "mensualidad"],
    "ubicacion": ["donde estan", "ubicacion", "mapa", "direccion", "llegar"],
    "saludo": ["hola", "buenos dias", "buenas", "que tal", "hey"],
    "aprender": ["aprender", "enseñar", "quiero enseñarte", "nuevo dato"] # ¡Nueva intención!
}

def limpiar_texto(texto):
    texto = texto.lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def detectar_mejor_coincidencia(texto_usuario, diccionario_opciones):
    texto_usuario = limpiar_texto(texto_usuario)
    mejor_score = 0
    mejor_opcion = None
    for clave, sinonimos in diccionario_opciones.items():
        match, score = process.extractOne(texto_usuario, sinonimos, scorer=fuzz.partial_ratio)
        if score > mejor_score:
            mejor_score = score
            mejor_opcion = clave
    return mejor_opcion if mejor_score >= 75 else None

# -----------------------------
# Lógica Principal (Con Modo Aprendizaje)
# -----------------------------
def generar_respuesta(mensaje, user_id, general, carreras, materias):
    mensaje_limpio = limpiar_texto(mensaje)
    memoria = obtener_memoria(user_id)

    # --- 0. MODO ENTRENAMIENTO (SimSimi) ---
    if memoria.get('modo_aprendizaje'):
        paso = memoria.get('paso_aprendizaje')
        
        if paso == 'esperando_pregunta':
            memoria['nueva_pregunta'] = mensaje
            memoria['paso_aprendizaje'] = 'esperando_respuesta'
            guardar_memoria(user_id, memoria)
            return f"Entendido. Cuando alguien me pregunte: '{mensaje}'... \n¿Qué debo responder? ✍️"
            
        if paso == 'esperando_respuesta':
            nueva_pregunta = memoria['nueva_pregunta']
            guardar_nuevo_conocimiento(nueva_pregunta, mensaje) # Guardamos en JSON
            
            # Reseteamos modo aprendizaje
            memoria['modo_aprendizaje'] = False
            del memoria['paso_aprendizaje']
            del memoria['nueva_pregunta']
            guardar_memoria(user_id, memoria)
            return "¡Listo! He aprendido algo nuevo. 🧠✨ \nIntenta preguntarme eso de nuevo."

    # --- 1. Comandos Globales ---
    if 'menu' in mensaje_limpio or 'inicio' in mensaje_limpio or 'cancelar' in mensaje_limpio:
        reset_memoria(user_id)
        return "🔄 Reiniciado. ¿En qué puedo ayudarte?"

    # --- 2. Activar Modo Aprendizaje ---
    intencion = detectar_mejor_coincidencia(mensaje_limpio, INTENCIONES)
    if intencion == 'aprender':
        memoria['modo_aprendizaje'] = True
        memoria['paso_aprendizaje'] = 'esperando_pregunta'
        guardar_memoria(user_id, memoria)
        return "🎓 ¡Modo Aprendizaje Activado! \n¿Qué pregunta quieres enseñarme a responder?"

    # --- 3. BUSCAR EN LO APRENDIDO (JSON) ---
    # Primero miramos si ya aprendió esto dinámicamente
    conocimiento_json = cargar_conocimiento_adquirido()
    if conocimiento_json:
        # Buscamos en las llaves del JSON
        mejor_pregunta, score = process.extractOne(mensaje, list(conocimiento_json.keys()), scorer=fuzz.token_sort_ratio) or (None, 0)
        if score > 85:
            return conocimiento_json[mejor_pregunta]

    # --- 4. Buscar Intenciones Generales (CSV) ---
    if intencion == "saludo":
        return "¡Hola! 👋 Soy AulaBot. Puedes enseñarme cosas nuevas escribiendo 'aprender'."
    
    for item in general:
        if fuzz.partial_ratio(limpiar_texto(item['palabra_clave']), mensaje_limpio) > 85:
            return item['respuesta']

    # --- 5. Lógica de Carreras y Materias (Igual que antes) ---
    # (Aquí va tu lógica de carreras que ya tenías, la resumo para que quepa, 
    #  pero tú deja el bloque completo de carreras/materias aquí)
    posible_carrera = detectar_mejor_coincidencia(mensaje_limpio, SINONIMOS_CARRERAS)
    if posible_carrera:
        memoria['carrera_seleccionada'] = posible_carrera
        memoria['modo_materias'] = False 
        guardar_memoria(user_id, memoria)
        info = next((c for c in carreras if c['nombre'] == posible_carrera), None)
        return f"🎓 **{info['nombre']}**\n{info['descripcion']}\n¿Quieres ver materias?"

    if memoria.get('carrera_seleccionada'):
        carrera_sel = memoria['carrera_seleccionada']
        if intencion == "materias" or "si" in mensaje_limpio:
            memoria['modo_materias'] = True
            guardar_memoria(user_id, memoria)
            return f"Viendo materias de {carrera_sel}. Escribe 'todas' o el semestre."
        
        if memoria.get('modo_materias'):
             if 'todas' in mensaje_limpio: return materias_todas(carrera_sel, materias)
             nums = re.findall(r'\d+', mensaje_limpio)
             if nums: return materias_por_semestre(carrera_sel, int(nums[0]), materias)
             # Búsqueda materia difusa...
             nombres = [m['materia'] for m in materias if m['carrera'] == carrera_sel]
             if nombres:
                 match, sc = process.extractOne(mensaje_limpio, nombres, scorer=fuzz.partial_ratio)
                 if sc > 80:
                     m = next((x for x in materias if x['materia'] == match and x['carrera'] == carrera_sel), None)
                     return f"📘 {m['materia']} (Semestre {m['semestre']})"

    # --- 6. No entendí -> Sugerir Aprender ---
    registrar_ignorancia(mensaje_limpio)
    return "No sé la respuesta a eso. 😅\n\nSi tú la sabes, escribe **'aprender'** para enseñármela."