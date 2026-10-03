import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno si existe un archivo .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

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

# Formulario 
FORMULARIO_URL = os.getenv("FORMULARIO_URL", "")
