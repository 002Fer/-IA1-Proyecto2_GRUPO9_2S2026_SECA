import os
import re
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from rpa.config import (
    UEDI_URL,
    USAC_USER,
    USAC_PASSWORD,
    DOWNLOAD_DIR,
    CURSO_OBJETIVO,
    SECCION_TEMA,
    MATERIAL_OBJETIVO
)
from rpa.browser import get_browser_session

logger = logging.getLogger("RPA_Material")

# ---------------------------------------------------------------------------
# Caché en memoria: evita relanzar Chromium si el archivo ya fue descargado.
# TTL de 1 hora. El resultado incluye la ruta al archivo descargado.
# ---------------------------------------------------------------------------
_CACHE_TTL = 3600
_cache_result: Optional[Dict[str, Any]] = None
_cache_timestamp: float = 0.0


def _get_cached() -> Optional[Dict[str, Any]]:
    global _cache_result, _cache_timestamp
    if _cache_result and (time.time() - _cache_timestamp) < _CACHE_TTL:
        # Verificar que el archivo todavía existe en disco
        fp = _cache_result.get("file_path")
        if fp and Path(fp).exists():
            return _cache_result
    return None


def _set_cached(result: Dict[str, Any]) -> None:
    global _cache_result, _cache_timestamp
    _cache_result = result
    _cache_timestamp = time.time()

def _normalizar(texto: str) -> str:
    # Normaliza texto eliminando acentos, caracteres especiales y espacios extras.
    t = texto.lower()
    t = re.sub(r'[áàäâ]', 'a', t)
    t = re.sub(r'[éèëê]', 'e', t)
    t = re.sub(r'[íìïî]', 'i', t)
    t = re.sub(r'[óòöô]', 'o', t)
    t = re.sub(r'[úùüû]', 'u', t)
    t = re.sub(r'[^a-z0-9]', '', t)
    return t

def _calcular_coincidencia(texto_actividad: str, material_buscado: str) -> int:
    t_act = texto_actividad.strip()
    norm_act = _normalizar(t_act)
    norm_mat = _normalizar(material_buscado)

    # Coincidencia exacta completa
    if norm_act == norm_mat:
        return 1000

    nums_act = re.findall(r'\d+', t_act)
    nums_mat = re.findall(r'\d+', material_buscado)

    # Si ambos tienen números y no coinciden, descalificar completamente
    if nums_mat and nums_act and nums_mat != nums_act:
        return -1000

    score = 0
    # Si coinciden los números
    if nums_mat and nums_act and nums_mat == nums_act:
        score += 300

    # Coincidencia de subcadena
    if norm_mat in norm_act:
        score += 200
    elif norm_act in norm_mat:
        score += 150

    # Coincidencias palabra por palabra
    palabras_mat = re.findall(r'[a-zA-Z0-9]+', material_buscado.lower())
    for p in palabras_mat:
        if len(p) > 2 and p in t_act.lower():
            score += 50

    return score

def _buscar_mejor_curso(course_links, curso_buscado: str):
    
    # Encuentra el enlace del curso más parecido descartando palabras comunes como Laboratorio.
    stop_words = {"DE", "DEL", "LA", "LAS", "EL", "LOS", "POR", "PARA", "EN", "Y", "CURSO", "NOMBRE", "SECCION", "SECCIÓN", "LABORATORIO"}
    palabras = [p for p in re.findall(r'[a-zA-Z0-9]+', curso_buscado.upper()) if p not in stop_words and len(p) > 1]

    mejor_url = None
    mejor_score = 0
    mejor_nombre = ""

    for cl in course_links:
        t_upper = cl['text'].upper()
        # Coincidencia de palabras distintivas
        score = sum(3 for p in palabras if p in t_upper)

        # Bonificación secundaria si ambos son o no laboratorios
        if "LABORATORIO" in curso_buscado.upper() and "LABORATORIO" in t_upper:
            score += 1

        # Coincidencia de número de curso
        nums_buscados = re.findall(r'\d+', curso_buscado)
        nums_curso = re.findall(r'\d+', t_upper)
        if nums_buscados and nums_curso:
            if set(nums_buscados).intersection(set(nums_curso)):
                score += 4
            else:
                score -= 3

        if score > mejor_score:
            mejor_score = score
            mejor_url = cl['href']
            mejor_nombre = cl['text']

    return mejor_url, mejor_nombre

async def descargar_material(
    user: Optional[str] = None,
    password: Optional[str] = None,
    curso: Optional[str] = None,
    material: Optional[str] = None,
    headless: bool = True
) -> Dict[str, Any]:
    """
    RPA 2: Descargar automáticamente material/enunciado desde UEDI.
    Gesto asociado: Índice hacia abajo

    Soporta de forma transparente:
    - Archivos adjuntos dentro de Tareas (mod/assign).
    - Archivos como Recursos directos (mod/resource o PDFs).
    - Descarga autenticada preservando nombres originales de archivo.

    El resultado se almacena en caché por 1 hora: si el archivo ya existe
    en disco, la segunda llamada es instantánea.
    """
    # --- Responder desde caché si el archivo ya fue descargado ---
    cached = _get_cached()
    if cached:
        logger.info("Material servido desde caché (archivo ya descargado).")
        return cached

    # Leer valores actualizados en caliente del .env si no se enviaron explícitamente
    from dotenv import load_dotenv
    from rpa.config import BASE_DIR
    load_dotenv(BASE_DIR / ".env", override=True)

    target_curso = curso or os.getenv("CURSO_OBJETIVO", CURSO_OBJETIVO)
    target_material = material or os.getenv("MATERIAL_OBJETIVO", MATERIAL_OBJETIVO)
    username = user or os.getenv("USAC_USER", USAC_USER)
    pwd = password or os.getenv("USAC_PASSWORD", USAC_PASSWORD)

    logger.info(f"Iniciando descarga de material: '{target_material}' para curso '{target_curso}'...")

    try:
        async with get_browser_session(headless=headless, block_heavy_resources=True) as (page, context):
            # 1. Acceder directamente a la pantalla de login de UEDI
            logger.info("1. Navegando al campus virtual de UEDI...")
            login_url = "https://uedi.ingenieria.usac.edu.gt/campus/login/index.php"
            await page.goto(login_url, timeout=75000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            # 3. Completar credenciales en Keycloak SSO
            if username and pwd and ("auth.ingenieria.usac.edu.gt" in page.url or await page.locator("#username").count() > 0):
                logger.info(f"Ingresando credenciales de Keycloak para usuario: {username}...")
                await page.locator("#username").fill(username, timeout=25000)
                await page.locator("#password").fill(pwd, timeout=25000)
                await page.click("#kc-login, input[type='submit']")
                # CORRECCIÓN: timeout explícito — el default de Playwright es 30 000 ms
                # y con la cámara corriendo la red USAC lo agotaba.
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=60000)
                except Exception:
                    pass
                await page.wait_for_timeout(3000)

            # Función auxiliar para descargar de forma autenticada y extraer el nombre original
            async def guardar_desde_url(url_descarga: str, nombre_default: str):
                resp = await context.request.get(url_descarga)
                disposition = resp.headers.get("content-disposition", "")
                nombre_final = nombre_default
                if "filename=" in disposition:
                    m = re.search(r'filename=["\']?([^"\';]+)["\']?', disposition)
                    if m:
                        nombre_final = m.group(1).strip()
                destino = DOWNLOAD_DIR / nombre_final
                destino.write_bytes(await resp.body())
                return str(destino), destino.stat().st_size

            # ---------------------------------------------------------------
            # 4. Navegar DIRECTAMENTE al curso por URL conocida.
            #    Esto es más rápido y robusto que buscar el curso en el dashboard.
            # ---------------------------------------------------------------
            from rpa.config import UEDI_COURSE_URL
            course_url = os.getenv("UEDI_COURSE_URL", UEDI_COURSE_URL)
            logger.info(f"2. Navegando directo al curso: {course_url}")
            await page.goto(course_url, timeout=75000, wait_until="commit")
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=30000)
            except Exception:
                pass
            await page.wait_for_timeout(2000)

            # ---------------------------------------------------------------
            # 5. Encontrar la sección "Proyectos" en el formato card de Moodle.
            #    Las secciones se renderizan como tarjetas con links que contienen
            #    "section=" en la URL o como li.section con un encabezado visible.
            # ---------------------------------------------------------------
            target_seccion = os.getenv("SECCION_TEMA", SECCION_TEMA)
            logger.info(f"3. Buscando sección '{target_seccion}' en el curso...")

            seccion_url = await page.evaluate("""
                (seccion) => {
                    const q = seccion.toLowerCase().trim();

                    // Formato card de Moodle: cada tarjeta es un <a> o contiene un <a>
                    // con el nombre de la sección en el texto o en un atributo aria-label / title.
                    const candidatos = Array.from(document.querySelectorAll(
                        'a[href*="section="], .card a, .section-card a, ' +
                        '.course-section-header a, li.section > a, ' +
                        'a.aalink, .activity-title a'
                    ));

                    for (const a of candidatos) {
                        const txt = (
                            a.textContent ||
                            a.getAttribute('aria-label') ||
                            a.getAttribute('title') || ''
                        ).toLowerCase().trim();
                        if (txt === q || txt.startsWith(q)) {
                            return a.href;
                        }
                    }

                    // Fallback: buscar cualquier elemento visible con ese texto
                    const todo = Array.from(document.querySelectorAll('a'));
                    for (const a of todo) {
                        const txt = (a.textContent || '').trim().toLowerCase();
                        if (txt === q) return a.href;
                    }

                    return null;
                }
            """, target_seccion)

            if seccion_url:
                logger.info(f"   Sección '{target_seccion}' → {seccion_url}")
                await page.goto(seccion_url, timeout=75000, wait_until="commit")
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=30000)
                except Exception:
                    pass
                await page.wait_for_timeout(2000)
            else:
                logger.warning(
                    f"   Sección '{target_seccion}' no encontrada como card. "
                    "Buscando en la página completa del curso..."
                )

            # 6. Localizar la actividad dentro de la sección actual (ya navegamos a "Proyectos").
            #    Si no encontramos la sección, la búsqueda se hace sobre toda la página del curso.
            logger.info(f"4. Buscando actividad '{target_material}' en la página actual...")

            actividades = await page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('a[href*="/mod/"], a[href*="pluginfile.php"]'))
                        .map(e => ({
                            text: (e.textContent || e.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' '),
                            href: e.href,
                            inTargetSection: true
                        }))
                        .filter(e => e.text.length > 0);
                }
            """)

            logger.info(f"   Actividades encontradas en la página: {len(actividades)}")

            # Puntuación y selección de la mejor actividad
            # Las actividades de la sección objetivo reciben un bonus de puntuación.
            candidatos_puntuados = []
            for act in actividades:
                score = _calcular_coincidencia(act['text'], target_material)
                if act.get("inTargetSection"):
                    score += 100   # Bonus por estar en la sección correcta
                if score > 0:
                    candidatos_puntuados.append((score, act))

            candidatos_puntuados.sort(key=lambda x: x[0], reverse=True)

            if not candidatos_puntuados:
                return {
                    "success": False,
                    "file_path": None,
                    "message": f"No se encontró la actividad o recurso '{target_material}' en el curso de UEDI."
                }

            actividad_elegida = candidatos_puntuados[0][1]
            act_url = actividad_elegida['href']
            logger.info(f"Actividad seleccionada: '{actividad_elegida['text']}' ({act_url})")

            archivo_guardado = None
            tam = 0

            # 6. Procesar según el tipo de actividad en Moodle
            # Caso A: Recurso directo
            if "/mod/resource/" in act_url or any(ext in act_url.lower() for ext in [".pdf", ".zip", "forcedownload=1"]):
                logger.info("Tipo detectado: Recurso directo (mod/resource). Descargando archivo directamente...")
                archivo_guardado, tam = await guardar_desde_url(act_url, f"{target_material}.pdf")

            # Caso B: Tarea
            elif "/mod/assign/" in act_url:
                logger.info("Tipo detectado: Tarea (mod/assign). Ingresando a la tarea para localizar el enunciado adjunto...")
                # CORRECCIÓN: timeout explícito — el default de 30 000 ms se agotaba
                # con la red USAC lenta cuando la cámara corre en paralelo.
                await page.goto(act_url, timeout=75000, wait_until="commit")
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=30000)
                except Exception:
                    pass
                await page.wait_for_timeout(2000)

                # Localizar archivos adjuntos en el área principal de la tarea
                adjuntos = await page.locator("#region-main a[href*='pluginfile.php'], #intro a, .introattachment a").evaluate_all("""
                    els => els.map(e => ({
                        text: (e.textContent || '').trim().replace(/\\s+/g, ' '),
                        href: e.href
                    })).filter(e => e.href.includes('introattachment') || e.href.includes('pluginfile.php') || e.text.endsWith('.pdf'))
                """)

                if adjuntos:
                    adjunto = adjuntos[0]
                    sug_name = adjunto['text'] if adjunto['text'].endswith('.pdf') else f"{target_material}.pdf"
                    logger.info(f"Descargando enunciado adjunto de la tarea: '{sug_name}'...")
                    archivo_guardado, tam = await guardar_desde_url(adjunto['href'], sug_name)
                else:
                    logger.warning("No se encontró archivo adjunto en la descripción de la tarea.")

            if not archivo_guardado:
                return {
                    "success": False,
                    "file_path": None,
                    "message": f"No se pudo descargar el archivo para '{target_material}' en UEDI."
                }

            nombre_archivo = Path(archivo_guardado).name
            logger.info(f"Descarga exitosa: '{nombre_archivo}' ({tam} bytes) guardado en downloads/")

            result = {
                "success": True,
                "file_path": archivo_guardado,
                "message": f"Material '{nombre_archivo}' descargado correctamente en downloads/ ({tam} bytes)"
            }
            _set_cached(result)   # Guardar en caché (1 hora) para próximas llamadas
            return result

    except Exception as e:
        logger.error(f"Error al descargar material de UEDI: {str(e)}")
        return {
            "success": False,
            "file_path": None,
            "error": str(e),
            "message": f"Error al descargar material desde UEDI: {str(e)}"
        }
