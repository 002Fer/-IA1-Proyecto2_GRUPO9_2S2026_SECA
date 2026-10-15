import os
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

@asynccontextmanager
async def get_browser_session(headless: bool = True, block_heavy_resources: bool = True):
    # Si en Raspberry Pi se usa un chromium del sistema, puede especificarse aquí
    system_chromium = os.getenv("CHROMIUM_EXECUTABLE_PATH", None)
    # Se configuran los argumentos del navegador optimizados al maximo para Raspberry Pi
    launch_args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--disable-extensions",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-renderer-backgrounding",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-breakpad",
        "--disable-component-extensions-with-background-pages",
        "--disable-features=Translate,OptimizationHints,MediaRouter",
        "--disable-ipc-flooding-protection",
        "--blink-settings=imagesEnabled=false",
        "--mute-audio",
        "--js-flags=--max-old-space-size=128",
    ]

    import sys
    if sys.platform.startswith("linux"):
        launch_args.append("--single-process")
        launch_args.append("--no-zygote")

    async with async_playwright() as p:
        # Se inicia el navegador Chromium
        browser: Browser = await p.chromium.launch(
            headless=headless,
            executable_path=system_chromium if system_chromium else None,
            args=launch_args
        )
        # Se configuran las opciones del navegador con resolucion reducida para ahorrar RAM
        context: BrowserContext = await browser.new_context(
            accept_downloads=True,
            viewport={"width": 800, "height": 600},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        # Se crea una nueva pagina
        page: Page = await context.new_page()

        # Optimizacion: bloquear imagenes, videos, fuentes y analitica para reducir CPU y RAM
        if block_heavy_resources:
            async def intercept_route(route):
                resource_type = route.request.resource_type
                url = route.request.url.lower()
                if resource_type in ["image", "media", "font"] or any(k in url for k in ["google-analytics", "analytics", "stats", "telemetry"]):
                    await route.abort()
                else:
                    await route.continue_()
            # Se bloquean recursos pesados
            await page.route("**/*", intercept_route)
        # Se ejecuta el navegador
        try:
            yield page, context
        finally:
            await context.close()
            await browser.close()
