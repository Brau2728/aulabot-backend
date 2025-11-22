import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# 1. Configuración para encontrar la carpeta 'modules'
# Esto asegura que Python encuentre tus archivos ia.py, memoria.py, etc.
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

try:
    from modules import ia  # Importamos el cerebro que creamos
except ImportError as e:
    print(f"Error importando módulos: {e}")
    # Fallback por si acaso
    class ia:
        @staticmethod
        def obtener_respuesta(texto):
            return "Error interno: No pude cargar mi cerebro (modules/ia.py)."

# Cargar variables de entorno (.env)
load_dotenv()

# 2. Inicializar la App Flask
app = Flask(__name__)

# 3. Habilitar CORS (Vital para que Flutter pueda conectarse)
CORS(app) 

# --- RUTAS ---

@app.route('/', methods=['GET'])
def home():
    """Ruta de prueba para ver si el servidor está vivo en Render"""
    return "<h1>🤖 AulaBot Backend está EN LÍNEA</h1><p>La API está lista para recibir peticiones en /chat</p>"


@app.route('/chat', methods=['POST'])
def chat():
    """Ruta principal donde la App de Flutter envía los mensajes"""
    try:
        # 1. Recibir datos del usuario
        data = request.get_json()
        
        if not data:
            return jsonify({"respuesta": "Error: No enviaste datos JSON"}), 400

        mensaje_usuario = data.get('mensaje', '')
        usuario_id = data.get('usuario_id', 'anonimo')

        print(f"📩 Mensaje recibido de {usuario_id}: {mensaje_usuario}")

        # 2. Consultar a la IA (Gemini)
        respuesta_ia = ia.obtener_respuesta(mensaje_usuario)

        # CORRECCIÓN AQUÍ ABAJO:
        print(f"🤖 Respuesta generada: {respuesta_ia[:50]}...") 

        # 3. Responder a Flutter
        return jsonify({
            "respuesta": respuesta_ia,
            "status": "success"
        })

    except Exception as e:
        print(f"⚠️ Error en el servidor: {e}")
        return jsonify({"respuesta": "Lo siento, mi servidor tuvo un error interno."}), 500
# --- ARRANQUE DEL SERVIDOR (CONFIGURACIÓN RENDER) ---

if __name__ == '__main__':
    # IMPORTANTE: Render asigna un puerto dinámico en la variable 'PORT'.
    # Si 'PORT' no existe (ej. en tu PC), usa el 5000.
    port = int(os.environ.get("PORT", 5000))
    
    print(f"🚀 Iniciando servidor en el puerto {port}...")
    
    # host='0.0.0.0' es OBLIGATORIO para que la nube pueda acceder a tu API.
    # debug=False es mejor para producción.
    app.run(host='0.0.0.0', port=port, debug=False)