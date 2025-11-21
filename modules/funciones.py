import csv

# -----------------------------
# Leer CSV
# -----------------------------
def leer_csv(nombre_archivo):
    datos = []
    with open(nombre_archivo, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for fila in reader:
            datos.append(fila)
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
    for sem in sorted(set(int(m['semestre']) for m in materias_carrera)):
        texto += f"Semestre {sem}:\n"
        for m in materias_carrera:
            if int(m['semestre']) == sem:
                texto += f"  - {m['materia']} ({m['clave']}) - {m['horas']} hrs\n"
        texto += "\n"
    texto += "Escribe 'menu' para regresar al inicio."
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
    texto += "Escribe 'menu' para regresar al inicio."
    return texto
