from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # Importar esto
from fastapi.responses import FileResponse # Importar esto
from modules.ia import generar_respuesta
from modules.funciones import leer_csv
import os

app = FastAPI()

# Configuración CORS (Se mantiene igual)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cargar datos (Optimización: hacerlo una sola vez al inicio es correcto)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
general = leer_csv(os.path.join(BASE_DIR, "data/general.csv"))
carreras = leer_csv(os.path.join(BASE_DIR, "data/carreras.csv"))
materias = leer_csv(os.path.join(BASE_DIR, "data/materias.csv"))

# --- NUEVO: Servir el frontend ---
# 1. Endpoint raíz devuelve el HTML
@app.get("/")
async def read_index():
    # Asegúrate de que index.html esté en la misma carpeta o ajusta la ruta
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

# 2. Endpoint de Chat (Tu lógica existente)
@app.get("/chat")
def chat(mensaje: str):
    respuesta = generar_respuesta(mensaje, general, carreras, materias)
    return {"respuesta": respuesta}

