from modules.funciones import listar_carreras, materias_por_semestre, materias_todas
from modules.memoria import obtener_memoria, guardar_memoria, reset_memoria
import unicodedata
import re

# -----------------------------
# Función para normalizar texto
# -----------------------------
def limpiar_texto(texto):
    texto = texto.lower()
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

# -----------------------------
# Función principal para generar respuesta
# -----------------------------
def generar_respuesta(mensaje, general, carreras, materias):
    mensaje_limpio = limpiar_texto(mensaje)
    memoria = obtener_memoria()

    # -----------------------------
    # Comando para regresar al menú
    # -----------------------------
    if 'menu' in mensaje_limpio or 'inicio' in mensaje_limpio:
        reset_memoria()
        return "Volvemos al menú principal. ¿Qué te gustaría saber? Puedes preguntar por carreras, materias o información general."

    # -----------------------------
    # Si ya se eligió carrera
    # -----------------------------
    if memoria.get('carrera_seleccionada'):
        carrera_sel = memoria['carrera_seleccionada']

        # Modo materias
        if memoria.get('modo_materias'):

            # Todas las materias
            if 'todas' in mensaje_limpio:
                lista = materias_todas(carrera_sel, materias)
                return f"Todas las materias de {carrera_sel} son:\n{lista}"

            # Materias por semestre
            sem = re.findall(r'\b\d+\b', mensaje_limpio)
            if sem:
                lista = materias_por_semestre(carrera_sel, int(sem[0]), materias)
                return lista

            # Materia específica
            for m in materias:
                if limpiar_texto(m['materia']) in mensaje_limpio and m['carrera'].lower() == carrera_sel.lower():
                    return f"{m['materia']} ({m['clave']}) - {m['horas']} hrs (Semestre {m['semestre']})"

            return "No encontré esa materia. Puedes escribir el semestre, 'todas' o el nombre exacto de la materia."

        else:
            # Pregunta inicial: ¿quieres ver materias?
            if 'sí' in mensaje_limpio or 'si' in mensaje_limpio:
                memoria['modo_materias'] = True
                guardar_memoria(memoria)
                return "¿Quieres ver todas las materias, de un semestre específico o una materia en particular?"
            else:
                reset_memoria()
                return "De acuerdo, volvemos al menú principal. ¿Qué te gustaría saber?"

    # -----------------------------
    # Revisar palabras clave generales
    # -----------------------------
    for item in general:
        if limpiar_texto(item['palabra_clave']) in mensaje_limpio:
            if item['categoria'] == 'consulta_carreras':
                lista = listar_carreras(carreras)
                texto_carreras = "\n- ".join(lista)
                return f"Las carreras disponibles son:\n- {texto_carreras}\n\n¿Cuál te interesa? Puedes escribir el nombre completo o parcial de la carrera."
            return item['respuesta']

    # -----------------------------
    # Revisar si el mensaje corresponde a alguna carrera
    # -----------------------------
    for c in carreras:
        nombre_limpio = limpiar_texto(c['nombre'])
        if nombre_limpio in mensaje_limpio or nombre_limpio.replace('ingenieria','ing') in mensaje_limpio:
            memoria['carrera_seleccionada'] = c['nombre']
            guardar_memoria(memoria)
            return f"{c['nombre']} ({c['clave']}) - {c['duracion']}\n{c['descripcion']}\n¿Quieres ver las materias de esta carrera? (sí/no)"

    # -----------------------------
    # Si no se entendió el mensaje
    # -----------------------------
    return "No entendí tu mensaje. Puedes preguntar por carreras, materias o información general."
