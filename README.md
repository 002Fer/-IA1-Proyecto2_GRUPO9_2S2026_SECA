# AURA — Agente Visual con Automatización Robótica de Procesos
### Proyecto 2 · Laboratorio de Inteligencia Artificial 1 · FIUSAC · 2S 2026 · Grupo 9

> **Hardware objetivo:** Raspberry Pi 3A+ (512 MB RAM) · **Python:** 3.12 · **Branch de trabajo:** `develop`

---

## Tabla de contenidos

1. [Descripción general](#1-descripción-general)
2. [Arquitectura del sistema](#2-arquitectura-del-sistema)
3. [Estructura del repositorio](#3-estructura-del-repositorio)
4. [Instalación rápida](#4-instalación-rápida)
5. [Configuración de variables de entorno](#5-configuración-de-variables-de-entorno)
6. [Módulo 1 — Computer Vision](#6-módulo-1--computer-vision)
7. [Módulo 2 — Robot 2D y Realidad Aumentada](#7-módulo-2--robot-2d-y-realidad-aumentada)
8. [Módulo 3 — Bot de Telegram](#8-módulo-3--bot-de-telegram)
9. [Módulo 4 — RPA (Automatización de procesos)](#9-módulo-4--rpa-automatización-de-procesos)
10. [Punto de entrada principal — `main.py`](#10-punto-de-entrada-principal--mainpy)
11. [Gestos reconocidos](#11-gestos-reconocidos)
12. [Stream de video MJPEG](#12-stream-de-video-mjpeg)
13. [Comandos del bot de Telegram](#13-comandos-del-bot-de-telegram)
14. [Pruebas](#14-pruebas)
15. [Notas de rendimiento en Raspberry Pi](#15-notas-de-rendimiento-en-raspberry-pi)

---

## 1. Descripción general

**AURA** es un agente inteligente que corre en una Raspberry Pi y combina:

| Capacidad | Descripción |
|---|---|
| **Visión por computadora** | Detecta presencia de persona y reconoce 9 gestos en tiempo real con MediaPipe |
| **Realidad Aumentada** | Superpone landmarks, bounding boxes y un robot virtual 2D sobre el video |
| **Stream de video** | Publica el video con overlay vía HTTP MJPEG en el puerto 8080 |
| **Bot de Telegram** | Permite monitoreo y control remoto del agente desde cualquier dispositivo |
| **Automatización RPA** | Ejecuta procesos reales en portales web (horario FIUSAC, material UEDI, formulario) disparados por gestos |

El flujo principal es:

```
Cámara → MediaPipe → Gesto detectado → RPA en hilo paralelo → Resultado → Telegram + Overlay AR
```

---

## 2. Arquitectura del sistema

```
main.py  (orquestador)
   │
   ├── VisionDetector          vision/
   │       ├── Camera          (rpicam-vid subprocess + MJPEG pipe)
   │       ├── HandLandmarks   (MediaPipe Hand Landmarker)
   │       ├── PoseLandmarks   (MediaPipe Pose Landmarker Lite)
   │       └── GestureRecognizer
   │
   ├── AuraUI                  ui/
   │       ├── RobotStateController   (máquina de estados visual)
   │       ├── AugmentedRealityOverlay
   │       └── RobotRenderer          (sprites PNG por estado)
   │
   ├── Bot de Telegram         telegram/
   │       ├── TelegramService        (HTTP nativo, sin librería pesada)
   │       ├── TelegramHandlers
   │       ├── AgentService
   │       │       ├── MockAgentService   (PC / modo desarrollo)
   │       │       └── RaspberryAgentService  (RPi / producción)
   │       └── RuntimeAdapter         (puente con main.py)
   │
   ├── RPAService              rpa/
   │       ├── horario.py      (Portal Académico FIUSAC)
   │       ├── material.py     (UEDI — descarga enunciado)
   │       └── formulario.py   (formulario auxiliares)
   │
   └── Servidor MJPEG HTTP     (puerto 8080, hilo daemon)
```

### Concurrencia

| Hilo | Función |
|---|---|
| **Principal** | Loop de visión + AR (~15 FPS normal, ~2.5 FPS durante RPA) |
| **Daemon — MJPEG** | Sirve los frames JPEG a navegadores conectados |
| **Daemon — Telegram** | Long-polling de comandos y envío de notificaciones |
| **Daemon — RPA** | Ejecuta Chromium headless para automatización web |

---

## 3. Estructura del repositorio

```
.
├── main.py                    # Punto de entrada principal
├── requirements.txt
├── .env.example               # Plantilla de variables de entorno
│
├── core/
│   └── states.py              # RobotState enum + RobotStateController
│
├── vision/
│   ├── camera.py              # Captura rpicam-vid con pipe MJPEG no-bloqueante
│   ├── landmarks.py           # HandLandmarker (21 puntos por mano)
│   ├── pose.py                # PoseLandmarker Lite (33 puntos corporales)
│   ├── gestures.py            # GestureRecognizer (9 gestos)
│   └── detector.py            # VisionDetector — API unificada
│
├── ui/
│   ├── overlay.py             # AugmentedRealityOverlay
│   ├── robot.py               # RobotRenderer + sprites
│   ├── assets/                # Sprites PNG (idle, greeting, detecting…)
│   └── README.md
│
├── telegram/
│   ├── bot.py                 # Composición del módulo
│   ├── handlers.py            # Procesamiento de comandos
│   ├── commands.py            # Catálogo de comandos
│   ├── telegram_service.py    # HTTP nativo contra Telegram Bot API
│   ├── agent_service.py       # MockAgentService / RaspberryAgentService
│   ├── .env.example
│   └── README.md
│
├── rpa/
│   ├── browser.py             # Contexto Playwright optimizado para RPi
│   ├── config.py              # Lectura de variables de entorno RPA
│   ├── horario.py             # RPA 1 — Consultar horario (INDEX_UP)
│   ├── material.py            # RPA 2 — Descargar material UEDI (INDEX_DOWN)
│   ├── formulario.py          # RPA 3 — Completar formulario (WRITE_GESTURE)
│   ├── service.py             # RPAService — interfaz pública
│   └── test_rpa.py            # Prueba interactiva de los 3 RPA
│
├── models/
│   ├── hand_landmarker.task   # Modelo MediaPipe (descargado automáticamente)
│   └── pose_landmarker_lite.task
│
├── tests/
│   ├── test_camera.py
│   ├── test_detector.py
│   ├── test_core_states.py
│   ├── test_state_controller.py
│   ├── test_execution_states.py
│   ├── test_robot.py
│   ├── test_assets.py
│   ├── test_overlay.py
│   └── test_aura_ui.py
│
└── downloads/                 # Material descargado por RPA 2
```

---

## 4. Instalación rápida

### Requisitos previos

- Python 3.12 (se recomienda instalar con `uv` en la Raspberry Pi)
- `rpicam-vid` disponible en el sistema (paquete `rpicam-apps`)
- Conexión a internet (para Playwright y modelos MediaPipe en la primera ejecución)

### Clonar y preparar entorno

```bash
git clone <URL_DEL_REPO>
cd -IA1-Proyecto2_GRUPO9_2S2026_SECA
git checkout develop

# Crear entorno virtual
python -m venv .venv          # Cualquier sistema
# o con uv (recomendado en Raspberry Pi):
uv venv .venv --python 3.12
```

### Activar entorno virtual

```bash
# Linux / Raspberry Pi
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### Instalar dependencias

```bash
pip install -r requirements.txt

# Instalar Playwright + descargar Chromium
playwright install chromium
```

### Primera ejecución

Los modelos de MediaPipe se descargan automáticamente en `models/` si no existen o si los archivos son inválidos (p. ej., punteros Git LFS).

```bash
python main.py
```

---

## 5. Configuración de variables de entorno

### Archivo raíz `.env`

Copia `.env.example` como `.env` y completa los valores:

```env
# Credenciales USAC (para RPA 1 y RPA 2)
USAC_USER=202XXXXXX
USAC_PASSWORD=tu_contraseña

# URLs de los portales (no modificar)
PORTAL_ACADEMICO_URL=https://dashboardacademico.ingenieria.usac.edu.gt/
UEDI_URL=https://uedi.ingenieria.usac.edu.gt/campus/
UEDI_LOGIN_URL=https://uedi.ingenieria.usac.edu.gt/campus/

# Curso y material que descargará RPA 2
CURSO_OBJETIVO="LABORATORIO DE INTELIGENCIA ARTIFICIAL 1"
SECCION_TEMA="Proyectos"
MATERIAL_OBJETIVO="Proyecto #2"

# URL del formulario de auxiliares (para RPA 3)
FORMULARIO_URL=
```

### Archivo `telegram/.env`

Copia `telegram/.env.example` como `telegram/.env`:

```env
AURA_BOT_TOKEN=1234567890:AAxxxxxxxxxxxxxxxxxxxxxxxx
AURA_MODE=rpi          # pc → datos simulados | rpi → datos reales de Linux
AURA_ALLOWED_CHAT_ID=  # Opcional: restringe acceso a un solo chat
AURA_POLL_TIMEOUT=25
AURA_DATA_DIR=data
```

> **Nunca subas `.env` a Git.** Ya están en `.gitignore`.

---

## 6. Módulo 1 — Computer Vision

### Responsabilidad

Detectar visualmente **qué ocurre** frente a la cámara: presencia de persona, proximidad estimada y gesto reconocido. El módulo **no decide** qué acción tomar; solo informa al orquestador.

### Componentes

| Archivo | Responsabilidad |
|---|---|
| `vision/camera.py` | Captura frames desde `rpicam-vid` vía pipe MJPEG; lectura no-bloqueante con `fcntl` |
| `vision/landmarks.py` | Inicializa y ejecuta `HandLandmarker` (21 puntos por mano) |
| `vision/pose.py` | Inicializa y ejecuta `PoseLandmarker Lite` (33 puntos corporales) |
| `vision/gestures.py` | `GestureRecognizer`: reglas geométricas para los 9 gestos |
| `vision/detector.py` | `VisionDetector`: API unificada que combina todos los componentes |

### API pública

```python
from vision.detector import VisionDetector

detector = VisionDetector(
    hand_model_path="models/hand_landmarker.task",
    pose_model_path="models/pose_landmarker.task",
)
detector.open()

result = detector.process()
# result = {
#     "person_detected": bool,
#     "gesture": str,          # p. ej. "THUMBS_UP"
#     "confidence": float,     # 0.0 – 1.0
#     "proximity": str,        # "NEAR" | "MEDIUM" | "FAR" | "UNKNOWN"
#     "frame": ndarray,        # frame BGR con anotaciones básicas
#     "hand_results": ...,
#     "pose_results": ...,
# }

detector.release()
```

### Detección de presencia

- Se requieren **≥ 5 frames** consecutivos con persona para confirmar presencia.
- Se requieren **≥ 10 frames** consecutivos sin persona para confirmar ausencia.
- Esto elimina falsos positivos y parpadeos visuales.

### Estimación de proximidad

Basada en el ancho normalizado de los hombros detectados por Pose:

| Rango | Resultado |
|---|---|
| ≥ 0.30 | `NEAR` |
| ≥ 0.18 | `MEDIUM` |
| < 0.18 | `FAR` |

### Modelos de MediaPipe

Los archivos `.task` se descargan automáticamente desde Google CDN en la primera ejecución si no existen o están corruptos:

```
models/
├── hand_landmarker.task
└── pose_landmarker_lite.task    ← variante lite para Raspberry Pi
```

### Pruebas de visión

```bash
# Prueba de cámara (solo acceso, sin MediaPipe)
python -m tests.test_camera

# Prueba completa del detector (MediaPipe + gestos)
python -m tests.test_detector
```

Presiona `Q` para cerrar la ventana de prueba.

---

## 7. Módulo 2 — Robot 2D y Realidad Aumentada

### Responsabilidad

Renderizar el estado del agente sobre el video en tiempo real: landmarks, bounding boxes, panel de información y un robot virtual 2D animado por estados.

### Estados visuales

| Estado | Etiqueta | Cuándo |
|---|---|---|
| `IDLE` | Esperando | Sin usuario confirmado |
| `GREETING` | Saludando | Persona recién detectada |
| `DETECTING` | Detectando | Esperando gesto |
| `THINKING` | Interpretando | Gesto reconocido |
| `EXECUTING` | Ejecutando | Proceso RPA en curso |
| `SUCCESS` | Exito | RPA finalizado correctamente |
| `ERROR` | Error | RPA fallido |
| `GOODBYE` | Despedida | Persona salió de cámara |

### Sprites del robot

Cada estado tiene un sprite PNG en `ui/assets/` (`idle.png`, `greeting.png`, `detecting.png`, `thinking.png`, `executing.png`, `success.png`, `error.png`, `goodbye.png`). Todos usan canal alfa.

### API pública

```python
from ui import AuraUI

aura_ui = AuraUI()   # Una sola instancia para toda la sesión

ui_result = aura_ui.process(
    vision_result=result,        # dict de VisionDetector.process()
    execution_status="running",  # None | "running" | "success" | "error"
    interpretation="Texto AR",
    action="Acción en curso",
)

frame = ui_result["frame"]         # Frame BGR final con todo el overlay
state_label = ui_result["state_label"]
```

### Pruebas de UI

```bash
python -m unittest \
    tests.test_core_states \
    tests.test_state_controller \
    tests.test_execution_states \
    tests.test_robot \
    tests.test_assets \
    tests.test_overlay \
    tests.test_aura_ui
```

Resultado esperado: **48 tests OK**.

---

## 8. Módulo 3 — Bot de Telegram

### Responsabilidad

Permitir monitoreo y control remoto de AURA desde Telegram. No depende de ninguna librería pesada: usa HTTP nativo de Python.

### Arquitectura

```
Telegram API
    │
    ▼
TelegramService       (HTTP nativo — telegram/telegram_service.py)
    │
    ▼
TelegramHandlers      (routing de comandos — telegram/handlers.py)
    │
    ▼
AgentService          (contrato común)
    ├── MockAgentService        (AURA_MODE=pc, datos simulados)
    └── RaspberryAgentService   (AURA_MODE=rpi, /proc real de Linux)
```

### Crear el bot

1. En Telegram busca `@BotFather` → `/newbot`
2. Define nombre y username (debe terminar en `bot`)
3. Guarda el token en `telegram/.env` como `AURA_BOT_TOKEN`

### Comandos disponibles

| Comando | Descripción |
|---|---|
| `/status` | CPU, RAM y estado del agente en tiempo real |
| `/iniciar` | Reactiva el reconocimiento de gestos (si se pausó) |
| `/apagar` | Pausa MediaPipe y pone AURA en reposo |
| `/history` | Historial de gestos detectados (fecha, gesto, confianza, acción) |
| `/gestures` | Lista gestos registrados y su estado (activo/inactivo) |
| `/addGesture <nombre>` | Registra o reactiva un gesto en la configuración |
| `/deleteGesture <nombre>` | Deshabilita un gesto (no lo elimina permanentemente) |
| `/actions` | Lista las acciones disponibles |
| `/addAction <nombre>` | Registra una nueva acción |
| `/linkAction <gesto>\|<accion>` | Asocia un gesto a una acción |
| `/sendMessage <gesto>\|<mensaje>` | Configura un mensaje automático para un gesto |
| `/rpa` | Lista los procesos RPA disponibles |
| `/logs` | Últimos eventos del agente |

### Ejemplos de uso

```
/sendMessage mano_levantada|¡Hola! ¿En qué puedo ayudarte?
/linkAction pulgar_arriba|confirmar
/deleteGesture brazos_cruzados
/addGesture brazos_cruzados    ← reactiva el gesto eliminado
```

### Estado persistido

El estado del agente (gestos, acciones, historial, mensajes) se guarda automáticamente en:

```
telegram/data/agent_state.json
```

### Integración con `main.py`

El bot arranca automáticamente al ejecutar `python main.py`. El `RuntimeAdapter` conecta los comandos `/iniciar` y `/apagar` con la variable `_recognition_active` del loop principal, pausando y reanudando MediaPipe de verdad.

Cuando un gesto dispara un RPA y este finaliza, AURA envía automáticamente una notificación al último chat que interactuó con el bot:

```
🤖 [AURA RPA] ✅ Proceso 'Consultando horario' finalizado.
Resultado: Horario obtenido en tiempo real: Magistral (...)
```

---

## 9. Módulo 4 — RPA (Automatización de procesos)

### Responsabilidad

Automatizar acciones en portales web institucionales usando **Playwright + Chromium headless**, disparadas por los gestos del usuario.

### Procesos disponibles

| ID | Gesto | Descripción |
|---|---|---|
| `horario` | Índice arriba (`INDEX_UP`) | Consulta el horario del semestre actual en el Portal Académico FIUSAC (Keycloak SSO → Dashboard Académico → infoestudiantes) |
| `material` | Índice abajo (`INDEX_DOWN`) | Descarga el enunciado del Proyecto 2 desde el campus virtual UEDI (autenticación Keycloak SSO → búsqueda del curso → descarga del PDF) |
| `formulario` | Gesto escritura (`WRITE_GESTURE`) | Completa el formulario de auxiliares (requiere `FORMULARIO_URL` en `.env`) |

### Flujo de RPA 1 — Horario

```
1. Navegar a dashboardacademico.ingenieria.usac.edu.gt
2. Autenticar con Keycloak SSO (usuario USAC)
3. Seleccionar carrera Ciencias y Sistemas (si aplica)
4. Navegar a infoestudiantes.ingenieria.usac.edu.gt/datosPersonales
5. Configurar periodo (Segundo Semestre) y ejecutar consulta
6. Parsear tabla de horarios
7. Retornar horario magistral + laboratorio de IA1
```

### Flujo de RPA 2 — Descarga material UEDI

```
1. Navegar directamente a uedi.ingenieria.usac.edu.gt/campus/login/index.php
2. Autenticar con Keycloak SSO
3. Buscar el curso "LABORATORIO DE INTELIGENCIA ARTIFICIAL 1"
4. Localizar la actividad "Proyecto #2"
5. Descargar el PDF adjunto a downloads/
```

### Prueba independiente de RPA

```bash
python rpa/test_rpa.py
```

Muestra un menú para probar cada proceso por separado, sin cámara ni Telegram.

### Optimizaciones para Raspberry Pi 3A+

El contexto de Chromium (`rpa/browser.py`) incluye:

```python
"--disable-dev-shm-usage"         # Evita usar /dev/shm (limitado en RPi)
"--disable-gpu"                    # No hay GPU en RPi
"--disable-background-networking"  # Reduce tráfico de red en background
"--disable-renderer-backgrounding" # Mantiene el renderer activo
"--js-flags=--max-old-space-size=128"  # Limita el heap JS a 128 MB
```

Además se bloquean imágenes, fuentes y medios para reducir el consumo de RAM.

### Timeouts configurados

| Paso | Timeout |
|---|---|
| Navegación principal | 150 000 ms (150 s) |
| `wait_until` en infoestudiantes | `"commit"` (más tolerante) |
| `wait_for_load_state` post-goto | 60 000 ms (tolerante, no lanza excepción) |
| Fill de credenciales Keycloak | 35 000 ms |
| Loop de redirección Keycloak | 15 iteraciones × 1 s |

---

## 10. Punto de entrada principal — `main.py`

### Ejecución

```bash
# En la Raspberry Pi (desde SSH)
source .venv/bin/activate
python main.py
```

```bash
# En tu PC (para ver el stream)
http://<IP_DE_LA_RASPBERRY>:8080
```

### Lo que hace `main.py`

1. Inicializa `VisionDetector` y `AuraUI`
2. Inicia el bot de Telegram en hilo daemon
3. Abre la cámara con `rpicam-vid`
4. Inicia el servidor MJPEG en el puerto 8080
5. Ejecuta el loop principal:
   - Si `_recognition_active = False` (comando `/apagar`): muestra cámara sin MediaPipe
   - Si hay un RPA corriendo: reduce FPS a ~2.5, cede CPU a Chromium
   - En modo normal: procesa frames con MediaPipe a ~15 FPS
   - Al detectar un gesto RPA: lanza `_trigger_rpa()` en hilo daemon
6. Ctrl+C / SIGTERM detiene todo limpiamente en menos de 1 segundo

### Mapeo de gestos → RPA

```python
RPA_GESTURES = {
    "INDEX_UP":      ("horario",    "Consultando horario"),
    "INDEX_DOWN":    ("material",   "Descargando material UEDI"),
    "WRITE_GESTURE": ("formulario", "Completando formulario"),
}
```

---

## 11. Gestos reconocidos

| Constante | Gesto | Descripción | Acción |
|---|---|---|---|
| `HAND_RAISED` | Mano abierta levantada | Los 5 dedos extendidos | Mensaje configurable |
| `THUMBS_UP` | Pulgar arriba | Pulgar extendido hacia arriba, dedos cerrados | Mensaje configurable |
| `THUMBS_DOWN` | Pulgar abajo | Pulgar extendido hacia abajo, dedos cerrados | Mensaje configurable |
| `POINT_LEFT` | Señalar izquierda | Índice horizontal apuntando a la izquierda | Mensaje configurable |
| `POINT_RIGHT` | Señalar derecha | Índice horizontal apuntando a la derecha | Mensaje configurable |
| `ARMS_CROSSED` | Brazos cruzados | Muñecas cruzadas frente al torso (detección por Pose) | Mensaje configurable |
| `INDEX_UP` | Índice arriba | Índice vertical hacia arriba, otros dedos cerrados | **RPA 1: Consultar horario** |
| `INDEX_DOWN` | Índice abajo | Índice vertical hacia abajo, otros dedos cerrados | **RPA 2: Descargar material** |
| `WRITE_GESTURE` | Gesto escritura | Movimiento zigzag del índice | **RPA 3: Completar formulario** |

Los gestos pueden habilitarse o deshabilitarse desde Telegram con `/deleteGesture` y `/addGesture`.

---

## 12. Stream de video MJPEG

El servidor MJPEG inicia automáticamente al ejecutar `main.py`:

```
http://<IP_RASPBERRY>:8080
```

- Compatible con cualquier navegador moderno
- Calidad JPEG: 75% (equilibrio calidad/ancho de banda)
- FPS publicados al cliente: ~10 FPS
- FPS de captura: ~15 FPS (normal) / ~2.5 FPS (durante RPA)

Para obtener la IP de la Raspberry Pi:

```bash
hostname -I
```

---

## 13. Comandos del bot de Telegram

Ver la tabla completa en la [sección 8](#8-módulo-3--bot-de-telegram). A continuación, ejemplos del flujo típico:

```
/status          → CPU: 42% | RAM: 61% | Estado: RUNNING | Reconocimiento: ACTIVE
/gestures        → Lista de 9 gestos activos
/rpa             → Lista de 3 procesos RPA disponibles
/history         → Último gesto detectado con timestamp y confianza
/apagar          → AURA entra en reposo (MediaPipe pausado)
/iniciar         → AURA se reactiva
/sendMessage mano_levantada|¡Saludos! → Configura mensaje automático
/deleteGesture brazos_cruzados         → Deshabilita gesto
/addGesture brazos_cruzados            → Reactiva gesto
/logs            → Últimos eventos del agente
```

---

## 14. Pruebas

### Pruebas de visión

```bash
python -m tests.test_camera      # Solo acceso a cámara
python -m tests.test_detector    # Detector completo (presionar Q para salir)
```

### Pruebas de UI (48 tests)

```bash
python -m unittest \
    tests.test_core_states \
    tests.test_state_controller \
    tests.test_execution_states \
    tests.test_robot \
    tests.test_assets \
    tests.test_overlay \
    tests.test_aura_ui
```

### Prueba de RPA (sin cámara)

```bash
python rpa/test_rpa.py
```

Opciones del menú:
1. Listar procesos disponibles
2. Probar RPA 1 — Consultar horario
3. Probar RPA 2 — Descargar material UEDI
4. Probar RPA 3 — Completar formulario
5. Probar todos secuencialmente

### Prueba completa integrada

```bash
python main.py
```

Luego desde Telegram: `/status` → gesticular frente a cámara → `/history`.

---

## 15. Notas de rendimiento en Raspberry Pi

| Aspecto | Detalle |
|---|---|
| **Hardware** | Raspberry Pi 3A+, 512 MB RAM, ARM Cortex-A53 @ 1.4 GHz |
| **Temperatura** | ~60 °C bajo carga combinada (normal, sin throttling) |
| **MediaPipe durante RPA** | Pausado completamente para ceder CPU a Chromium |
| **Modelo de pose** | Variante `lite` (menor consumo vs. `full` o `heavy`) |
| **Cámara** | `rpicam-vid` subprocess + pipe MJPEG no-bloqueante (`fcntl`) |
| **Chromium** | Descargado con `playwright install chromium` (no el del sistema) |
| **Timeouts RPA** | 150 s para portales lentos de FIUSAC |
| **RAM del heap JS** | Limitado a 128 MB (`--js-flags=--max-old-space-size=128`) |
| **Bloqueo de recursos** | Imágenes, fuentes y medios bloqueados en Playwright |

---

## Créditos

**Grupo 9 — Laboratorio de Inteligencia Artificial 1, 2S 2026**  
Sección A · Facultad de Ingeniería · USAC

| Módulo | Responsable |
|---|---|
|Juntar y hacer pruebas| Persona 1|
| Orquestador + Visión + Cámara | Persona 2 |
| Robot 2D + Realidad Aumentada | Persona 3|
| RPA — Automatización web | Persona 4|
| Bot de Telegram | Persona 5 |
