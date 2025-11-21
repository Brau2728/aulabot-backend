from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import sys

# Importar tus módulos locales
from modules.ia import generar_respuesta
from modules.funciones import leer_csv

# -----------------------------
# 1. Configuración Inicial
# -----------------------------
app = FastAPI(title="AulaBot API", version="2.0")

# Configuración CORS (Permite que tu App Flutter y Web se conecten)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# 2. Modelos de Datos (Pydantic)
# -----------------------------
class MensajeUsuario(BaseModel):
    usuario_id: str
    mensaje: str

class RespuestaBot(BaseModel):
    respuesta: str
    estado: str = "ok"

# -----------------------------
# 3. Carga de Datos Robusta
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    path_general = os.path.join(BASE_DIR, "data", "general.csv")
    path_carreras = os.path.join(BASE_DIR, "data", "carreras.csv")
    path_materias = os.path.join(BASE_DIR, "data", "materias.csv")

    general = leer_csv(path_general)
    carreras = leer_csv(path_carreras)
    materias = leer_csv(path_materias)
    print("✅ Base de datos cargada correctamente.")

except Exception as e:
    print(f"❌ Error crítico al cargar datos: {e}")
    sys.exit(1)

# -----------------------------
# 4. Endpoints (Rutas)
# -----------------------------
@app.get("/")
async def read_index():
    file_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"mensaje": "AulaBot API activa. Usa /docs para ver la documentación."}

@app.post("/chat", response_model=RespuestaBot)
def chat_endpoint(datos: MensajeUsuario):
    if not datos.mensaje.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")

    try:
        respuesta_texto = generar_respuesta(
            datos.mensaje, 
            datos.usuario_id, 
            general, 
            carreras, 
            materias
        )
        
        return RespuestaBot(respuesta=respuesta_texto)

    except Exception as e:
        print(f"Error interno en chat: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")