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
    RPA 3: Completar automáticamente formulario de pruebas RPA.
    Gesto asociado: Simular escritura con el índice (WRITE_GESTURE)

    1. Accede al formulario de Google Forms configurado en .env o config.py.
    2. Identifica dinámicamente los campos requeridos:
       - Número de grupo
       - Nombre completo de los integrantes
       - Módulo del proyecto evaluado (1, 2, 3)
       - Proceso RPA a registrar
       - Validación de automatización (Sí / No / Tal vez)
       - Fecha de ejecución en tiempo real (Día / Mes / Año)
       - Hora de ejecución en tiempo real (Hora / Minuto / AM-PM)
       - Soporte para campos de respaldo (Carnet, Correo, Sección, Repo, Estado).
    3. Rellena las respuestas y valida los campos requeridos.
    4. Envía el formulario y confirma el mensaje de respuesta de Google Forms.
    """
    # Recargar .env en caliente por si se actualizó FORMULARIO_URL recientemente
    load_dotenv(BASE_DIR / ".env", override=True)

    target_url = os.getenv("FORMULARIO_URL", FORMULARIO_URL).strip()
    if not target_url:
        logger.error("FORMULARIO_URL no configurada en el archivo .env ni en config.py")
        return {
            "success": False,
            "data": None,
            "message": "FORMULARIO_URL no configurada. Define la URL del formulario en el archivo .env"
        }

    # Fecha y hora en tiempo real
    now = datetime.now()
    dia_str = now.strftime("%d")
    mes_str = now.strftime("%m")
    ano_str = now.strftime("%Y")
    fecha_hoy = f"{dia_str}/{mes_str}/{ano_str}"

    # Hora en formato 12 horas y AM/PM (Google Forms usa reloj de 12H)
    hora_12 = now.strftime("%I").lstrip("0") or "12"  # 1 a 12 sin cero a la izquierda
    minuto_str = now.strftime("%M")
    periodo_str = now.strftime("%p")  # AM o PM

    user_carnet = os.getenv("ESTUDIANTE_CARNET", ESTUDIANTE_CARNET or USAC_USER)
    nombre_estudiante = os.getenv("ESTUDIANTE_NOMBRE", ESTUDIANTE_NOMBRE)

    datos_finales = {
        "carnet": str(user_carnet),
        "nombre": str(nombre_estudiante),
        "integrantes": str(os.getenv("INTEGRANTES_GRUPO", INTEGRANTES_GRUPO or nombre_estudiante)),
        "correo": str(os.getenv("ESTUDIANTE_CORREO", ESTUDIANTE_CORREO or (f"{user_carnet}@ingenieria.usac.edu.gt" if user_carnet else ""))),
        "grupo": str(os.getenv("GRUPO_NUMERO", GRUPO_NUMERO)),
        "seccion": str(os.getenv("SECCION_LAB", SECCION_LAB)),
        "modulo": str(os.getenv("MODULO_EVALUADO", MODULO_EVALUADO)),
        "proceso": str(os.getenv("PROCESO_RPA_NOMBRE", PROCESO_RPA_NOMBRE)),
        "automatizacion_correcta": str(os.getenv("AUTOMATIZACION_CORRECTA", AUTOMATIZACION_CORRECTA)),
        "fecha": fecha_hoy,
        "hora": f"{hora_12}:{minuto_str} {periodo_str}",
        "repo": str(os.getenv("REPO_GITHUB", REPO_GITHUB)),
        "estado": str(os.getenv("ESTADO_AGENTE", ESTADO_AGENTE_DEFAULT))
    }

    if datos:
        for k, v in datos.items():
            if v is not None:
                datos_finales[k] = str(v)

    logger.info(f"Iniciando RPA 3: Completar formulario en: {target_url}")
    logger.info(
        f"Datos a registrar: Grupo={datos_finales['grupo']}, Modulo={datos_finales['modulo']}, "
        f"Proceso={datos_finales['proceso']}, Fecha={fecha_hoy}, Hora={datos_finales['hora']}"
    )

    try:
        async with get_browser_session(headless=headless, block_heavy_resources=True) as (page, _):
            # 1. Navegar al formulario
            logger.info("1. Cargando formulario de Google Forms...")
            await page.goto(target_url, timeout=60000, wait_until="domcontentloaded")

            # 2. Localizar preguntas (esperando que estén adjuntas al DOM con margen térmico)
            logger.info("2. Esperando que el formulario se renderice en el DOM...")
            items = page.locator("div[role='listitem'], div.Qr7Oae")
            try:
                await items.first.wait_for(state="attached", timeout=60000)
            except Exception:
                await page.locator("form, input[type='text']").first.wait_for(state="attached", timeout=30000)

            # Pequeña pausa para estabilizar hidratación de scripts de Google
            await page.wait_for_timeout(1000)

            total_items = await items.count()
            logger.info(f"   Formulario cargado. Total de preguntas encontradas: {total_items}")

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
                        logger.info(f"   [Campo {i+1}] Integrantes completado: {datos_finales['integrantes'][:35]}...")
                        campos_llenados += 1

                # --- 3. Módulo del proyecto evaluado ---
                elif any(k in title_clean for k in ["MÓDULO", "MODULO"]):
                    target_mod = str(datos_finales["modulo"]).strip()
                    radio = item.locator(
                        f"div[role='radio'][data-value='{target_mod}'], "
                        f"div[role='radio'][aria-label='{target_mod}'], "
                        f"div[role='radio']:has-text('{target_mod}')"
                    ).first
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
                    if target_resp in ["si", "sí", "yes", "true", "1"]:
                        val_sel = "Sí"
                    elif target_resp in ["no", "false", "0"]:
                        val_sel = "No"
                    else:
                        val_sel = "Tal vez"

                    radio = item.locator(
                        f"div[role='radio'][data-value='{val_sel}'], "
                        f"div[role='radio'][aria-label='{val_sel}'], "
                        f"div[role='radio']:has-text('{val_sel}')"
                    ).first
                    if await radio.count() > 0:
                        await radio.click()
                        logger.info(f"   [Campo {i+1}] Estado automatización seleccionado (radio): {val_sel}")
                        campos_llenados += 1

                # --- 6. Fecha de ejecución de la prueba ---
                elif "FECHA" in title_clean:
                    inp_date = item.locator("input[type='date']")
                    if await inp_date.count() > 0:
                        await inp_date.fill(f"{ano_str}-{mes_str}-{dia_str}")
                        logger.info(f"   [Campo {i+1}] Fecha completada (input date): {dia_str}/{mes_str}/{ano_str}")
                        campos_llenados += 1
                    else:
                        # Google Forms en desktop usa 3 inputs individuales (Día, Mes, Año)
                        inp_dia = item.locator("input[aria-label*='Día'], input[aria-label*='Dia'], input[aria-label*='Day']").first
                        inp_mes = item.locator("input[aria-label*='Mes'], input[aria-label*='Month']").first
                        inp_ano = item.locator("input[aria-label*='Año'], input[aria-label*='Ano'], input[aria-label*='Year']").first

                        if await inp_dia.count() > 0 and await inp_mes.count() > 0 and await inp_ano.count() > 0:
                            await inp_dia.fill(dia_str)
                            await inp_mes.fill(mes_str)
                            await inp_ano.fill(ano_str)
                            logger.info(f"   [Campo {i+1}] Fecha completada (Día/Mes/Año): {dia_str}/{mes_str}/{ano_str}")
                            campos_llenados += 1
                        else:
                            # Fallback por orden de inputs en la pregunta
                            text_inputs = item.locator("input[type='text']")
                            if await text_inputs.count() >= 3:
                                await text_inputs.nth(0).fill(dia_str)
                                await text_inputs.nth(1).fill(mes_str)
                                await text_inputs.nth(2).fill(ano_str)
                                logger.info(f"   [Campo {i+1}] Fecha completada (por índice): {dia_str}/{mes_str}/{ano_str}")
                                campos_llenados += 1

                # --- 7. Hora de ejecución ---
                elif "HORA" in title_clean:
                    inpHora = item.locator("input[aria-label*='Hora'], input[aria-label*='Hour']").first
                    inpMin = item.locator("input[aria-label*='Minuto'], input[aria-label*='Minute']").first

                    if await inpHora.count() > 0 and await inpMin.count() > 0:
                        await inpHora.fill(hora_12)
                        await inpMin.fill(minuto_str)
                    else:
                        text_inputs = item.locator("input[type='text']")
                        if await text_inputs.count() >= 2:
                            await text_inputs.nth(0).fill(hora_12)
                            await text_inputs.nth(1).fill(minuto_str)

                    # Selector AM / PM si está presente
                    if periodo_str == "PM":
                        listbox = item.locator("div[role='listbox']").first
                        if await listbox.count() > 0:
                            try:
                                await listbox.click()
                                await page.wait_for_timeout(300)
                                pm_opt = page.locator("div[role='option'][data-value='PM'], span:text-is('PM')").first
                                if await pm_opt.count() > 0:
                                    await pm_opt.click()
                            except Exception as ex_ampm:
                                logger.debug(f"Aviso al seleccionar PM: {ex_ampm}")

                    logger.info(f"   [Campo {i+1}] Hora completada: {hora_12}:{minuto_str} {periodo_str}")
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
            submit_btn = page.locator(
                "div[role='button']:has-text('Enviar'), "
                "span:has-text('Enviar'), "
                "div[role='button']:has-text('Submit'), "
                "div[role='button'][aria-label='Submit'], "
                "div[role='button'][aria-label='Enviar'], "
                "button[type='submit']"
            ).first

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
            try:
                await confirm_loc.first.wait_for(timeout=25000)
                confirm_msg = "Se registró tu respuesta exitosamente."
            except Exception:
                if "formResponse" in page.url:
                    confirm_msg = "Formulario enviado (página de confirmación recibida)."
                else:
                    raise RuntimeError("No se detectó el mensaje de confirmación tras presionar Enviar.")

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
