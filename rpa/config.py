import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno si existe un archivo .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

# URLs oficiales
PORTAL_ACADEMICO_URL = os.getenv(
    "PORTAL_ACADEMICO_URL",
    "https://dashboardacademico.ingenieria.usac.edu.gt/"
)
UEDI_URL = os.getenv(
    "UEDI_URL",
    "https://uedi.ingenieria.usac.edu.gt/campus/"
)
UEDI_LOGIN_URL = os.getenv(
    "UEDI_LOGIN_URL",
    "https://uedi.ingenieria.usac.edu.gt/campus/"
)
# URL directa al curso — evita la búsqueda frágil en el dashboard
UEDI_COURSE_URL = os.getenv(
    "UEDI_COURSE_URL",
    "https://uedi.ingenieria.usac.edu.gt/campus/course/view.php?id=7055"
)

# Credenciales de acceso configuradas en .env
USAC_USER = os.getenv("USAC_USER", "")
USAC_PASSWORD = os.getenv("USAC_PASSWORD", "")

# Configuracion de descargas
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Parametros del curso y material a buscar en UEDI
CURSO_OBJETIVO = os.getenv("CURSO_OBJETIVO", "LABORATORIO DE INTELIGENCIA ARTIFICIAL 1")
SECCION_OBJETIVO = os.getenv("SECCION_OBJETIVO", "Sección A")
SECCION_TEMA = os.getenv("SECCION_TEMA", "Proyectos")
MATERIAL_OBJETIVO = os.getenv("MATERIAL_OBJETIVO", "Proyecto #2")

# Formulario institucional / auxiliares (RPA 3)
FORMULARIO_URL = os.getenv(
    "FORMULARIO_URL",
    "https://docs.google.com/forms/d/e/1FAIpQLSc07nFfApobJQuo-3CCMqYOiYe9hYohH86vuDB7mfXHQ3ePVg/viewform?usp=sharing&ouid=106647079914827724912"
)
ESTUDIANTE_CARNET = os.getenv("ESTUDIANTE_CARNET", "555545124")
ESTUDIANTE_NOMBRE = os.getenv("ESTUDIANTE_NOMBRE", "Daniel")
ESTUDIANTE_CORREO = os.getenv("ESTUDIANTE_CORREO", f"{USAC_USER}@ingenieria.usac.edu.gt" if USAC_USER else "")
GRUPO_NUMERO = os.getenv("GRUPO_NUMERO", "Grupo 9")
SECCION_LAB = os.getenv("SECCION_LAB", "A")
REPO_GITHUB = os.getenv("REPO_GITHUB", "https://github.com/002Fer/-IA1-Proyecto2_GRUPO9_2S2026_SECA")
ESTADO_AGENTE_DEFAULT = os.getenv(
    "ESTADO_AGENTE",
    "Agente AURA activo. Gesto de escritura detectado. Llenado y validacion de formulario completados con exito."
)
