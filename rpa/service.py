import asyncio
from typing import Dict, Any, List
from rpa.horario import consultar_horario
from rpa.material import descargar_material
from rpa.formulario import completar_formulario

class RPAService:
    """
    Servicio central de RPA para el agente AURA.
    Esta es la interfaz pública que consumirán:
    - Persona 1 (Orquestador / Raspberry Pi) al reconocer los gestos.
    - Persona 4 (Bot de Telegram) con los comandos /rpa y ejecución de acciones.
    """

    PROCESOS_DISPONIBLES = [
        {
            "id": "horario",
            "nombre": "Consultar horario",
            "gesto": "Indice hacia arriba",
            "descripcion": "Consulta horario de clase magistral y laboratorio en el portal académico."
        },
        {
            "id": "descargar_material",
            "nombre": "Descargar material",
            "gesto": "Indice hacia abajo",
            "descripcion": "Ingresa a UEDI y descarga el enunciado del Proyecto 2."
        },
        {
            "id": "completar_formulario",
            "nombre": "Completar formulario",
            "gesto": "Simular escritura con el indice",
            "descripcion": "Llena y valida los campos requeridos en el formulario de auxiliares."
        }
    ]

    @classmethod
    def listar_procesos(cls) -> List[Dict[str, str]]:
        """Retorna la lista de procesos RPA disponibles (ideal para comando /rpa en Telegram)."""
        return cls.PROCESOS_DISPONIBLES

    @staticmethod
    async def ejecutar_horario(headless: bool = True) -> Dict[str, Any]:
        """Ejecuta el proceso RPA 1 de consulta de horario."""
        return await consultar_horario(headless=headless)

    @staticmethod
    async def ejecutar_descarga_material(headless: bool = True) -> Dict[str, Any]:
        """Ejecuta el proceso RPA 2 de descarga de enunciado en UEDI."""
        return await descargar_material(headless=headless)

    @staticmethod
    async def ejecutar_formulario(datos: Dict[str, str] = None, headless: bool = True) -> Dict[str, Any]:
        """Ejecuta el proceso RPA 3 de llenado de formulario."""
        return await completar_formulario(datos=datos, headless=headless)

    @classmethod
    async def ejecutar_por_gesto(cls, gesto: str, headless: bool = True) -> Dict[str, Any]:
        """
        Despacha automáticamente el proceso según el gesto detectado.
        """
        gesto_norm = gesto.lower()
        if "arriba" in gesto_norm or "indice_arriba" in gesto_norm or "horario" in gesto_norm:
            return await cls.ejecutar_horario(headless=headless)
        elif "abajo" in gesto_norm or "indice_abajo" in gesto_norm or "material" in gesto_norm:
            return await cls.ejecutar_descarga_material(headless=headless)
        elif "escribir" in gesto_norm or "formulario" in gesto_norm or "escritura" in gesto_norm:
            return await cls.ejecutar_formulario(headless=headless)
        else:
            return {
                "success": False,
                "message": f"No hay ningún proceso RPA asociado al gesto: {gesto}"
            }

    # Métodos síncronos de conveniencia para scripts simples
    @classmethod
    def sync_ejecutar_horario(cls) -> Dict[str, Any]:
        return asyncio.run(cls.ejecutar_horario())

    @classmethod
    def sync_ejecutar_descarga_material(cls) -> Dict[str, Any]:
        return asyncio.run(cls.ejecutar_descarga_material())

    @classmethod
    def sync_ejecutar_formulario(cls) -> Dict[str, Any]:
        return asyncio.run(cls.ejecutar_formulario())
