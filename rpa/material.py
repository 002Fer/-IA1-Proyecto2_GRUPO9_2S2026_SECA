import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from rpa.config import (
    UEDI_URL,
    USAC_USER,
    USAC_PASSWORD,
    DOWNLOAD_DIR,
    CURSO_OBJETIVO,
    MATERIAL_OBJETIVO
)
from rpa.browser import get_browser_session

logger = logging.getLogger("RPA_Material")

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
    """
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
            # 1. Acceder al portal UEDI campus
            logger.info("1. Navegando al campus virtual de UEDI...")
            await page.goto(UEDI_URL, timeout=35000, wait_until="domcontentloaded")

            # 2. Iniciar sesión si es necesario
            login_btn = page.locator("a:has-text('Iniciar sesión'), a:has-text('Ingresar')")
            if await login_btn.count() > 0:
                logger.info("Redirigiendo a pantalla de autenticación SSO...")
                await login_btn.first.click()
                await page.wait_for_load_state("domcontentloaded")

            # 3. Completar credenciales en Keycloak SSO
            if username and pwd and ("auth.ingenieria.usac.edu.gt" in page.url or await page.locator("#username").count() > 0):
                logger.info(f"Ingresando credenciales de Keycloak para usuario: {username}...")
                await page.fill("#username", username)
                await page.fill("#password", pwd)
                await page.click("#kc-login, input[type='submit']")
                await page.wait_for_load_state("domcontentloaded")
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

            # 4. Navegar al curso objetivo
            logger.info(f"2. Buscando curso '{target_curso}'...")
            course_links = await page.locator("a[href*='course/view.php']").evaluate_all("""
                els => els.map(e => ({
                    text: (e.textContent || '').trim().replace(/\\s+/g, ' '),
                    href: e.href
                }))
            """)

            target_course_url, nombre_curso_match = _buscar_mejor_curso(course_links, target_curso)
            if target_course_url:
                logger.info(f"Curso encontrado: '{nombre_curso_match}' -> {target_course_url}")
                await page.goto(target_course_url)
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(2000)

            # 5. Localizar la actividad solicitada
            logger.info(f"3. Buscando actividad para material '{target_material}'...")
            actividades = await page.locator("a[href*='/mod/'], a[href*='pluginfile.php']").evaluate_all("""
                els => els.map(e => ({
                    text: (e.textContent || e.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' '),
                    href: e.href
                })).filter(e => e.text.length > 0)
            """)

            # Puntuación y selección de la mejor actividad
            candidatos_puntuados = []
            for act in actividades:
                score = _calcular_coincidencia(act['text'], target_material)
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
                await page.goto(act_url)
                await page.wait_for_load_state("domcontentloaded")
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

            return {
                "success": True,
                "file_path": archivo_guardado,
                "message": f"Material '{nombre_archivo}' descargado correctamente en downloads/ ({tam} bytes)"
            }

    except Exception as e:
        logger.error(f"Error al descargar material de UEDI: {str(e)}")
        return {
            "success": False,
            "file_path": None,
            "error": str(e),
            "message": f"Error al descargar material desde UEDI: {str(e)}"
        }
