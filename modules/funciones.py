import csv
import json
import os

# -----------------------------
# Funciones de Soporte
# -----------------------------
RUTA_APRENDIZAJE = "data/aprendido.json"

def _parse_horas(horas_str):
    """Convierte '3-2-5' a '3T / 2P (5 Créditos)'"""
    if not horas_str or '-' not in horas_str:
        return f"{horas_str} hrs"
    
    parts = horas_str.split('-')
    if len(parts) == 3:
        teoricas = parts[0]
        practicas = parts[1]
        creditos = parts[2]
        return f"{teoricas}T / {practicas}P ({creditos} Créditos)"
    return f"{horas_str} hrs"

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
    os.makedirs(os.path.dirname(RUTA_APRENDIZAJE), exist_ok=True)
    with open(RUTA_APRENDIZAJE, "w", encoding="utf-8") as f:
        json.dump(conocimiento, f, ensure_ascii=False, indent=4)

def registrar_ignorancia(mensaje_usuario):
    """Guarda en un archivo de texto lo que el bot no entendió"""
    archivo = "data/preguntas_sin_respuesta.txt"
    os.makedirs(os.path.dirname(archivo), exist_ok=True)
    with open(archivo, "a", encoding="utf-8") as f:
        f.write(f"{mensaje_usuario}\n")

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
# Listar carreras (Para el menú de "carreras")
# -----------------------------
def listar_carreras(carreras_data):
    """Genera una lista formateada de todas las carreras."""
    lista = []
    
    nombres_carrera = [
        carrera['nombre'].replace("Ingeniería en ", "").replace("Ingeniería ", "")
        for carrera in carreras_data
    ]
    
    # Formatear la lista con emojis
    for i, nombre in enumerate(nombres_carrera):
        lista.append(f"🎓 {i+1}. {nombre}")
    
    return "\n".join(lista)

# -----------------------------
# Materias de toda la carrera
# -----------------------------
def materias_todas(carrera, materias):
    materias_carrera = [m for m in materias if m['carrera'].lower() == carrera.lower()]
    if not materias_carrera:
        return "No se encontraron materias para esta carrera."

    try:
        materias_carrera.sort(key=lambda x: int(x['semestre']))
    except ValueError:
        pass
        
    texto = ""
    semestres = sorted(set(m['semestre'] for m in materias_carrera), key=lambda x: int(x) if x.isdigit() else x)
    
    for sem in semestres:
        texto += f"**Semestre {sem}:**\n"
        for m in materias_carrera:
            if m['semestre'] == sem:
                parsed_horas = _parse_horas(m.get('horas', 'N/A'))
                texto += f"  - {m['materia']} ({m['clave']}) - {parsed_horas}\n"
        texto += "\n"
    
    return texto

# -----------------------------
# Materias por semestre
# -----------------------------
def materias_por_semestre(carrera, semestre, materias):
    semestre_str = str(semestre)
    materias_carrera = [m for m in materias if m['carrera'].lower() == carrera.lower() and m['semestre'] == semestre_str]
    if not materias_carrera:
        return f"No se encontraron materias para el semestre {semestre}."

    texto = f"**Semestre {semestre} de {carrera}:**\n"
    for m in materias_carrera:
        parsed_horas = _parse_horas(m.get('horas', 'N/A'))
        texto += f"  - {m['materia']} ({m['clave']}) - {parsed_horas}\n"
    
    return texto