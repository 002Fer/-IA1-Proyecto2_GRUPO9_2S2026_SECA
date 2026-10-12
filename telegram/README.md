# Módulo Telegram

---

## 1. Estructura del módulo

```text
telegram/
├── .env
├── .env.example
├── README.md
├── data/
│
├── __init__.py
├── bot.py
├── handlers.py
├── commands.py
├── telegram_service.py
└── agent_service.py
```

### Responsabilidad de cada archivo

| Archivo | Responsabilidad |
|---|---|
| `.env` | Configuración local y secreto del bot |
| `.env.example` | Plantilla de configuración |
| `.gitignore` | Evita subir secretos y estado generado |
| `README.md` | Manual del módulo |
| `data/` | Estado local de pruebas/configuración |
| `bot.py` | Punto de entrada y composición del módulo |
| `handlers.py` | Procesamiento de comandos Telegram |
| `commands.py` | Catálogo y parser de comandos |
| `telegram_service.py` | HTTP nativo contra Telegram Bot API |
| `agent_service.py` | Contrato común entre Telegram y AURA |

---

# 2. Arquitectura de integración

```text
                    TELEGRAM
                        │
                        ▼
              TelegramService
                        │
                        ▼
               TelegramHandlers
                        │
                        ▼
                 AgentService
                    /       \
                   /         \
                  ▼           ▼
          MockAgentService   RaspberryAgentService
              (PC)                 (Raspberry)
                                  │
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
               Vision            RPA          Robot 2D
```

La capa `AgentService` funciona como contrato común. Por ejemplo:

```python
agent.get_status()
agent.start()
agent.stop()
agent.execute_gesture(gesture, confidence)
```

Los handlers no necesitan saber cómo funciona MediaPipe ni cómo se ejecuta un RPA.

---

# 3. Requisitos

- Python 3.8+ recomendado.
- Telegram.
- Un bot creado con `@BotFather`.
- Internet para comunicarse con Telegram.

No es necesario instalar una librería para Telegram.

---

# 4. Crear el bot con BotFather

## Paso 1

En Telegram busca:

```text
@BotFather
```

## Paso 2

Ejecuta:

```text
/newbot
```

BotFather solicitará el nombre y username. El username debe terminar en `bot`.

Ejemplo:

```text
AURA IA1
AURA_IA1_2026_bot
```

## Paso 3

BotFather entregará un token parecido a:

```text
1234567890:AAxxxxxxxxxxxxxxxxxxxxxxxx
```

Ese token es secreto. **No debe subirse a GitHub.**

---

# 5. Configurar `.env`

Dentro de `telegram/` existe un `.env.example`. Para una instalación limpia, puede copiarse como `.env`.

Ejemplo:

```env
AURA_BOT_TOKEN=1234567890:AAxxxxxxxxxxxxxxxxxxxxxxxx
AURA_MODE=pc
AURA_ALLOWED_CHAT_ID=
AURA_POLL_TIMEOUT=25
AURA_DATA_DIR=data
```

### Variables

`AURA_BOT_TOKEN`
: Token entregado por BotFather.

`AURA_MODE`
: `pc` utiliza datos simulados; `rpi` utiliza el adaptador de Raspberry/Linux.

`AURA_ALLOWED_CHAT_ID`
: Opcional. Si se configura, solo ese chat podrá utilizar el bot.

`AURA_POLL_TIMEOUT`
: Tiempo de long polling de Telegram.

`AURA_DATA_DIR`
: Carpeta de datos. Si es relativa, se resuelve **respecto a la carpeta `telegram/`**, no respecto al directorio desde el que se ejecutó Python.

Esto evita problemas de rutas al ejecutar el módulo desde diferentes ubicaciones.

---

# 6. `.env` y Git

`.env` está incluido en el `.gitignore` del módulo.

Nunca hacer:

```bash
git add telegram/.env
```

Sí debe compartirse:

```text
telegram/.env.example
```

Cada integrante coloca su propio token en su `.env`.

---

# 7. Ejecutar desde la raíz del proyecto

Si la estructura general es:

```text
AURA/
└── telegram/
    ├── .env
    ├── bot.py
    └── ...
```

Desde `AURA/` ejecutar:

```bash
python -m telegram.bot
```

---

# 8. Ejecutar directamente desde `telegram/`

También está soportado:

```bash
cd telegram
python bot.py
```

El código tiene imports de respaldo para esta modalidad.

El `.env` y `data/` continúan resolviéndose desde la ubicación real de `bot.py`, por lo que cambiar el directorio actual no rompe las rutas.

---

# 9. Prueba en PC

Usar:

```env
AURA_MODE=pc
```

Al ejecutar el bot, `MockAgentService` proporciona inicialmente:

```text
CPU: 35%
RAM: 48%
Estado: RUNNING
Reconocimiento: ACTIVE
```

La información se guarda en:

```text
telegram/data/agent_state.json
```

El archivo se crea automáticamente.

---

# 10. Probar `/status`, `/iniciar` y `/apagar`

En Telegram:

```text
/status
```

Después:

```text
/apagar
/status
/iniciar
/status
```

El estado debe cambiar entre `RUNNING/ACTIVE` y `STOPPED/INACTIVE`. Esto permite demostrar el flujo desde la PC sin Raspberry.

---

# 11. Comandos obligatorios

```text
/status
/iniciar
/apagar
/history
/gestures
/addGesture
/deleteGesture
/actions
/addAction
/linkAction
/sendMessage
/rpa
/logs
```

## `/status`

Consulta CPU, RAM y estado del agente.

## `/iniciar`

Ejecuta `AgentService.start()`.

## `/apagar`

Ejecuta `AgentService.stop()`.

## `/history`

Muestra fecha, gesto, confianza y acción.

## `/gestures`

Lista gestos registrados y estado.

## `/addGesture`

Uso:

```text
/addGesture saludo
```

Registra el gesto en la configuración. **No significa entrenar MediaPipe**; el entrenamiento/clasificación pertenece al módulo de visión.

## `/deleteGesture`

```text
/deleteGesture saludo
```

Deshabilita el gesto.

## `/actions`

Lista las acciones disponibles.

## `/addAction`

```text
/addAction enviar_notificacion
```

## `/linkAction`

```text
/linkAction gesto|accion
```

Ejemplo:

```text
/linkAction pulgar_arriba|confirmar
```

## `/sendMessage`

```text
/sendMessage gesto|mensaje
```

Ejemplo:

```text
/sendMessage mano_levantada|Hola, ¿en qué puedo ayudarte?
```

## `/rpa`

Lista los procesos RPA registrados. Inicialmente:

- consultar horario
- descargar material
- completar formulario

## `/logs`

Muestra los últimos eventos registrados por el agente.

---

# 12. Integración con visión

El módulo de visión debe evitar importar directamente `handlers.py`. La integración recomendada es llamar al servicio común.

Ejemplo conceptual:

```python
resultado = agent.execute_gesture(
    gesture="pulgar_arriba",
    confidence=94
)
```

El servicio registra el evento y resuelve la asociación configurada:

```text
gesto detectado
      ↓
confidence
      ↓
AgentService.execute_gesture()
      ↓
historial
      ↓
gesto → acción
      ↓
RPA / mensaje / acción
```

Cuando el grupo termine MediaPipe, la implementación real debe utilizar esta misma interfaz.

---

# 13. Integración con RPA

El proyecto define procesos RPA que deben ejecutarse como consecuencia de gestos reconocidos.

La integración puede hacerse mediante un runtime adapter o una implementación concreta de `AgentService`.

La idea es:

```text
MediaPipe
   ↓
Gesto
   ↓
AgentService
   ↓
Acción asociada
   ↓
RPA
   ↓
Resultado
   ↓
Telegram / Robot 2D
```

No se debe colocar código de Selenium, Playwright u otra automatización directamente dentro de `handlers.py`.

---

# 14. Integración con el robot 2D

El robot 2D puede consultar el estado del agente o reaccionar a los eventos producidos por `AgentService`.

Ejemplo conceptual:

```text
Esperando
   ↓
Detectando
   ↓
Interpretando
   ↓
Ejecutando
   ↓
Éxito / Error
```

Telegram solamente administra y consulta el agente; no controla directamente los sprites.

---

# 15. Raspberry Pi

En Raspberry se configura:

```env
AURA_MODE=rpi
```

`RaspberryAgentService` mantiene la misma interfaz y obtiene CPU/RAM desde Linux mediante `/proc`, sin instalar `psutil`.

Para conectar el agente real, se puede utilizar `set_runtime_adapter()`. El adapter debe proporcionar como mínimo:

```python
get_status()
start()
stop()
```

Esto permite conectar el proceso real de AURA sin modificar `handlers.py`.

---

# 16. Flujo final del proyecto

```text
                 CÁMARA
                    ↓
                 OpenCV
                    ↓
                MediaPipe
                    ↓
          Clasificación de gesto
                    ↓
              AgentService
              ↙     ↓      ↘
        Telegram   Acción     Robot 2D
                     ↓
                    RPA
                     ↓
                 Resultado
                     ↓
                  Telegram
```

La información puede circular en ambos sentidos: Telegram consulta/administra el agente y el agente puede producir eventos derivados de visión/RPA.

---

# 17. Checklist de integración

Antes de integrar con el resto del proyecto:

- [ ] Crear bot con BotFather.
- [ ] Configurar `telegram/.env`.
- [ ] Verificar `/status`.
- [ ] Verificar `/iniciar` y `/apagar`.
- [ ] Verificar los 13 comandos.
- [ ] Verificar que `telegram/data/agent_state.json` se genere correctamente.
- [ ] Conectar módulo de visión con `execute_gesture()`.
- [ ] Conectar RPA con la acción asociada.
- [ ] Conectar robot 2D con los estados/eventos del agente.
- [ ] Cambiar `AURA_MODE=rpi`.
- [ ] Probar `/status` sobre Raspberry.
- [ ] Verificar que `.env` no aparezca en Git.