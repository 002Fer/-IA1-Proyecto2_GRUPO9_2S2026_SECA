import os
import logging
from typing import Dict, Any, Optional
from rpa.config import PORTAL_ACADEMICO_URL, USAC_USER, USAC_PASSWORD
from rpa.browser import get_browser_session

logger = logging.getLogger("RPA_Horario")

async def consultar_horario(
    user: Optional[str] = None,
    password: Optional[str] = None,
    curso_busqueda: str = "INTELIGENCIA ARTIFICIAL 1",
    headless: bool = True
) -> Dict[str, Any]:
    """
    RPA 1: Consultar horario real en el portal académico / infoestudiantes de FIUSAC.
    Gesto asociado: Índice hacia arriba

    1. Ingresa a https://dashboardacademico.ingenieria.usac.edu.gt/
    2. Autentica con Keycloak SSO institucional.
    3. Selecciona la carrera de Ciencias y Sistemas.
    4. Consulta la sección de cursos asignados y horarios en infoestudiantes.
    5. Extrae el horario real de magistral y laboratorio para el curso especificado.
    """
    username = user or USAC_USER
    pwd = password or USAC_PASSWORD

    logger.info("Iniciando consulta de horario real en portal academico FIUSAC...")

    try:
        async with get_browser_session(headless=headless, block_heavy_resources=True) as (page, _):
            # 1. Ingresar al dashboard academico
            logger.info("1. Navegando al Dashboard Academico...")
            await page.goto(PORTAL_ACADEMICO_URL, timeout=60000, wait_until="domcontentloaded")

            # 2. Autenticacion en Keycloak SSO si es requerida
            if "auth.ingenieria.usac.edu.gt" in page.url or await page.locator("#username").count() > 0:
                logger.info(f"Autenticando en Keycloak para usuario: {username}...")
                await page.locator("#username").fill(username, timeout=25000)
                await page.locator("#password").fill(pwd, timeout=25000)
                await page.click("#kc-login")
                
                # Esperar a que Keycloak procese el login (puede tardar en la Raspberry Pi)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    pass

                # Verificar si Keycloak arrojó un error de credenciales
                error_locators = page.locator(".alert-error, #input-error, .kc-feedback-text, span.kc-error")
                if await error_locators.count() > 0:
                    error_texto = (await error_locators.first.inner_text()).strip()
                    logger.error(f"Error devuelto por Keycloak: {error_texto}")
                    return {
                        "success": False,
                        "data": None,
                        "message": f"Error de autenticación en portal USAC: {error_texto}. Revisa USAC_USER y USAC_PASSWORD en tu .env"
                    }

                # Esperar hasta que se complete la redirección fuera de Keycloak
                for _ in range(10):
                    if "auth.ingenieria.usac.edu.gt" not in page.url:
                        break
                    await page.wait_for_timeout(1000)

                logger.info(f"URL tras autenticacion: {page.url}")

            # 3. Seleccionar carrera solo si existe carreras simultáneas
            if "carrera" in page.url:
                logger.info("Pantalla de seleccion de carrera detectada (carreras simultaneas)...")
                sistemas_link = page.locator("a[href*='carrera=09'], a:has-text('CIENCIAS Y SISTEMAS')")
                if await sistemas_link.count() > 0:
                    await sistemas_link.first.click()
                else:
                    primera_opcion = page.locator("a:has-text('Seleccionar Carrera')")
                    if await primera_opcion.count() > 0:
                        await primera_opcion.first.click()

                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                except Exception:
                    pass
                await page.wait_for_timeout(2000)
            elif "dashboardacademico" in page.url:
                logger.info("Usuario autenticado en Dashboard Academico exitosamente.")

            # 4. Navegar a datosPersonales / infoestudiantes
            logger.info("2. Accediendo a infoestudiantes para consultar asignacion...")
            await page.goto("https://infoestudiantes.ingenieria.usac.edu.gt/datosPersonales", timeout=75000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            # Si infoestudiantes pide login SSO de nuevo
            if "auth.ingenieria.usac.edu.gt" in page.url or await page.locator("#username").count() > 0:
                logger.info("Infoestudiantes requiere autenticacion SSO secundaria...")
                if await page.locator("#username").count() > 0:
                    await page.fill("#username", username)
                    await page.fill("#password", pwd)
                    await page.click("#kc-login")
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=15000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(3000)

            # 5. Configurar periodo y enviar consulta
            logger.info("3. Consultando horarios de cursos asignados (Segundo Semestre)...")
            await page.evaluate("""() => {
                const p = document.getElementById('periodocr') || document.querySelector('select[name="periodocr"]');
                if (p) p.value = '05'; // Segundo Semestre
                const y = document.getElementById('aniocr') || document.querySelector('select[name="aniocr"]');
                if (y && y.options.length > 0) y.value = y.options[0].value;
                if (typeof viewFormAction === 'function') {
                    viewFormAction();
                } else if (document.frmHorario) {
                    document.frmHorario.action = "/horarioCursosAsignados";
                    document.frmHorario.submit();
                }
            }""")

            await page.wait_for_timeout(4000)
            logger.info(f"Pagina de horarios cargada: {page.url}")

            # 6. Parsear la tabla de horarios de cursos asignados
            filas_datos = await page.evaluate("""() => {
                const rows = Array.from(document.querySelectorAll('table tr'));
                const resultados = [];
                for (let r of rows) {
                    const text = r.innerText.trim();
                    if (text && !text.startsWith('Código') && !text.startsWith('Lu\\tMa')) {
                        const cols = text.split('\\t').map(c => c.trim());
                        if (cols.length >= 7) {
                            resultados.push({
                                codigo: cols[0],
                                nombre: cols[1],
                                seccion: cols[2],
                                edificio: cols[3],
                                salon: cols[4],
                                inicio: cols[5],
                                fin: cols[6]
                            });
                        }
                    }
                }
                return resultados;
            }""")

            logger.info(f"Cursos asignados encontrados en vivo: {len(filas_datos)}")

            # 7. Filtrar por el curso solicitado
            ia_filas = [
                f for f in filas_datos 
                if curso_busqueda.upper() in f.get("nombre", "").upper()
            ]

            if not ia_filas:
                cursos_disponibles = [f.get("nombre") for f in filas_datos]
                return {
                    "success": False,
                    "data": None,
                    "message": f"No se encontró el curso '{curso_busqueda}' en la asignación oficial.",
                    "cursos_disponibles": cursos_disponibles
                }

            # Asignar las sesiones encontradas en la tabla oficial (Fila 1: Magistral, Fila 2: Laboratorio)
            horario_magistral = f"{ia_filas[0]['inicio']} - {ia_filas[0]['fin']}" if len(ia_filas) > 0 else "No asignado"
            horario_lab = f"{ia_filas[1]['inicio']} - {ia_filas[1]['fin']}" if len(ia_filas) > 1 else "No asignado"

            horario_real = {
                "curso": ia_filas[0]["nombre"],
                "codigo": ia_filas[0]["codigo"],
                "seccion": ia_filas[0]["seccion"],
                "magistral": horario_magistral,
                "laboratorio": horario_lab,
                "sesiones_encontradas": len(ia_filas),
                "fuente": "infoestudiantes.ingenieria.usac.edu.gt (En vivo)",
                "total_cursos_asignados": len(filas_datos)
            }

            msg = (
                f"Horario obtenido en tiempo real: "
                f"Magistral ({horario_real['magistral']}), "
                f"Laboratorio ({horario_real['laboratorio']})"
            )
            logger.info(msg)

            return {
                "success": True,
                "data": horario_real,
                "message": msg
            }

    except Exception as e:
        logger.error(f"Error al consultar horario en vivo: {str(e)}")
        return {
            "success": False,
            "data": None,
            "error": str(e),
            "message": f"Error al consultar horario en el portal académico: {str(e)}"
        }
