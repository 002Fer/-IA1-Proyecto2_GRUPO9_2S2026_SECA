# -IA1-Proyecto2_GRUPO9_2S2026_SECA

## Módulo de Computer Vision y tests

### 1. Objetivo

El módulo de Computer Vision de AURA tiene como objetivo proporcionar percepción visual del entorno mediante el procesamiento de imágenes capturadas por una cámara. El módulo permite detectar la presencia de una persona, estimar su proximidad y reconocer diferentes gestos definidos por los requerimientos del sistema.

El procesamiento se realiza de forma local utilizando Python, OpenCV y MediaPipe, sin depender de servicios externos de visión artificial.

### 2. Responsabilidad dentro del sistema

La responsabilidad del módulo de Computer Vision es identificar **qué está ocurriendo visualmente**, proporcionando esta información al núcleo de AURA mediante una estructura de percepción.

El módulo no determina qué acción debe ejecutar el agente. Por ejemplo, si se detecta un `THUMBS_UP` (Pulgar arriba), Computer Vision únicamente informa que se detectó dicho gesto. La interpretación del gesto y la acción correspondiente son responsabilidad del núcleo del sistema.

La separación permite mantener una clara división de responsabilidades entre la percepción y la lógica de decisión del agente.

### 3. Arquitectura interna

El módulo se divide en componentes especializados, cada componente posee una responsabilidad específica. `camera.py` administra la captura de imágenes; `landmarks.py` procesa los landmarks de las manos; `pose.py` procesa los landmarks corporales; `gestures.py` contiene las reglas de reconocimiento; y `detector.py` coordina el procesamiento y genera la salida final.

### 4. Tecnologías utilizadas

* **Python 3.x:** lenguaje utilizado para implementar el módulo.
* **OpenCV:** captura y procesamiento de los frames de la cámara.
* **MediaPipe Tasks:** detección de landmarks de manos y cuerpo.
* **MediaPipe Hand Landmarker:** identificación de los 21 landmarks correspondientes a cada mano.
* **MediaPipe Pose Landmarker:** identificación de landmarks corporales utilizados para presencia, proximidad y brazos cruzados.

Todo el procesamiento de visión está diseñado para ejecutarse localmente, de acuerdo con el requisito de procesamiento nativo en Raspberry Pi.

## 5. Instalación y ejecución

### 5.1. Requisitos
Para ejecutar el módulo de Computer Vision se requiere:

* Python 3.x.
* Una cámara disponible para el equipo.
* OpenCV.
* MediaPipe.
* Los modelos `.task` utilizados por MediaPipe.
El módulo está diseñado para ejecutarse localmente y no requiere servicios de visión artificial en la nube.

### 5.2. Preparar el entorno virtual
Desde la raíz del proyecto se recomienda crear un entorno virtual:

```bash
python -m venv .venv
```

Activación en Windows:

```bash
.venv\Scripts\activate
```

Activación en Linux/Raspberry Pi:

```bash
source .venv/bin/activate
```

### 5.3. Instalar dependencias

Con el entorno virtual activado:

Ejecutar el siguiente comando para instalar todas las dependecias:

```bash
python -m pip install -r requirements.txt

```
O ejecutar espesificamente la instalacion de opencv y mediapipe
```bash
pip install opencv-python mediapipe
```

Para comprobar que MediaPipe quedó instalado correctamente:

```bash
python -c "import mediapipe; print(mediapipe.__version__)"
```

### 5.4. Modelos de MediaPipe
Los modelos utilizados deben encontrarse en:

```text
models/
├── hand_landmarker.task
└── pose_landmarker.task
```
Estos archivos son necesarios para que `HandLandmarks` y `PoseLandmarks` puedan inicializar sus respectivos detectores.

### 5.5. Ejecutar la prueba del detector
La prueba principal del módulo se ejecuta desde la raíz del proyecto con:
```bash
python -m tests.test_detector
```

No se recomienda ejecutar directamente:
```bash
python tests/test_detector.py
```
porque el proyecto utiliza los módulos del paquete `vision` y la ejecución mediante `python -m` permite resolver correctamente estas importaciones desde la raíz del proyecto.

### 5.6. Prueba de la cámara
También existe una prueba independiente para comprobar únicamente el acceso a la cámara:
```bash
python -m tests.test_camera
```

La prueba abre una ventana con la imagen capturada. Para finalizarla se debe presionar:
```text
Q
```

### 5.7. Prueba del detector de Computer Vision
Al ejecutar:
```bash
python -m tests.test_detector
```

se abre la cámara y se procesa continuamente cada frame.
El programa muestra la percepción obtenida, por ejemplo:

```text
Persona: True | Gesto: THUMBS_UP | Confianza: 0.91 | Proximidad: MEDIUM
```

También se muestran visualmente los landmarks detectados sobre la imagen.
Durante la prueba se pueden realizar los gestos definidos para el sistema:
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
```

Cuando la persona deja de estar frente a la cámara durante el tiempo suficiente para superar el umbral de ausencia, la salida pasa a:
```text
Persona: False | Gesto: UNKNOWN | Confianza: 0.0 | Proximidad: UNKNOWN
```

Para finalizar la prueba:
```text
Q
```

### 5.8. Resultado esperado
Una ejecución correcta debe permitir comprobar:

* acceso a la cámara;
* detección de una persona;
* detección de landmarks de manos;
* detección de landmarks corporales;
* reconocimiento de los gestos definidos;
* estimación de proximidad;
* transición entre persona presente y ausente;
* generación de una estructura de percepción para el resto del sistema.

### 5.9. Flujo rápido para compañeros

Después de clonar el repositorio, el flujo básico es:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/Raspberry Pi:

```bash
source .venv/bin/activate
```

Instalar dependencias:

```bash
pip install opencv-python mediapipe
```

Comprobar la cámara:

```bash
python -m tests.test_camera
```
Presionar `Q` para finalizar test de camara

Ejecutar modulo Vision:

```bash
python -m tests.test_detector
```

Presionar `Q` para finalizar la prueba general.

