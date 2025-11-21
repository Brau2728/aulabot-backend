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
# Define qué datos esperamos recibir del celular
class MensajeUsuario(BaseModel):
    usuario_id: str  # Identificador único (ej. "usuario_123")
    mensaje: str     # Lo que escribe la persona

# Define qué datos vamos a responder
class RespuestaBot(BaseModel):
    respuesta: str
    estado: str = "ok"

# -----------------------------
# 3. Carga de Datos Robusta
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    # Construir rutas absolutas para evitar errores en la nube
    path_general = os.path.join(BASE_DIR, "data", "general.csv")
    path_carreras = os.path.join(BASE_DIR, "data", "carreras.csv")
    path_materias = os.path.join(BASE_DIR, "data", "materias.csv")

    # Cargar los archivos
    general = leer_csv(path_general)
    carreras = leer_csv(path_carreras)
    materias = leer_csv(path_materias)
    print("✅ Base de datos cargada correctamente.")

except Exception as e:
    print(f"❌ Error crítico al cargar datos: {e}")
    # Detener el servidor si no hay datos (evita que arranque roto)
    sys.exit(1)

# -----------------------------
# 4. Endpoints (Rutas)
# -----------------------------

# Ruta Raíz: Sirve el frontend web (opcional, pero útil para pruebas rápidas)
@app.get("/")
async def read_index():
    file_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"mensaje": "AulaBot API activa. Usa /docs para ver la documentación."}

# Ruta de Chat PRO: Usa POST y Modelos
@app.post("/chat", response_model=RespuestaBot)
def chat_endpoint(datos: MensajeUsuario):
    """
    Recibe un mensaje y un ID de usuario, devuelve la respuesta de la IA.
    """
    # 1. Validación básica
    if not datos.mensaje.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")

    try:
        # 2. Llamar a la lógica de IA (pasando el ID de usuario)
        # NOTA: Asegúrate de actualizar generar_respuesta en ia.py para aceptar usuario_id
        respuesta_texto = generar_respuesta(
            datos.mensaje, 
            datos.usuario_id, 
            general, 
            carreras, 
            materias
        )
        
        # 3. Devolver respuesta estructurada
        return RespuestaBot(respuesta=respuesta_texto)

    except Exception as e:
        print(f"Error interno en chat: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")