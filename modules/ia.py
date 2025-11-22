import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def cargar_conocimiento():
    """
    Carga toda la información textual de la carpeta data para crear el cerebro del bot.
    """
    contexto_acumulado = ""
    
    # Archivos clave que debe leer
    archivos_conocimiento = [
        ("informe_institucional.txt", "INFORMACIÓN ESTRATÉGICA, CARRERAS Y COSTOS"),
        ("normativa_visitas.txt", "NORMATIVA DE VISITAS A EMPRESAS (P-ITSCH-DPV-17)")
    ]

    for nombre_archivo, titulo_seccion in archivos_conocimiento:
        ruta = os.path.join("data", nombre_archivo)
        if os.path.exists(ruta):
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                    contexto_acumulado += f"\n--- {titulo_seccion} ---\n{contenido}\n"
            except Exception as e:
                print(f"Error leyendo {nombre_archivo}: {e}")
    
    return contexto_acumulado

# Cargamos el contexto en memoria al iniciar la app
BASE_CONOCIMIENTO = cargar_conocimiento()

def obtener_respuesta(mensaje_usuario):
    if not api_key:
        return "Error: Configura tu API KEY en el archivo .env o en Render."

    try:
        model = genai.GenerativeModel('gemini-1.5-flash') # Usamos Flash por ser rápido y tener gran ventana de contexto
        
        prompt_sistema = f"""
        Rol: Eres 'AulaBot', el asistente oficial y experto del Instituto Tecnológico Superior de Ciudad Hidalgo (ITSCH).
        
        Tu Base de Conocimiento (ESTRICTA):
        {BASE_CONOCIMIENTO}
        
        Instrucciones de Personalidad y Diseño:
        1. Eres un experto académico: Si preguntan por una ingeniería (ej. Mecatrónica), no solo des la lista de materias. MENCIONA el perfil de ingreso, la especialidad (ej. Manufactura) y el campo laboral. Vende la carrera.
        2. Costos y Trámites: Sé preciso con los precios (ej. Ficha $880-$950).
        3. Formato: Usa Markdown para listas, negritas en conceptos clave y tablas si hay precios.
        4. Tono: Profesional, innovador (como el ITSCH) y motivador.
        5. Si la respuesta está en el texto, úsala. Si no, di que no tienes esa información específica.
        
        Usuario: {mensaje_usuario}
        """

        response = model.generate_content(prompt_sistema)
        return response.text.strip()

    except Exception as e:
        print(f"Error Gemini: {e}")
        return "Lo siento, mis circuitos están procesando demasiada información. ¿Podrías preguntar de nuevo?"