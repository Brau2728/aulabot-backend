import csv
import json  # <--- IMPORTANTE
import os    # <--- IMPORTANTE

# -----------------------------
# Leer CSV
# -----------------------------
def leer_csv(nombre_archivo):
    datos = []
    try:
        with open(nombre_archivo, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for fila in reader:
                datos.append(fila)
    except FileNotFoundError:
        print(f"⚠️ Advertencia: No se encontró {nombre_archivo}")
    return datos

# -----------------------------
# Listar carreras
# -----------------------------
def listar_carreras(carreras):
    """Devuelve una lista de nombres de carreras"""
    return [c['nombre'] for c in carreras]

# -----------------------------
# Materias de toda la carrera (texto plano)
# -----------------------------
def materias_todas(carrera, materias):
    materias_carrera = [m for m in materias if m['carrera'].lower() == carrera.lower()]
    if not materias_carrera:
        return "No se encontraron materias para esta carrera."

    # Ordenar por semestre
    materias_carrera.sort(key=lambda x: int(x['semestre']))

    texto = ""
    # Obtenemos semestres únicos ordenados
    semestres = sorted(set(int(m['semestre']) for m in materias_carrera))
    
    for sem in semestres:
        texto += f"Semestre {sem}:\n"
        for m in materias_carrera:
            if int(m['semestre']) == sem:
                texto += f"  - {m['materia']} ({m['clave']}) - {m['horas']} hrs\n"
        texto += "\n"
    
    return texto

# -----------------------------
# Materias por semestre (texto plano)
# -----------------------------
def materias_por_semestre(carrera, semestre, materias):
    materias_carrera = [m for m in materias if m['carrera'].lower() == carrera.lower() and int(m['semestre']) == int(semestre)]
    if not materias_carrera:
        return f"No se encontraron materias para el semestre {semestre}."

    texto = f"Semestre {semestre}:\n"
    for m in materias_carrera:
        texto += f"  - {m['materia']} ({m['clave']}) - {m['horas']} hrs\n"
    
    return texto

# -----------------------------
# Manejo de Aprendizaje (SimSimi)
# -----------------------------
RUTA_APRENDIZAJE = "data/aprendido.json"

def cargar_conocimiento_adquirido():
    """Lee lo que el bot ha aprendido"""
    if not os.path.exists(RUTA_APRENDIZAJE):
        return {}
    try:
        with open(RUTA_APRENDIZAJE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def guardar_nuevo_conocimiento(pregunta, respuesta):
    """Guarda una nueva enseñanza"""
    conocimiento = cargar_conocimiento_adquirido()
    conocimiento[pregunta] = respuesta
    
    # Aseguramos que el directorio data exista
    os.makedirs(os.path.dirname(RUTA_APRENDIZAJE), exist_ok=True)
    
    with open(RUTA_APRENDIZAJE, "w", encoding="utf-8") as f:
        json.dump(conocimiento, f, ensure_ascii=False, indent=4)

# -----------------------------
# Registrar preguntas sin respuesta
# -----------------------------
def registrar_ignorancia(mensaje_usuario):
    """Guarda en un archivo de texto lo que el bot no entendió"""
    archivo = "data/preguntas_sin_respuesta.txt"
    
    # Aseguramos que el directorio data exista
    os.makedirs(os.path.dirname(archivo), exist_ok=True)
    
    with open(archivo, "a", encoding="utf-8") as f:
        f.write(f"{mensaje_usuario}\n")

        
def listar_carreras(carreras_data):
    """Genera una lista formateada de todas las carreras."""
    lista = []
    
    # Crear una lista de nombres de carrera, excluyendo "Ingeniería en" para que quepa mejor.
    nombres_carrera = [
        carrera['nombre'].replace("Ingeniería en ", "").replace("Ingeniería ", "")
        for carrera in carreras_data
    ]
    
    # Formatear la lista con emojis
    for i, nombre in enumerate(nombres_carrera):
        lista.append(f"🎓 {i+1}. {nombre}")
    
    return "\n".join(lista)