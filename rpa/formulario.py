import os
import re
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from rpa.config import (
    BASE_DIR,
    FORMULARIO_URL,
    USAC_USER,
    ESTUDIANTE_CARNET,
    ESTUDIANTE_NOMBRE,
    INTEGRANTES_GRUPO,
    ESTUDIANTE_CORREO,
    GRUPO_NUMERO,
    SECCION_LAB,
    MODULO_EVALUADO,
    PROCESO_RPA_NOMBRE,
    AUTOMATIZACION_CORRECTA,
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
    2. Identifica dinámicamente todos los tipos de preguntas:
       - Número de grupo
       - Nombre completo de los integrantes
       - Módulo del proyecto evaluado 
       - Proceso RPA a registrar
       - Validación de automatización 
       - Fecha de ejecución en tiempo real 
       - Hora de ejecución en tiempo real 
       - Compatibilidad con Carnet, Correo, Sección, Repo y Estado.
    3. Rellena las respuestas y valida los campos requeridos.
    4. Envía el formulario y confirma el mensaje de respuesta de Google Forms.
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

    # Fecha y hora en tiempo real
    now = datetime.now()
    fecha_hoy = now.strftime("%Y-%m-%d")
    hora_24 = now.strftime("%H")
    minuto = now.strftime("%M")

    user_carnet = os.getenv("ESTUDIANTE_CARNET", ESTUDIANTE_CARNET or USAC_USER)
    nombre_estudiante = os.getenv("ESTUDIANTE_NOMBRE", ESTUDIANTE_NOMBRE)

    datos_finales = {
        "carnet": user_carnet,
        "nombre": nombre_estudiante,
        "integrantes": os.getenv("INTEGRANTES_GRUPO", INTEGRANTES_GRUPO or nombre_estudiante),
        "correo": os.getenv("ESTUDIANTE_CORREO", ESTUDIANTE_CORREO or f"{user_carnet}@ingenieria.usac.edu.gt"),
        "grupo": os.getenv("GRUPO_NUMERO", GRUPO_NUMERO),
        "seccion": os.getenv("SECCION_LAB", SECCION_LAB),
        "modulo": os.getenv("MODULO_EVALUADO", MODULO_EVALUADO),
        "proceso": os.getenv("PROCESO_RPA_NOMBRE", PROCESO_RPA_NOMBRE),
        "automatizacion_correcta": os.getenv("AUTOMATIZACION_CORRECTA", AUTOMATIZACION_CORRECTA),
        "fecha": fecha_hoy,
        "hora": f"{hora_24}:{minuto}",
        "repo": os.getenv("REPO_GITHUB", REPO_GITHUB),
        "estado": os.getenv("ESTADO_AGENTE", ESTADO_AGENTE_DEFAULT)
    }

    if datos:
        datos_finales.update(datos)

    logger.info(f"Iniciando RPA 3: Completar formulario en: {target_url}")
    logger.info(f"Datos a registrar: Grupo={datos_finales['grupo']}, Integrantes={datos_finales['integrantes']}, Modulo={datos_finales['modulo']}, Proceso={datos_finales['proceso']}")

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
                title_clean = re.sub(r'[*<>\n\r]', ' ', title).strip()

                # --- 1. Número de Grupo ---
                if "NUMERO DE GRUPO" in title_clean or ("GRUPO" in title_clean and "INTEGRANTES" not in title_clean):
                    inp = item.locator("input[type='text']")
                    if await inp.count() > 0:
                        await inp.fill(str(datos_finales["grupo"]))
                        logger.info(f"   [Campo {i+1}] Grupo completado: {datos_finales['grupo']}")
                        campos_llenados += 1

                # --- 2. Integrantes del Grupo o Nombre Completo ---
                elif any(k in title_clean for k in ["INTEGRANTES", "NOMBRE"]):
                    inp = item.locator("input[type='text'], textarea")
                    if await inp.count() > 0:
                        await inp.fill(datos_finales["integrantes"])
                        logger.info(f"   [Campo {i+1}] Integrantes completado: {datos_finales['integrantes']}")
                        campos_llenados += 1

                # --- 3. Módulo del proyecto ---
                elif any(k in title_clean for k in ["MÓDULO", "MODULO"]):
                    target_mod = str(datos_finales["modulo"]).strip()
                    radio = item.locator(f"div[role='radio'][data-value='{target_mod}'], div[role='radio']:has-text('{target_mod}')").first
                    if await radio.count() > 0:
                        await radio.click()
                        logger.info(f"   [Campo {i+1}] Módulo seleccionado (radio): {target_mod}")
                        campos_llenados += 1

                # --- 4. Proceso RPA a registrar ---
                elif any(k in title_clean for k in ["PROCESO RPA", "PROCESO"]):
                    inp = item.locator("input[type='text'], textarea")
                    if await inp.count() > 0:
                        await inp.fill(datos_finales["proceso"])
                        logger.info(f"   [Campo {i+1}] Proceso RPA completado: {datos_finales['proceso']}")
                        campos_llenados += 1

                # --- 5. Automatización completada correctamente ---
                elif any(k in title_clean for k in ["CORRECTAMENTE", "AUTOMATIZACIÓN", "AUTOMATIZACION"]):
                    target_resp = datos_finales["automatizacion_correcta"].strip().lower()
                    radio = item.locator(f"div[role='radio'][data-value='{target_resp}'], div[role='radio']:has-text('{target_resp}')").first
                    if await radio.count() > 0:
                        await radio.click()
                        logger.info(f"   [Campo {i+1}] Estado automatización seleccionado (radio): {target_resp}")
                        campos_llenados += 1

                # --- 6. Fecha de ejecución ---
                elif "FECHA" in title_clean:
                    inp_date = item.locator("input[type='date']")
                    if await inp_date.count() > 0:
                        await inp_date.fill(fecha_hoy)
                        logger.info(f"   [Campo {i+1}] Fecha completada: {fecha_hoy}")
                        campos_llenados += 1

                # --- 7. Hora de ejecución ---
                elif "HORA" in title_clean:
                    inpHora = item.locator("input[aria-label='Hora']")
                    if await inpHora.count() > 0:
                        await inpHora.fill(hora_24)

                    inpMin = item.locator("input[aria-label='Minuto']")
                    if await inpMin.count() > 0:
                        await inpMin.fill(minuto)

                    logger.info(f"   [Campo {i+1}] Hora completada (24H): {hora_24}:{minuto}")
                    campos_llenados += 1

                # --- Campos anteriores de soporte (Carnet, Correo, Sección, Repo, Estado) ---
                elif any(k in title_clean for k in ["CARNET", "CARNE", "REGISTRO", "CUI"]):
                    inp = item.locator("input[type='text']")
                    if await inp.count() > 0:
                        await inp.fill(str(datos_finales["carnet"]))
                        logger.info(f"   [Campo {i+1}] Carnet completado: {datos_finales['carnet']}")
                        campos_llenados += 1

                elif any(k in title_clean for k in ["CORREO", "EMAIL"]):
                    inp = item.locator("input[type='text'], input[type='email']")
                    if await inp.count() > 0:
                        await inp.fill(datos_finales["correo"])
                        logger.info(f"   [Campo {i+1}] Correo completado: {datos_finales['correo']}")
                        campos_llenados += 1

                elif any(k in title_clean for k in ["SECCION", "SECCIÓN"]):
                    sec_target = datos_finales["seccion"].strip().upper()
                    radio = item.locator(f"div[role='radio'][data-value='{sec_target}'], div[role='radio']:has-text('{sec_target}')").first
                    if await radio.count() > 0:
                        await radio.click()
                    else:
                        inp = item.locator("input[type='text']")
                        if await inp.count() > 0:
                            await inp.fill(sec_target)
                    logger.info(f"   [Campo {i+1}] Sección completada: {sec_target}")
                    campos_llenados += 1

                elif any(k in title_clean for k in ["REPO", "GITHUB", "ENLACE", "LINK", "URL"]):
                    inp = item.locator("input[type='text']")
                    if await inp.count() > 0:
                        await inp.fill(datos_finales["repo"])
                        logger.info(f"   [Campo {i+1}] Repositorio completado: {datos_finales['repo']}")
                        campos_llenados += 1

                elif any(k in title_clean for k in ["ESTADO", "AGENTE", "COMENTARIO"]):
                    inp = item.locator("textarea, input[type='text']")
                    if await inp.count() > 0:
                        await inp.fill(datos_finales["estado"])
                        logger.info(f"   [Campo {i+1}] Estado completado.")
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
