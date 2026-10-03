import asyncio
import sys

# Asegurar codificación utf-8 en la consola de Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rpa.service import RPAService
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)

async def run_menu():
    print("=" * 60)
    print("      AURA RPA - PRUEBA DE PROCESOS INDEPENDIENTES     ")
    print("=" * 60)
    print("1. Listar procesos disponibles (Comando /rpa)")
    print("2. Probar RPA 1: Consultar horario (Indice arriba )")
    print("3. Probar RPA 2: Descargar material en UEDI (Indice abajo )")
    print("4. Probar RPA 3: Completar formulario (Escritura )")
    print("5. Probar todos los procesos secuencialmente")
    print("0. Salir")
    print("=" * 60)

    while True:
        try:
            opcion = input("\nSelecciona una opcion (0-5): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo...")
            break

        if opcion == "1":
            procesos = RPAService.listar_procesos()
            print("\nProcesos registrados:")
            for p in procesos:
                print(f" - {p['nombre']}: {p['descripcion']}")

        elif opcion == "2":
            print("\n[RPA 1] Ejecutando consulta de horario...")
            res = await RPAService.ejecutar_horario(headless=True)
            print(f"Resultado: {res}")

        elif opcion == "3":
            print("\n[RPA 2] Ejecutando descarga de material en UEDI...")
            res = await RPAService.ejecutar_descarga_material(headless=True)
            print(f"Resultado: {res}")

        elif opcion == "4":
            print("\n[RPA 3] Ejecutando completado de formulario...")
            res = await RPAService.ejecutar_formulario(headless=True)
            print(f"Resultado: {res}")

        elif opcion == "5":
            print("\n--- Ejecutando RPA 1 ---")
            print(await RPAService.ejecutar_horario(headless=True))
            print("\n--- Ejecutando RPA 2 ---")
            print(await RPAService.ejecutar_descarga_material(headless=True))
            print("\n--- Ejecutando RPA 3 ---")
            print(await RPAService.ejecutar_formulario(headless=True))

        elif opcion == "0":
            print("Finalizado.")
            break
        else:
            print("Opcion invalida.")

if __name__ == "__main__":
    asyncio.run(run_menu())
