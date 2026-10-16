import os
import re
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from rpa.config import (
    BASE_DIR,
    FORMULARIO_URL,
    USAC_USER,
    ESTUDIANTE_CARNET,
    ESTUDIANTE_NOMBRE,
    ESTUDIANTE_CORREO,
    GRUPO_NUMERO,
    SECCION_LAB,
    REPO_GITHUB,
    ESTADO_AGENTE_DEFAULT
)
from rpa.browser import get_browser_session

logger = logging.getLogger("RPA_Formulario")


async def completar_formulario(
    datos: Optional[Dict[str, str]] = None,
    headless: bool = True
) -> Dict[str, Any]:
    """
    RPA 3: Completar automáticamente formulario.
    Gesto asociado: Simular escritura con el índice

    1. Accede al formulario de Google Forms configurado en .env.
    2. Identifica los campos requeridos (Carné, Nombre, Correo, Grupo, Sección, Repo, Estado).
    3. Rellena las respuestas y selecciona las opciones correspondientes.
    4. Valida que los campos requeridos hayan sido completados.
    5. Envía el formulario y confirma el mensaje de respuesta de Google Forms.
    """
    # Recargar .env en caliente por si se actualizó FORMULARIO_URL recientemente
    load_dotenv(BASE_DIR / ".env", override=True)

    target_url = os.getenv("FORMULARIO_URL", FORMULARIO_URL).strip()
    if not target_url:
        logger.error("FORMULARIO_URL no configurada en el archivo .env")
        return {
            "success": False,
            "data": None,
            "message": "FORMULARIO_URL no configurada. Define la URL del formulario en el archivo .env"
        }

    # Armar datos por defecto combinados con datos personalizados si se enviaron
    user_carnet = os.getenv("USAC_USER", USAC_USER)
    datos_finales = {
        "carnet": os.getenv("ESTUDIANTE_CARNET", ESTUDIANTE_CARNET),
        "nombre": os.getenv("ESTUDIANTE_NOMBRE", ESTUDIANTE_NOMBRE),
        "correo": os.getenv("ESTUDIANTE_CORREO", ESTUDIANTE_CORREO or f"{user_carnet}@ingenieria.usac.edu.gt"),
        "grupo": os.getenv("GRUPO_NUMERO", GRUPO_NUMERO),
        "seccion": os.getenv("SECCION_LAB", SECCION_LAB),
        "repo": os.getenv("REPO_GITHUB", REPO_GITHUB),
        "estado": os.getenv("ESTADO_AGENTE", ESTADO_AGENTE_DEFAULT)
    }

    if datos:
        datos_finales.update(datos)

    logger.info(f"Iniciando RPA 3: Completar formulario en: {target_url}")
    logger.info(f"Datos a registrar: Carnet={datos_finales['carnet']}, Nombre={datos_finales['nombre']}, Grupo={datos_finales['grupo']}, Sección={datos_finales['seccion']}")

    try:
        async with get_browser_session(headless=headless, block_heavy_resources=True) as (page, _):
            # 1. Navegar al formulario
            logger.info("1. Cargando formulario de Google Forms...")
            await page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_selector("div[role='listitem']", timeout=20000)

            # 2. Localizar preguntas
            items = page.locator("div[role='listitem']")
            total_items = await items.count()
            logger.info(f"2. Formulario cargado. Total de preguntas encontradas: {total_items}")

            campos_llenados = 0

            for i in range(total_items):
                item = items.nth(i)
                title_el = item.locator("div[role='heading'], span.M7eMe, div.M7eMe").first
                if await title_el.count() == 0:
                    continue

                title = (await title_el.text_content()).strip().upper()
                # Quitar asteriscos de campos obligatorios
                title_clean = re.sub(r'[*]', '', title).strip()

                # A. Carnet / CUI / Registro
                if any(k in title_clean for k in ["CARNET", "CARNE", "REGISTRO", "CUI"]):
                    inp = item.locator("input[type='text']")
                    if await inp.count() > 0:
                        await inp.fill(str(datos_finales["carnet"]))
                        logger.info(f"   [Campo {i+1}] Carnet completado: {datos_finales['carnet']}")
                        campos_llenados += 1

                # B. Nombre Completo
                elif any(k in title_clean for k in ["NOMBRE", "ESTUDIANTE", "ALUMNO"]):
                    inp = item.locator("input[type='text']")
                    if await inp.count() > 0:
                        await inp.fill(datos_finales["nombre"])
                        logger.info(f"   [Campo {i+1}] Nombre completado: {datos_finales['nombre']}")
                        campos_llenados += 1

                # C. Correo Institucional
                elif any(k in title_clean for k in ["CORREO", "EMAIL", "MAIL"]):
                    inp = item.locator("input[type='text'], input[type='email']")
                    if await inp.count() > 0:
                        await inp.fill(datos_finales["correo"])
                        logger.info(f"   [Campo {i+1}] Correo completado: {datos_finales['correo']}")
                        campos_llenados += 1

                # D. Número de Grupo
                elif any(k in title_clean for k in ["GRUPO", "EQUIPO"]):
                    inp = item.locator("input[type='text']")
                    if await inp.count() > 0:
                        await inp.fill(str(datos_finales["grupo"]))
                        logger.info(f"   [Campo {i+1}] Grupo completado: {datos_finales['grupo']}")
                        campos_llenados += 1

                # E. Sección (Opciones Radio o Texto)
                elif any(k in title_clean for k in ["SECCION", "SECCIÓN"]):
                    sec_target = datos_finales["seccion"].strip().upper()
                    # Si es selección múltiple (radio button)
                    radio = item.locator(f"div[role='radio'][data-value='{sec_target}'], div[role='radio']:has-text('{sec_target}')").first
                    if await radio.count() > 0:
                        await radio.click()
                        logger.info(f"   [Campo {i+1}] Sección seleccionada (radio): {sec_target}")
                        campos_llenados += 1
                    else:
                        inp = item.locator("input[type='text']")
                        if await inp.count() > 0:
                            await inp.fill(sec_target)
                            logger.info(f"   [Campo {i+1}] Sección completada (texto): {sec_target}")
                            campos_llenados += 1

                # F. Enlace al repositorio de GitHub
                elif any(k in title_clean for k in ["REPO", "GITHUB", "ENLACE", "LINK", "URL"]):
                    inp = item.locator("input[type='text']")
                    if await inp.count() > 0:
                        await inp.fill(datos_finales["repo"])
                        logger.info(f"   [Campo {i+1}] Repositorio GitHub completado: {datos_finales['repo']}")
                        campos_llenados += 1

                # G. Estado del Agente / Comentarios
                elif any(k in title_clean for k in ["ESTADO", "AGENTE", "COMENTARIO", "OBSERVACION", "DESCRIPCION"]):
                    inp = item.locator("textarea, input[type='text']")
                    if await inp.count() > 0:
                        await inp.fill(datos_finales["estado"])
                        logger.info(f"   [Campo {i+1}] Estado del agente completado.")
                        campos_llenados += 1

            if campos_llenados == 0:
                return {
                    "success": False,
                    "data": None,
                    "message": "No se pudieron emparejar las preguntas del formulario con los datos requeridos."
                }

            # 3. Validar y presionar botón de enviar
            logger.info("3. Enviando formulario...")
            submit_btn = page.locator("div[role='button']:has-text('Enviar'), span:has-text('Enviar'), div[role='button']:has-text('Submit')").first
            if await submit_btn.count() == 0:
                return {
                    "success": False,
                    "data": None,
                    "message": "No se encontró el botón de envío en el formulario."
                }

            await submit_btn.click()

            # 4. Esperar y verificar mensaje de confirmación
            logger.info("4. Esperando confirmación de respuesta...")
            confirm_loc = page.locator(
                ".freebirdFormviewerViewResponseConfirmationMessage, "
                "div:has-text('Se registró tu respuesta'), "
                "div:has-text('Se ha registrado tu respuesta'), "
                "div:has-text('Your response has been recorded')"
            )
            await confirm_loc.first.wait_for(timeout=15000)
            confirm_msg = "Se registró tu respuesta exitosamente."

            logger.info(f"Formulario enviado con éxito: {confirm_msg}")

            return {
                "success": True,
                "data": datos_finales,
                "mensaje_confirmacion": confirm_msg,
                "message": f"Formulario institucional completado y enviado exitosamente ({campos_llenados} campos registrados)."
            }

    except Exception as e:
        logger.error(f"Error al completar el formulario: {str(e)}")
        return {
            "success": False,
            "data": None,
            "error": str(e),
            "message": f"Error al completar el formulario: {str(e)}"
        }
