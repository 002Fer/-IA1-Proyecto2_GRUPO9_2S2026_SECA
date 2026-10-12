# AURA UI - Realidad Aumentada y Robot 2D

Este módulo implementa la capa visual del agente AURA correspondiente a Realidad Aumentada y Robot Virtual 2D.

Su objetivo es recibir la percepción generada por `VisionDetector`, representar visualmente el estado del agente y exponer una interfaz simple para que el orquestador general pueda integrarla sin conocer los detalles internos del módulo gráfico.

## Funcionalidades implementadas

- Robot virtual 2D.
- Ocho estados visuales diferenciados.
- Overlay de Realidad Aumentada.
- Landmarks de manos.
- Landmarks de pose.
- Bounding boxes de mano y persona.
- Panel de percepción, interpretación y acción.
- Estabilización temporal de presencia.
- Integración directa con `VisionDetector`.
- Estados de ejecución externa.
- Interfaz de alto nivel `AuraUI`.

## Estructura

```text
core/
└── states.py

ui/
├── __init__.py
├── overlay.py
├── robot.py
├── README.md
└── assets/
    ├── idle.png
    ├── greeting.png
    ├── detecting.png
    ├── thinking.png
    ├── executing.png
    ├── success.png
    ├── error.png
    └── goodbye.png
```

## Estados visuales

| Estado | Etiqueta visible | Uso |
| --- | --- | --- |
| `IDLE` | Esperando | No hay usuario confirmado |
| `GREETING` | Saludando | Persona recién detectada |
| `DETECTING` | Detectando | Esperando o detectando gesto |
| `THINKING` | Interpretando | Gesto reconocido |
| `EXECUTING` | Ejecutando | Acción externa en ejecución |
| `SUCCESS` | Exito | Acción finalizada correctamente |
| `ERROR` | Error | Acción externa fallida |
| `GOODBYE` | Despedida | Persona dejó la interacción |

## Interfaz pública recomendada

El punto de integración recomendado para el orquestador es `AuraUI`.

```python
from ui import AuraUI

aura_ui = AuraUI()
```

La misma instancia de `AuraUI` debe mantenerse durante todo el ciclo de ejecución.

No debe crearse una instancia nueva en cada frame, porque internamente se conserva información temporal utilizada para estabilizar la presencia y controlar las transiciones entre estados.

## Integración mínima con VisionDetector

```python
import cv2

from ui import AuraUI
from vision.detector import VisionDetector


detector = VisionDetector()
aura_ui = AuraUI()

try:
    detector.open()

    while True:
        vision_result = detector.process()

        ui_result = aura_ui.process(
            vision_result
        )

        frame = ui_result["frame"]

        cv2.imshow(
            "AURA",
            frame
        )

        key = cv2.waitKey(1) & 0xFF

        if key in (
            ord("q"),
            ord("Q")
        ):
            break

finally:
    detector.release()
    cv2.destroyAllWindows()
```

## Contrato de entrada desde VisionDetector

`AuraUI.process()` recibe directamente el diccionario generado por:

```python
VisionDetector.process()
```

La estructura esperada es:

```python
{
    "person_detected": bool,
    "gesture": str,
    "confidence": float,
    "proximity": str,
    "frame": frame_bgr,
    "hand_results": hand_results,
    "pose_results": pose_results
}
```

La UI no vuelve a ejecutar MediaPipe.

Los landmarks de manos y pose calculados por el módulo de visión son reutilizados directamente para dibujar el overlay.

Esto evita procesamiento duplicado y reduce carga innecesaria, especialmente pensando en la ejecución sobre Raspberry Pi.

## Resultado de AuraUI

`AuraUI.process()` devuelve un diccionario con la siguiente estructura:

```python
{
    "frame": frame_renderizado,
    "state": RobotState,
    "state_label": str,
    "interpretation": str,
    "action": str
}
```

El campo `frame` ya contiene la representación visual completa:

```text
Frame de cámara
    +
Landmarks
    +
Bounding boxes
    +
Panel de información
    +
Estado visual
    +
Interpretación
    +
Acción
    +
Robot 2D
```

## Flujo visual de presencia

Cuando no existe una persona confirmada:

```text
IDLE
```

Cuando aparece una persona de forma estable:

```text
IDLE
  |
  v
GREETING
  |
  v
DETECTING
```

Cuando Vision detecta un gesto:

```text
DETECTING
    |
    v
THINKING
```

Cuando el gesto deja de detectarse:

```text
THINKING
    |
    v
DETECTING
```

Cuando la persona sale de cámara:

```text
DETECTING
    |
    v
GOODBYE
    |
    v
IDLE
```

## Estabilización temporal

`RobotStateController` utiliza confirmación temporal para reducir cambios visuales causados por falsos positivos o pérdidas momentáneas de detección.

Una detección aislada de:

```python
person_detected = True
```

no necesariamente provoca inmediatamente una nueva interacción.

De igual manera, una pérdida momentánea de:

```python
person_detected = False
```

no provoca automáticamente la despedida.

La transición ocurre únicamente cuando la condición permanece durante el tiempo configurado.

## Gestos soportados por la presentación

La interfaz incluye textos predeterminados para los gestos utilizados actualmente por el módulo Vision:

```text
HAND_RAISED
THUMBS_UP
THUMBS_DOWN
POINT_LEFT
POINT_RIGHT
ARMS_CROSSED
INDEX_UP
INDEX_DOWN
WRITE_GESTURE
UNKNOWN
```

Ejemplos:

```text
HAND_RAISED
Interpretación: Saludo detectado
Acción: Responder

THUMBS_UP
Interpretación: Aprobacion
Acción: Confirmar

THUMBS_DOWN
Interpretación: Desaprobacion
Acción: Cambiar respuesta

INDEX_UP
Interpretación: Consulta de horario
Acción: Consultar horario

INDEX_DOWN
Interpretación: Solicitud de material
Acción: Descargar material

WRITE_GESTURE
Interpretación: Escritura detectada
Acción: Completar formulario
```

## Estados de ejecución externa

`AuraUI` permite que el orquestador informe el estado de una acción real mediante el parámetro:

```python
execution_status
```

Los valores soportados son:

```text
None
running
success
error
```

La relación con los estados visuales es:

```text
running -> EXECUTING
success -> SUCCESS
error   -> ERROR
```

Ejemplo de una operación en ejecución:

```python
ui_result = aura_ui.process(
    vision_result,
    execution_status="running",
    interpretation="Consultando portal",
    action="Obtener horario"
)
```

Esto produce:

```text
Estado: EXECUTING
Interpretación: Consultando portal
Acción: Obtener horario
```

## Resultado de una acción

Si una operación externa devuelve un resultado como:

```python
resultado = {
    "success": True
}
```

el orquestador puede convertirlo al contrato esperado por la UI:

```python
execution_status = (
    "success"
    if resultado.get("success")
    else "error"
)
```

Después:

```python
ui_result = aura_ui.process(
    vision_result,
    execution_status=execution_status
)
```

Si el resultado fue exitoso:

```text
SUCCESS
```

Si falló:

```text
ERROR
```

Los estados `SUCCESS` y `ERROR` permanecen visibles brevemente aunque posteriormente `execution_status` vuelva a `None`.

## Integración con RPA

La UI no ejecuta procesos RPA.

La arquitectura esperada es:

```text
VisionDetector
      |
      v
Percepción
      |
      v
Orquestador
      |
      +--------> RPA
      |           |
      |           v
      |        Resultado
      |           |
      +-----------+
      |
      v
execution_status
      |
      v
AuraUI
      |
      v
Frame renderizado
```

Mientras una acción está en ejecución:

```python
execution_status = "running"
```

Cuando finaliza correctamente:

```python
execution_status = "success"
```

Cuando falla:

```python
execution_status = "error"
```

## Consideración importante para Persona 1

Las operaciones RPA pueden tardar varios segundos.

El loop de cámara no debe quedar bloqueado esperando que finalice un proceso externo.

Si el orquestador realiza una llamada bloqueante como:

```python
resultado = ejecutar_rpa()
```

la cámara podría dejar de actualizarse durante la ejecución y el usuario no vería correctamente el estado `EXECUTING`.

Por ello, la ejecución externa debe manejarse de forma asíncrona o mediante una tarea independiente mientras el ciclo visual continúa procesando frames.

## Textos personalizados

El orquestador puede sustituir la interpretación y acción predeterminadas:

```python
ui_result = aura_ui.process(
    vision_result,
    execution_status="running",
    interpretation="Consultando horario",
    action="Abrir portal académico"
)
```

Los textos enviados explícitamente tienen prioridad sobre los valores predeterminados de la UI.

## RobotRenderer

`RobotRenderer` se encarga de cargar y dibujar el sprite asociado al estado actual.

Puede importarse mediante:

```python
from ui import RobotRenderer
```

Por defecto utiliza:

```python
assets_dir="ui/assets"
```

Los sprites se mantienen en caché para evitar lecturas repetitivas desde disco.

## Assets del robot

Los ocho sprites utilizados son:

```text
idle.png
greeting.png
detecting.png
thinking.png
executing.png
success.png
error.png
goodbye.png
```

Todos utilizan PNG con canal alfa.

Se encuentran en:

```text
ui/assets/
```

## AugmentedRealityOverlay

El componente:

```python
AugmentedRealityOverlay
```

es responsable de dibujar:

```text
Landmarks de mano
Landmarks de pose
Bounding boxes
Panel de información
Robot 2D
```

Puede importarse con:

```python
from ui import AugmentedRealityOverlay
```

Normalmente Persona 1 no necesita utilizarlo directamente porque `AuraUI` ya lo encapsula.

## RobotStateController

`RobotStateController` administra las transiciones visuales.

Puede importarse mediante:

```python
from ui import RobotStateController
```

Controla:

```text
IDLE
GREETING
DETECTING
THINKING
EXECUTING
SUCCESS
ERROR
GOODBYE
```

Normalmente tampoco debe manejarse directamente desde el orquestador porque `AuraUI` ya lo utiliza internamente.

## API principal para Persona 1

La integración normal se reduce a:

```python
from ui import AuraUI

aura_ui = AuraUI()
```

Dentro del loop principal:

```python
vision_result = detector.process()

ui_result = aura_ui.process(
    vision_result,
    execution_status=execution_status
)

frame = ui_result["frame"]
```

Para obtener información adicional:

```python
state = ui_result["state"]
state_label = ui_result["state_label"]
interpretation = ui_result["interpretation"]
action = ui_result["action"]
```

## Pruebas del módulo

Las pruebas automáticas correspondientes a esta responsabilidad son:

```text
tests/test_core_states.py
tests/test_state_controller.py
tests/test_execution_states.py
tests/test_robot.py
tests/test_assets.py
tests/test_overlay.py
tests/test_aura_ui.py
```

En PowerShell pueden ejecutarse con:

```powershell
python -m unittest `
    tests.test_core_states `
    tests.test_state_controller `
    tests.test_execution_states `
    tests.test_robot `
    tests.test_assets `
    tests.test_overlay `
    tests.test_aura_ui
```

El resultado validado actualmente es:

```text
Ran 48 tests
OK
```

## Archivos principales

```text
core/states.py
ui/__init__.py
ui/robot.py
ui/overlay.py
ui/assets/
ui/README.md
```

## Resumen de integración

Persona 1 únicamente necesita consumir:

```python
from ui import AuraUI
```

crear una sola instancia:

```python
aura_ui = AuraUI()
```

y enviar cada resultado de Vision:

```python
ui_result = aura_ui.process(
    vision_result,
    execution_status=execution_status
)
```

El frame final que debe mostrarse se obtiene mediante:

```python
frame = ui_result["frame"]
```

El módulo UI se encarga internamente de:

```text
Robot 2D
Estados visuales
Overlay AR
Landmarks
Bounding boxes
Información de percepción
Interpretación
Acción
Transiciones temporales
Estados de ejecución
```

No es necesario que el orquestador replique ninguna de estas responsabilidades.