import os
from modules.funciones import leer_csv
from modules.ia import generar_respuesta

# -----------------------------
# Ruta base del proyecto
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -----------------------------
# Cargar CSVs desde data/
# -----------------------------
general = leer_csv(os.path.join(BASE_DIR, "data", "general.csv"))
carreras = leer_csv(os.path.join(BASE_DIR, "data", "carreras.csv"))
materias = leer_csv(os.path.join(BASE_DIR, "data", "materias.csv"))

# -----------------------------
# Chat en consola
# -----------------------------
print("AulaBot: ¡Hola! Soy tu asistente educativo. Escribe 'salir' para terminar la conversación.")

while True:
    mensaje = input("Tú: ")
    if mensaje.lower() == "salir":
        print("AulaBot: ¡Hasta luego!")
        break
    respuesta = generar_respuesta(mensaje, general, carreras, materias)
    print(f"AulaBot: {respuesta}")
