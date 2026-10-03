import os
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

@asynccontextmanager
async def get_browser_session(headless: bool = True, block_heavy_resources: bool = True):
    # Si en Raspberry Pi se usa un chromium del sistema, puede especificarse aquí
    system_chromium = os.getenv("CHROMIUM_EXECUTABLE_PATH", None)
    # Se configuran los argumentos del navegador
    launch_args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-extensions",
        "--no-first-run",
        "--no-default-browser-check",
    ]

    async with async_playwright() as p:
        # Se inicia el navegador Chromium
        browser: Browser = await p.chromium.launch(
            headless=headless,
            executable_path=system_chromium if system_chromium else None,
            args=launch_args
        )
        # Se configuran las opciones del navegador
        context: BrowserContext = await browser.new_context(
            accept_downloads=True,
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        # Se crea una nueva pagina
        page: Page = await context.new_page()

        # Optimizacion: bloquear imagenes y fuentes para reducir consumo de RAM en la Raspberry Pi
        if block_heavy_resources:
            async def intercept_route(route):
                resource_type = route.request.resource_type
                if resource_type in ["image", "media", "font"]:
                    await route.abort()
                else:
                    await route.continue_()
            # Se bloquean las imagenes y fuentes
            await page.route("**/*", intercept_route)
        # Se ejecuta el navegador
        try:
            yield page, context
        finally:
            await context.close()
            await browser.close()
