# Documentación de Micro Remote 2.0

> Audio en vivo por UDP para redes locales. Emisor (micrófono) y receptor (altavoces) con interfaz Tkinter, modo consola y descubrimiento automático.

---

## Índice

1. [Visión general](#1-visión-general)
2. [Características](#2-características)
3. [Requisitos y compatibilidad](#3-requisitos-y-compatibilidad)
4. [Instalación](#4-instalación)
5. [Uso de la interfaz gráfica](#5-uso-de-la-interfaz-gráfica)
6. [Uso desde la consola](#6-uso-desde-la-consola)
7. [Estructura del proyecto](#7-estructura-del-proyecto)
8. [Arquitectura](#8-arquitectura)
9. [Flujo de audio](#9-flujo-de-audio)
10. [Protocolo UDP](#10-protocolo-udp)
11. [Descubrimiento de receptores](#11-descubrimiento-de-receptores)
12. [Audio y DSP](#12-audio-y-dsp)
13. [Ajustes y persistencia](#13-ajustes-y-persistencia)
14. [Diseño de la interfaz](#14-diseño-de-la-interfaz)
15. [Referencia de módulos](#15-referencia-de-módulos)
16. [Pruebas](#16-pruebas)
17. [Iconos](#17-iconos)
18. [Empaquetado con PyInstaller](#18-empaquetado-con-pyinstaller)
19. [Solución de problemas](#19-solución-de-problemas)
20. [Migración de la versión 1](#20-migración-de-la-versión-1)
21. [Limitaciones y mejoras futuras](#21-limitaciones-y-mejoras-futuras)

---

## 1. Visión general

Micro Remote transmite el audio del micrófono de un equipo a los altavoces de otro a través de la red local usando **UDP**. Está formado por dos programas:

| Programa | Rol | Qué hace |
| --- | --- | --- |
| **Emisor** | Fuente | Captura el micrófono, aplica ganancia y envía paquetes UDP al receptor. |
| **Receptor** | Destino | Escucha en un puerto UDP, contabiliza pérdidas/tardíos, aplica volumen y reproduce en orden de llegada. |

Ambos comparten el mismo formato de audio y protocolo. Cualquiera de los dos puede ejecutarse con interfaz gráfica o en modo consola.

**Filosofía del proyecto**

- Dependencia mínima: solo **sounddevice** (PortAudio) en ejecución; Tkinter viene con Python.
- Sin NumPy ni Matplotlib: el procesamiento y el osciloscopio usan la biblioteca estándar y `tk.Canvas`.
- Lógica separada de la interfaz: los módulos de audio, red y protocolo no importan Tkinter.
- Tolerante a fallos: sin tarjeta de sonido el paquete se puede importar, probar y documentar.

---

## 2. Características

- **Interfaz oscura moderna**, inspirada en la estética *slate/indigo* de Tailwind: tarjetas con borde, títulos en versalitas, indicador de estado redondeado, métricas y registro con marcas de tiempo.
- **Osciloscopio** en tiempo real dibujado sobre un `Canvas` (envolvente min/max, sin perder picos) con **autoescala visual** suavizada para señales débiles.
- **Medidor de nivel** segmentado en dBFS (verde → ámbar → rojo) con marcador de pico.
- **Descubrimiento automático** de receptores por broadcast UDP, con barrido ICMP de la subred como reserva.
- **Selector de dispositivo** de entrada/salida y **ganancia ajustable en caliente** (0.0x – 5.0x).
- **Estadísticas**: paquetes enviados/recibidos, perdidos, tardíos, bitrate y duración.
- **Modo consola** para automatizar pruebas (`--cli`).
- **Ajustes persistentes** en JSON, con un archivo independiente para emisor y receptor (IP, puerto, ganancia y dispositivos).
- **Compatibilidad de protocolo** con la versión 1 (PCM crudo sin cabecera).
- **Compatible con PyInstaller** mediante `emisor.spec`, `receptor.spec` y `build.ps1`.
- **Sin dependencias de terceros** salvo `sounddevice`; pruebas con `unittest` de la biblioteca estándar.

---

## 3. Requisitos y compatibilidad

| Elemento | Requisito |
| --- | --- |
| Python | 3.10 o superior (probado con 3.14 en Windows) |
| Audio | `sounddevice` ≥ 0.5.6 (PortAudio incluido en Windows/macOS) |
| Interfaz | Tkinter (incluido en el instalador oficial de Windows) |
| Sistema | Windows 10/11 recomendado; el código es portable a Linux/macOS |
| Red | Los dos equipos deben estar en la misma red local y permitir UDP |

Detalles:

- El formato de audio es fijo: **PCM 16 bits con signo, mono, 44 100 Hz, little-endian**.
- Se usan los puertos **5000/UDP** (audio) y **5001/UDP** (descubrimiento) por defecto.
- No se requiere Internet: todo el tráfico es local (el descubrimiento consulta las direcciones de broadcast de las interfaces del equipo).

---

## 4. Instalación

### 4.1 Entorno virtual (recomendado)

```powershell
cd Micro_Remote
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

En Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4.2 Comprobar el audio y PortAudio

`sounddevice` incluye la DLL de PortAudio en los wheels de **Windows** y **macOS**, por lo que no hace falta compilador, Visual C++ Build Tools ni una versión concreta de Python. En Linux se usa la biblioteca del sistema:

```bash
sudo apt install libportaudio2
```

Comprueba que el equipo ve micrófonos y altavoces:

```powershell
python -m micro_remote devices
```

Si aparece «sounddevice no está disponible», revisa que el entorno virtual esté activado y vuelve a instalar `requirements.txt`.

### 4.3 Instalación como paquete

```powershell
pip install -e .
```

Esto habilita los comandos:

```powershell
micro-remote emisor
micro-remote receptor
micro-remote-emisor       # interfaz del emisor
micro-remote-receptor     # interfaz del receptor
```

### 4.4 Dependencias de desarrollo

```powershell
pip install -r requirements-dev.txt
```

Incluye `Pillow` (generación de iconos) y `pyinstaller` (ejecutables).

---

## 5. Uso de la interfaz gráfica

### 5.1 Arranque

```powershell
python interface_emisor.py
python interface_receptor.py
```

o, con el lanzador unificado:

```powershell
python -m micro_remote emisor
python -m micro_remote receptor
```

La ventana mide **1120 × 860** píxeles (mínimo 980 × 800, reducido en pantallas pequeñas) y se centra en la pantalla.

### 5.2 Emisor

1. **Conexión**
   - Escribe la **IP del receptor** en el campo correspondiente.
   - Ajusta el **puerto UDP** si el receptor usa otro (por defecto 5000).
   - Pulsa **Buscar** para descubrir receptores en la red. Los encontrados aparecen en **Dispositivos detectados**; al seleccionar uno se rellenan IP y puerto.
2. **Micrófono**
   - Elige el dispositivo de entrada (o «Sistema (predeterminado)»).
   - Ajusta la **ganancia de entrada**; se aplica en tiempo real sin cortar el audio.
3. **Controles**
   - **Iniciar transmisión** (`F5`).
   - **Detener** (`F6`).
4. **Panel derecho**
   - Métricas: enviados, destino, bitrate y tiempo.
   - Osciloscopio de la señal capturada (con autoescala para señales débiles) y medidor de nivel en dBFS.
   - Registro de eventos.

### 5.3 Receptor

1. **Recepción**
   - Indica el **puerto de escucha**.
   - Muestra tu **IP principal** (botón **Copiar**). Compártela con el emisor o deja que te encuentre con **Buscar**.
   - Si hay varias interfaces, se listan debajo.
2. **Altavoces**
   - Elige el dispositivo de salida y el **volumen de salida**.
3. **Controles**
   - **Iniciar recepción** (`F5`); **Detener** (`F6`).
   - Mientras la recepción está activa, el receptor responde automáticamente a las búsquedas del emisor.
4. Las métricas muestran recibidos, perdidos, bitrate, tiempo y la IP de origen.

### 5.4 Atajos de teclado

| Tecla | Acción |
| --- | --- |
| `F5` | Iniciar la sesión |
| `F6` | Detener la sesión |

### 5.5 Estados de la sesión

```text
        F5 / Iniciar                    audio listo
 idle ───────────────► starting ─────────────────► running
   ▲                       │                          │
   │                       │ error                    │ F6 / Detener
   │                       ▼                          ▼
   └──────────────────── error ◄─── error ────── stopping
                                                        │
                                                        └──► idle
```

| Estado | Botón Iniciar | Botón Detener | Indicador |
| --- | --- | --- | --- |
| `idle` | Activo | Desactivado | «Inactivo» (gris) |
| `starting` | Desactivado | Activo | «Preparando…» (ámbar) |
| `running` | Desactivado | Activo | «Transmitiendo» / «Escuchando» (verde) |
| `stopping` | Desactivado | Desactivado | «Deteniendo…» (ámbar) |
| `error` | Activo | Desactivado | «Error» (rojo) |

---

## 6. Uso desde la consola

El punto de entrada unificado es `python -m micro_remote`. Los lanzadores `cmd_emisor.py` y `cmd_receptor.py` son equivalentes abreviados.

### 6.1 Comandos

| Comando | Descripción |
| --- | --- |
| `emisor` | Emite el micrófono (interfaz o `--cli`). |
| `receptor` | Escucha audio (interfaz o `--cli`). |
| `scan` | Busca receptores en la red. |
| `devices` | Lista dispositivos de entrada y salida. |

### 6.2 Opciones

Opciones comunes de audio:

| Opción | Descripción |
| --- | --- |
| `--gain N` | Ganancia inicial (0.0 – 5.0). Si se omite, se usa la guardada. |
| `--device N` | Índice de dispositivo de audio (ver `devices`). |
| `--duration S` | Detener tras `S` segundos (0 = sin límite). |
| `--cli` | Ejecutar sin interfaz gráfica. |

Específicas:

| Comando | Opción | Descripción |
| --- | --- | --- |
| `emisor` | `--host IP` | IP del receptor (obligatoria con `--cli`). |
| `emisor` / `receptor` | `--port N` | Puerto UDP. Si se omite, se usa el guardado o 5000. |
| `scan` | `--timeout S` | Segundos de espera para el descubrimiento (debe ser > 0). |
| `scan` | `--port N` | Puerto a mostrar para hosts hallados solo por ICMP. |
| `scan` | `--no-sweep` | No hacer barrido ICMP si el descubrimiento no responde. |

### 6.3 Ejemplos

```powershell
# Ver dispositivos disponibles
python -m micro_remote devices

# Buscar receptores (UDP + barrido ICMP de reserva)
python -m micro_remote scan

# Buscar solo por UDP, sin barrido
python -m micro_remote scan --no-sweep --timeout 2

# Receptor en consola durante 30 segundos
python -m micro_remote receptor --cli --port 5000 --duration 30

# Emisor en consola hacia 192.168.1.42
python -m micro_remote emisor --cli --host 192.168.1.42 --port 5000 --gain 1.2

# Equivalente con el lanzador antiguo
python cmd_emisor.py --host 192.168.1.42
python cmd_receptor.py --port 5000
```

### 6.4 Salida en consola

- El emisor muestra paquetes enviados, bitrate y duración.
- El receptor muestra paquetes recibidos, perdidos, bitrate y la IP de origen.
- `Ctrl+C` detiene la sesión y, en el receptor, imprime un resumen (paquetes, pérdidas y bytes).
- Códigos de salida: `0` correcto, `1` error de audio/red, `2` argumentos inválidos.

---

## 7. Estructura del proyecto

```text
Micro_Remote/
├─ micro_remote/                 Paquete principal
│  ├─ __init__.py                Versión y nombres públicos
│  ├─ __main__.py                CLI unificada (emisor, receptor, scan, devices)
│  ├─ config.py                  Constantes y AudioConfig
│  ├─ dsp.py                     PCM, ganancia, RMS, pico y envolvente
│  ├─ protocol.py                Cabecera de paquete y SequenceTracker
│  ├─ net.py                     IPs, Peer, descubrimiento y barrido ICMP
│  ├─ audio/                     Capa de audio sobre sounddevice/PortAudio
│  │  ├─ __init__.py             API pública (Sender, Receiver, Device...)
│  │  ├─ backend.py              Carga diferida, dispositivos y errores
│  │  ├─ engine.py               AudioEngine y EngineStats
│  │  ├─ sender.py               Captura y transmisión
│  │  └─ receiver.py             Recepción y reproducción
│  ├─ settings.py                Persistencia JSON de preferencias
│  ├─ resources.py               Rutas de recursos en desarrollo y congelado
│  ├─ formatting.py              Formato de bitrate, tiempo, bytes, nivel
│  ├─ assets/                    Iconos incluidos en el paquete
│  │  ├─ emisor.ico
│  │  └─ receptor.ico
│  ├─ ui/
│  │  ├─ __init__.py
│  │  ├─ theme.py                Paleta y estilos ttk
│  │  ├─ window.py               Tamaño, centrado e icono
│  │  ├─ widgets.py              Card, StatusPill, MetricTile, LevelMeter...
│  │  ├─ scope.py                Osciloscopio sobre Canvas
│  │  ├─ base.py                 Ventana base y máquina de estados
│  │  ├─ emisor.py               Ventana del emisor
│  │  └─ receptor.py             Ventana del receptor
│  ├─ cli/
│  │  ├─ __init__.py
│  │  ├─ emisor.py               Emisor sin interfaz
│  │  ├─ receptor.py             Receptor sin interfaz
│  │  ├─ scan.py                 Búsqueda desde consola
│  │  └─ devices.py              Listado de dispositivos
│  └─ tools/
│     ├─ __init__.py
│     └─ icons.py                Generación de .ico multi-resolución
├─ tests/                        Pruebas unittest
│  ├─ __init__.py
│  ├─ test_audio.py
│  ├─ test_dsp.py
│  ├─ test_formatting.py
│  ├─ test_net.py
│  ├─ test_protocol.py
│  └─ test_settings.py
├─ icons/                        Recursos de imagen
│  ├─ emisor.jpeg
│  ├─ receptor.jpeg
│  └─ ico/
│     ├─ emisor.ico
│     └─ receptor.ico
├─ Diseño/                       Imágenes de referencia del diseño
├─ interface_emisor.py           Lanzador de la interfaz (compatibilidad)
├─ interface_receptor.py         Lanzador de la interfaz (compatibilidad)
├─ cmd_emisor.py                 Lanzador de consola (compatibilidad)
├─ cmd_receptor.py               Lanzador de consola (compatibilidad)
├─ convert_to_ico.py             Generador de iconos (compatibilidad)
├─ emisor.spec                   PyInstaller: dist/emisor.exe
├─ receptor.spec                 PyInstaller: dist/receptor.exe
├─ build.ps1                     Compilación de ambos ejecutables
├─ requirements.txt              Dependencias de ejecución
├─ requirements-dev.txt          Dependencias de desarrollo
├─ pyproject.toml                Metadatos, scripts y paquete
├─ README.md                     Inicio rápido
├─ DOC.md                        Este documento
└─ .gitignore
```

**Regla de dependencias:** `cli/` y `ui/` pueden importar el núcleo (`config`, `dsp`, `protocol`, `net`, `audio`, `settings`, `formatting`, `resources`); el núcleo **nunca** importa `ui` ni `cli`.

---

## 8. Arquitectura

### 8.1 Capas

```text
┌──────────────────────────────────────────────────────────────┐
│  Presentación                                                │
│  ui/ (Tkinter)                     cli/ (texto)              │
│  emisor.py, receptor.py, base.py   emisor.py, receptor.py    │
│  widgets.py, scope.py, theme.py    scan.py, devices.py       │
└───────────────────────────┬──────────────────────────────────┘
                            │ usa
┌───────────────────────────▼──────────────────────────────────┐
│  Dominio                                                     │
│  audio/ (Sender / Receiver)     net.py (Peer, descubrimiento)│
│  settings.py (preferencias)     protocol.py (paquetes)       │
└───────────────────────────┬──────────────────────────────────┘
                            │ usa
┌───────────────────────────▼──────────────────────────────────┐
│  Base                                                        │
│  config.py (constantes)   dsp.py (PCM y medidas)             │
│  formatting.py            resources.py                       │
└──────────────────────────────────────────────────────────────┘
```

### 8.2 Hilos

| Hilo | Quién lo crea | Función |
| --- | --- | --- |
| Principal | Tkinter | Toda la interfaz, sondeo cada 50 ms y cierre. |
| `Sender` / `Receiver` | `AudioEngine.start()` | Captura o reproduce audio y envía/recibe UDP. |
| `network-scan` | Ventana del emisor | `find_peers()` sin bloquear la interfaz. |
| `discovery-responder` | Ventana del receptor | Responde a los `probe` de descubrimiento. |

**Regla de oro:** ningún hilo secundario toca Tkinter. Los motores escriben su estado en atributos (`level`, `peak`, `wave`, `error`, contadores) y la ventana los lee desde `_poll()`. Los mensajes de los hilos de red se depositan en una `queue.Queue` (`post()`), que la ventana vacía en `_drain_events()`.

### 8.3 Máquina de estados

`BaseAudioApp` implementa los estados `idle → starting → running → stopping → idle` y `error`. Las subclases solo aportan:

| Método | Responsabilidad |
| --- | --- |
| `create_engine()` | Crear `Sender` o `Receiver`. |
| `build_connection(parent)` | Tarjeta de conexión/recepción. |
| `build_audio(parent)` | Tarjeta de dispositivo y ganancia. |
| `start_engine()` | Arrancar el motor con los valores de la interfaz. |
| `stop_engine()` | Liberar recursos propios (p. ej. el respondedor). |
| `validate()` | Devolver un mensaje si los datos no son válidos. |
| `collect_settings()` | Guardar los valores de la interfaz en `Settings`. |
| `detail_text(stats)` | Línea informativa bajo las métricas. |

La parada se ejecuta en un hilo aparte (`_shutdown_async`) para que `stop()` o `join()` no congelen la ventana. La UI detecta el final en el siguiente sondeo.

### 8.4 Cierre ordenado

`close()`:

1. Marca `_closed` para que el sondeo deje de reprogramarse.
2. Cancela el `after` pendiente (`after_cancel`) y evita el error `invalid command name "..._poll"`.
3. Guarda los ajustes.
4. Detiene el motor y el respondedor (con tiempo límite).
5. Destruye la ventana.

---

## 9. Flujo de audio

### 9.1 Emisor

```text
micrófono
   │  sounddevice (RawInputStream, int16, mono, 44100 Hz, 1024 frames)
   ▼
bytes nativos ──► pcm_from_native() ──► array('h')
   │
   ├─► rms() / peak() ────────────────► medidor y osciloscopio
   │
   ├─► apply_gain(gain) ──► pcm_to_bytes() ──► PCM little-endian
   │
   └─► build_packet(secuencia, pcm) ──► sendto(IP, puerto)
```

- Un bloque de 1024 muestras a 44 100 Hz dura **≈ 23,2 ms**.
- El paquete viaja con cabecera de 8 bytes + 2048 bytes de audio = **2056 bytes**.
- El bitrate útil es **≈ 706 kbps** (44 100 × 16 bits).
- El socket de envío usa `SO_SNDBUF` de 256 KiB.

### 9.2 Receptor

```text
socket UDP (0.0.0.0:puerto, SO_RCVBUF 1 MiB)
   │
   ▼
parse_packet() ──► cabecera MR / PCM heredado
   │
   ├─► SequenceTracker.update() ──► perdidos, tardíos, duplicados
   │
   ├─► pcm_from_bytes() ──► array('h')
   │
   ├─► rms() / peak() ──► medidor y osciloscopio
   │
   └─► apply_gain(volumen) ──► pcm_to_native() ──► stream.write()
```

- El socket usa un tiempo de espera de 0,4 s para poder comprobar la señal de parada.
- Los paquetes no válidos o vacíos se descartan sin cortar la reproducción.
- El receptor no reordena paquetes: reproduce en orden de llegada (UDP). Los tardíos se contabilizan.
- Los desbordes del búfer de entrada y los vacíos de salida se cuentan en `overflows` / `underflows`; la interfaz los muestra en la línea de detalle cuando ocurren.

### 9.3 Latencia

La latencia total depende del búfer de la tarjeta de sonido, del sistema operativo y de la red. En una LAN cableada suele estar en decenas de milisegundos. El bloque de 23 ms es un equilibrio entre latencia y número de paquetes por segundo (≈ 43 paquetes/s).

---

## 10. Protocolo UDP

### 10.1 Cabecera

Cada datagrama comienza con 8 bytes:

| Campo | Tamaño | Tipo | Valor |
| --- | --- | --- | --- |
| `magic` | 2 B | bytes | `b"MR"` (0x4D 0x52) |
| `version` | 1 B | entero | `1` |
| `flags` | 1 B | entero | `0` (reservado) |
| `sequence` | 4 B | entero sin signo | Contador incremental, big-endian |
| `payload` | n B | bytes | PCM 16 bits little-endian |

Formato `struct`: `!2sBBI` (big-endian, sin relleno).

Ejemplo de paquete con 4 muestras:

```text
4D 52 01 00 00 00 00 07   PCM PCM PCM PCM
└─MR─┘ │  │  └secuencia─┘
       │  └ flags
       └ versión
```

### 10.2 Compatibilidad con PCM crudo

Si un datagrama **no** empieza por `MR`, se interpreta como **PCM heredado** (formato de la versión 1):

- `AudioPacket.legacy = True`.
- `AudioPacket.sequence = -1`.
- El `SequenceTracker` lo cuenta como recibido, sin pérdidas ni duplicados.

Esto permite que un emisor antiguo alimente al receptor nuevo y que se pueda probar con herramientas como `netcat`. El emisor nuevo siempre envía cabecera. Los datagramas con magic `MR` pero versión distinta de `1` se descartan para no convertir una cabecera desconocida en audio audible. Los payloads de longitud impar también se descartan.

### 10.3 Secuencias y pérdidas

`SequenceTracker` mantiene la última secuencia vista y clasifica cada paquete:

| Resultado | Significado |
| --- | --- |
| `ok` | Paquete en orden. |
| `lost` | Hubo un salto: se suman `delta - 1` pérdidas. |
| `duplicate` | Secuencia ya vista en la ventana reciente (no suma pérdida). |
| `late` | Secuencia anterior; si estaba contada como perdida, se descuenta. |
| `legacy` | Paquete sin cabecera. |

- La comparación usa aritmética de 32 bits: `delta = (seq - last) & 0xFFFFFFFF`.
- Un `delta < 0x80000000` se considera avance; el resto, reordenación.
- Se recuerdan hasta 4 096 secuencias y huecos para detectar duplicados y tardíos.
- `loss_ratio = lost / (recibidos únicos + perdidos)`.

### 10.4 Tamaño máximo

El receptor acepta datagramas de hasta **65 507 bytes** (carga útil máxima UDP IPv4) y exige que la carga PCM tenga longitud par. Con el formato actual (2 056 bytes por paquete) hay margen de sobra; si en el futuro se aumenta `chunk`, hay que vigilar el MTU (1 500 bytes en Ethernet) para evitar fragmentación IP. `AudioConfig` rechaza configuraciones cuyo paquete exceda ese límite.

---

## 11. Descubrimiento de receptores

### 11.1 Protocolo

Puerto **5001/UDP**.

```text
Emisor                                      Receptor (sesión activa)
   │  MRD1?  ──────────────────────────────►  │
   │  (broadcast + 127.0.0.1 + broadcast /24) │
   │                                           │
   │  ◄──────────────  MRD1!{"name":...,       │
   │                    "port":5000}           │
```

- **Sonda:** `b"MRD1?"`.
- **Respuesta:** `b"MRD1!"` + JSON UTF-8 con `name` (máx. 60 caracteres) y `port`.
- El emisor escucha respuestas durante el tiempo indicado (1,5 s por defecto) y deduplica por `(IP, puerto)`.
- Se envían sondas a `255.255.255.255`, a `127.0.0.1` y al broadcast de cada red `/24` local. Así funciona también con emisor y receptor en el mismo equipo.

### 11.2 Respondedor

`DiscoveryResponder` se inicia al arrancar la recepción y se detiene al pararla. Escucha en `0.0.0.0:5001`, con tiempo de espera de 0,4 s para poder cerrarse. Si el puerto está ocupado, informa al registro («Descubrimiento inactivo…») pero la recepción de audio continúa.

> Importante: un receptor **inactivo** no responde. Es intencionado: solo anuncia un puerto cuando realmente está escuchando audio.

### 11.3 Reserva: barrido ICMP

Si no hay respuestas y el barrido está habilitado, `find_peers()` hace `ping` a los hosts de las redes `/24` locales:

- Se excluyen las IP propias y las redes loopback.
- Máximo **1 024 hosts por red** (`MAX_SCAN_HOSTS`).
- **64 trabajadores** concurrentes y 600 ms de espera por host.
- Los hosts que responden se devuelven como `Peer(ip, DEFAULT_PORT)`, sin nombre.
- Se puede cancelar con `should_stop` (al cerrar la ventana o pulsar de nuevo).

El barrido puede tardar varios segundos y solo encuentra equipos que respondan a ICMP (algunos firewalls lo bloquean).

### 11.4 Firewall

Para que el descubrimiento y el audio funcionen en Windows, permite:

- Entrada UDP en el puerto **5000** (audio).
- Entrada UDP en el puerto **5001** (descubrimiento).
- En redes públicas, Windows puede bloquear el broadcast; usa la IP manual o el barrido.

---

## 12. Audio y DSP

### 12.1 Formato

`AudioConfig` (en `config.py`) define:

| Parámetro | Valor | Nota |
| --- | --- | --- |
| `rate` | 44 100 Hz | Frecuencia de muestreo. |
| `channels` | 1 | Mono. |
| `chunk` | 1 024 muestras | ≈ 23,2 ms por bloque. |
| `sample_width` | 2 bytes | Solo PCM de 16 bits. |

Propiedades derivadas: `frame_bytes = 2`, `packet_bytes = 2 048`, `packet_ms ≈ 23,22`.

Los motores abren `sounddevice.RawInputStream` / `RawOutputStream` con `dtype="int16"` y `blocksize=chunk`. Al ser streams «Raw» trabajan con buffers de bytes y **no requieren NumPy**. El flujo se inicia explícitamente con `stream.start()` y se cierra con `stop()` + `close()`.

### 12.2 Funciones de `dsp.py`

| Función | Descripción |
| --- | --- |
| `pcm_from_bytes(data)` | Bytes little-endian de red → `array('h')` local (hace `byteswap` en big-endian). |
| `pcm_to_bytes(samples)` | `array('h')` → bytes little-endian para la red. |
| `pcm_from_native(data)` | Bytes nativos de sounddevice → `array('h')`. |
| `pcm_to_native(samples)` | Muestras → bytes nativos para la tarjeta. |
| `apply_gain(samples, gain)` | Multiplica y recorta a `[-32768, 32767]`; `gain == 1.0` no copia. |
| `rms(samples)` | Nivel eficaz normalizado 0..1. |
| `peak(samples)` | Valor absoluto máximo normalizado 0..1. |
| `envelope(samples, buckets)` | Pares (mínimo, máximo) por columna para el osciloscopio. |
| `normalized(samples)` | Generador de muestras en `-1..1`. |

Decisiones:

- `array('h')` ocupa 2 bytes por muestra y evita NumPy.
- El recorte evita el desbordamiento y el ruido de saturación.
- `envelope` conserva los picos, por lo que una señal rápida no desaparece al reducirla al ancho del canvas.

### 12.3 Medidores

- **Nivel:** `rms()` en 0..1 → dBFS (`20·log10`). Menos de `1e-5` se muestra como «silencio».
- **Barra:** 42 segmentos en escala logarítmica de −60 a 0 dBFS; verde hasta ~65 %, ámbar hasta ~88 %, rojo por encima. Incluye marcador de pico con caída lenta.
- **Osciloscopio:** actualiza la envolvente al ancho del canvas con autoescala visual; se limpia y reinicia la ganancia al iniciar, terminar o fallar.

---

## 13. Ajustes y persistencia

### 13.1 Ubicación

| Sistema | Ruta |
| --- | --- |
| Windows | `%APPDATA%\MicroRemote\settings-emisor.json` y `settings-receptor.json` |
| Linux/macOS | `~/.config/MicroRemote/settings-emisor.json` y `settings-receptor.json` |
| Pruebas | Variable `MICRO_REMOTE_HOME` (usa esa carpeta) |

Si `MICRO_REMOTE_HOME` está definida, se usa como carpeta de ajustes (útil para pruebas y para ejecutables portables). Cada aplicación guarda su propio archivo, de modo que cerrar una no sobrescribe la configuración de la otra. Si existe un `settings.json` antiguo y aún no hay archivo por rol, se usa como punto de partida.

### 13.2 Formato

```json
{
  "host": "192.168.1.42",
  "port": 5000,
  "gain": 1.0,
  "input_device": 1,
  "output_device": null
}
```

| Campo | Tipo | Validación |
| --- | --- | --- |
| `host` | string | IPv4 válida; si no, se usa `127.0.0.1`. |
| `port` | entero | 1–65535; si no, 5000. |
| `gain` | número | Se limita a 0.0–5.0. |
| `input_device` | entero o `null` | Índice ≥ 0; si no, `null` (predeterminado). |
| `output_device` | entero o `null` | Índice ≥ 0; si no, `null` (predeterminado). |

### 13.3 Comportamiento

- `Settings.load()` **nunca lanza** por datos inválidos: devuelve los valores por defecto que correspondan.
- `Settings.save()` escribe primero un `.tmp` único por proceso y luego lo renombra (`replace`), evitando archivos a medias y colisiones entre instancias.
- Los valores no finitos de ganancia (`NaN`, `Infinity`) se sustituyen por el valor por defecto al cargar.
- El archivo de cada rol se guarda al cerrar su ventana y al iniciar cada sesión (los valores se copian a `settings`).
- Los cambios de ganancia se aplican al motor en caliente (`engine.gain`), sin reiniciar el audio.

### 13.4 Restablecer

Cierra la aplicación y borra `settings-emisor.json` / `settings-receptor.json` (o define `MICRO_REMOTE_HOME` a una carpeta vacía para una sesión limpia).

---

## 14. Diseño de la interfaz

### 14.1 Composición

```text
┌────────────────────────────────────────────────────────────────┐
│ [MR] Micro Remote                          ● Transmitiendo  v2 │
│      Transmite el audio de tu micrófono a otro equipo          │
├────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────┐  ┌──────────────────────────────┐ │
│ │ CONEXIÓN                 │  │ RESUMEN                      │ │
│ │ IP, puerto, Buscar       │  │ [Enviados][Destino]…         │ │
│ │ Dispositivos detectados  │  ├──────────────────────────────┤ │
│ ├──────────────────────────┤  │ SEÑAL DE AUDIO               │ │
│ │ MICRÓFONO                │  │ AUTO ×96.9   PICO -40.8 dBFS │ │
│ │ Dispositivo, ganancia    │  │ ~~~~ forma de onda ~~~~      │ │
│ ├──────────────────────────┤  │ NIVEL ▓▓▓░░░░░  -40.9 dBFS   │ │
│ │ CONTROLES                │  ├──────────────────────────────┤ │
│ │ [Iniciar] [Detener]      │  │ REGISTRO                     │ │
│ │ F5 iniciar · F6 detener  │  │ 12:00:00  mensaje…           │ │
│ └──────────────────────────┘  └──────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

- Columna izquierda: 420 px mínimos; columna derecha elástica.
- La tarjeta de controles se ancla al fondo de la columna izquierda.
- Espaciado basado en una rejilla de 8 px, bordes de 1 px y títulos de tarjeta en versalitas.
- Todo el contenido usa `pack`/`grid` con expansión; la ventana se puede redimensionar.

### 14.2 Paleta

La paleta replica los tonos `slate` e `indigo` de Tailwind CSS. La misma gama se usa en todas las ventanas.

| Constante | Color | Uso |
| --- | --- | --- |
| `BG` | `#020617` | Fondo de la ventana (slate-950). |
| `SURFACE` | `#0F172A` | Tarjetas (slate-900). |
| `SURFACE_ALT` | `#1E293B` | Controles, registro, listas (slate-800). |
| `SURFACE_HOVER` | `#334155` | Hover de botones (slate-700). |
| `BORDER` | `#1E293B` | Bordes suaves. |
| `BORDER_STRONG` | `#334155` | Bordes activos. |
| `TEXT` | `#F8FAFC` | Texto principal (slate-50). |
| `MUTED` | `#94A3B8` | Texto secundario (slate-400). |
| `DISABLED` | `#64748B` | Texto deshabilitado (slate-500). |
| `ACCENT` | `#6366F1` | Acento, botón principal (indigo-500). |
| `ACCENT_HOVER` | `#818CF8` | Hover del acento (indigo-400). |
| `ACCENT_DARK` | `#4F46E5` | Pulsado (indigo-600). |
| `ACCENT_SOFT` | `#312E81` | Fondos de acento y selección (indigo-900). |
| `SUCCESS` | `#34D399` | Estado correcto (emerald-400). |
| `WARNING` | `#FBBF24` | Aviso, preparando (amber-400). |
| `DANGER` | `#FB7185` | Error, detener (rose-400). |
| `SCOPE_BG` | `#020617` | Fondo del osciloscopio. |
| `SCOPE_FILL` | `#1E1B4B` | Relleno de la onda (indigo-950). |
| `SCOPE_GLOW` | `#312E81` | Resplandor del trazo. |
| `SCOPE_LINE` | `#A5B4FC` | Trazo de la onda (indigo-300). |
| `GRID` | `#1E293B` | Rejilla del osciloscopio. |

Los estados usan además fondos suaves (`SUCCESS_SOFT`, `WARNING_SOFT`, `DANGER_SOFT`) y textos tintados para las píldoras de estado.

Tipografía: **Segoe UI** (Windows) / DejaVu Sans; monoespaciada **Consolas** / DejaVu Sans Mono. Las etiquetas de sección son de 7 pt en negrita y mayúsculas; los valores usan 12 pt y reducen hasta 8 pt si el texto no cabe (por ejemplo, una IP larga en la columna mínima).

### 14.3 Autoescala del osciloscopio

La onda se dibuja con una ganancia **solo visual**, independiente de la ganancia de audio:

- `AutoGain` calcula el factor para que el pico de cada bloque llene aproximadamente el 90 % de la altura.
- La ganancia sube despacio y baja rápido, evitando bombeos y recortes visuales.
- El factor se limita a `×160` (+44 dB) y solo se actualiza por encima de una puerta de `0.0005` (−66 dBFS).
- La lectura `AUTO ×N` muestra el factor aplicado; `PICO` y `NIVEL` siguen siendo valores reales en dBFS.
- El audio transmitido no se normaliza ni se modifica por esta autoescala.

El medidor de nivel usa una escala logarítmica de −60 a 0 dBFS. Una señal de −40 dBFS enciende aproximadamente un tercio de la barra, en lugar de quedar prácticamente apagada como ocurriría con una escala lineal.

### 14.4 Estilos ttk

| Estilo | Uso |
| --- | --- |
| `Card.TFrame` | Interior de las tarjetas. |
| `Field.TLabel` | Etiquetas de formulario. |
| `CardOverline.TLabel` | Títulos de sección y etiquetas en versalitas. |
| `CardReading.TLabel` | Lecturas numéricas monoespaciadas. |
| `Accent.TButton` | Acción principal (iniciar). |
| `Danger.TButton` | Detener (contorno rosa). |
| `Ghost.TButton` | Acciones secundarias (copiar). |
| `Scan.TButton` | Buscar (acento suave). |
| `Dark.TEntry` / `Dark.TCombobox` | Campos de texto y desplegables. |
| `Accent.Horizontal.TScale` | Ganancia/volumen. |
| `Value.TLabel`, `Ip.TLabel`, `CardMuted.TLabel` | Valores y textos de apoyo. |

El tema base es `clam`, reconfigurado por completo en `theme.py`. Los desplegables nativos se ajustan con `option_add` para que la lista también sea oscura.

### 14.5 Widgets propios

| Widget | Función |
| --- | --- |
| `StatusPill` | Píldora redondeada con punto de color y estado. |
| `MetricTile` | Tarjeta pequeña título/valor. |
| `LevelMeter` | Barra segmentada en dBFS con marcador de pico. |
| `LogPanel` | Registro con hora, color por nivel y máximo de 400 líneas. |
| `PeerList` | Lista de receptores con selección. |
| `AudioScope` | Osciloscopio con rejilla, envolvente y autoescala visual. |
| `Card` | Marco con borde, título en versalitas y cuerpo interior. |
| `muted_note` | Texto de ayuda pequeño, opcionalmente ajustado. |

Niveles del registro: `time` (gris), `info` (texto), `ok` (verde), `warn` (ámbar), `error` (rojo), `muted` (gris).

---

## 15. Referencia de módulos

### `micro_remote/config.py`

Constantes de la aplicación y `AudioConfig`.

- `APP_NAME`, `APP_VERSION`, `APP_TAGLINE`.
- `DEFAULT_PORT = 5000`, `DISCOVERY_PORT = 5001`, `DISCOVERY_TIMEOUT = 1.5`, `DISCOVERY_MAGIC = b"MRD1"`.
- `MIN_GAIN = 0.0`, `MAX_GAIN = 5.0`, `DEFAULT_GAIN = 1.0`, `GAIN_STEP = 0.1`.
- `WINDOW_SIZE = (1120, 860)`, `MIN_WINDOW_SIZE = (980, 800)`.
- `SETTINGS_FILENAME`, `SETTINGS_DIRNAME`, `SETTINGS_ENV_VAR`.

### `micro_remote/dsp.py`

Conversión PCM, ganancia y medidas. Ver [§12.2](#122-funciones-de-dsppy).

### `micro_remote/protocol.py`

- `build_packet(sequence, payload) -> bytes`.
- `parse_packet(data) -> AudioPacket | None`.
- `AudioPacket(sequence, payload, legacy)`.
- `SequenceTracker` con `received`, `lost`, `late`, `duplicates`, `loss_ratio`.
- Constantes `MAGIC`, `VERSION`, `HEADER_SIZE = 8`, `LEGACY_SEQUENCE = -1`.

### `micro_remote/net.py`

- Direcciones: `primary_ip()`, `local_ips()`, `local_subnets()`, `is_valid_ipv4()`, `is_valid_port()`, `ip_key()`.
- `Peer(ip, port, name)` con `.label`.
- `DiscoveryResponder(audio_port, name, port, on_error)` con `start()` / `stop()`.
- `discover(timeout, port) -> list[Peer]`.
- `ping_host(ip, timeout_ms, should_stop) -> bool`.
- `scan_network(networks, own_ips, max_workers, should_stop) -> list[str]`.
- `find_peers(timeout, sweep, should_stop, on_stage, default_port) -> list[Peer]`.

### `micro_remote/audio/`

Capa de audio sobre `sounddevice` (PortAudio), dividida en cuatro módulos.

**`backend.py`**

- `AudioError` — error controlado con mensaje amigable.
- `load_sounddevice()` — importación diferida; lanza `AudioError` con instrucciones si falta.
- `Device(index, name, channels, default, hostapi)` con `.display_name`.
- `audio_devices(kind) -> list[Device]` (`"input"` / `"output"`), con el nombre del host API (MME, DirectSound, WASAPI, WDM-KS…).
- `friendly_error(exc) -> str` — traduce errores de PortAudio y de red.
- `close_stream(stream)` — parada y cierre seguros.

**`engine.py`**

- `EngineStats(packets, lost, late, bytes_total, seconds, overflows, underflows)` con `.kbps` y `.loss_ratio`.
- `AudioEngine` — ciclo de vida: `start()`, `stop()`, `running`, `stats()`; contadores `overflows` (entrada) y `underflows` (salida).

**`sender.py`**

- `Sender.start(host, port, device)`; atributo `destination`.
- Usa `sounddevice.RawInputStream` (int16) y `SO_SNDBUF` de 256 KiB.

**`receiver.py`**

- `Receiver.start(port, device)`; atributo `source`.
- Usa `sounddevice.RawOutputStream` (int16), `SequenceTracker` y `SO_RCVBUF` de 1 MiB.

La importación de `sounddevice` es diferida: si falta, `start()` deja `engine.error` con un mensaje que la interfaz muestra en el registro y en un cuadro de diálogo. Los streams «Raw» trabajan con bytes, así que **no se necesita NumPy**; el flujo se inicia explícitamente con `stream.start()`.

### `micro_remote/settings.py`

- `settings_dir()`, `settings_path()`.
- `Settings(host, port, gain, input_device, output_device)`.
- `Settings.load(path=None)`, `Settings.save(path=None) -> Path`.

### `micro_remote/resources.py`

- `app_root()` — raíz del proyecto o `sys._MEIPASS` si está congelado.
- `asset_path(*parts)`.
- `icon_path(name)` — busca en `icons/ico`, `icons` y `micro_remote/assets`.

### `micro_remote/formatting.py`

`format_gain`, `format_level`, `format_bitrate`, `format_duration`, `format_bytes`.

### `micro_remote/ui/`

- `theme.apply_theme(root)` — aplica la paleta y devuelve el `ttk.Style`.
- `window.center_window`, `window.apply_icon`, `window.configure_window`.
- `base.BaseAudioApp` — ventana, estados, sondeo y eventos.
- `emisor.SenderApp`, `receptor.ReceiverApp` — ventanas concretas.
- `emisor.main()`, `receptor.main()` — puntos de entrada con valores opcionales de host/puerto/ganancia/dispositivo.
- `scope.AudioScope`, `widgets.*`.

### `micro_remote/__main__.py`

`build_parser()` y `main(argv=None)`. Punto de entrada de `micro-remote` y de `python -m micro_remote`.

### `micro_remote/cli/`

`run(args)` en `emisor`, `receptor`, `scan` y `devices`.

---

## 16. Pruebas

### 16.1 Ejecución

```powershell
python -m unittest discover -s tests -t . -v
```

Las 86 pruebas cubren:

| Archivo | Qué comprueba |
| --- | --- |
| `test_dsp.py` | Conversión de bytes, ganancia, recorte, valores no finitos, RMS, pico y envolvente. |
| `test_protocol.py` | Cabecera, ida y vuelta, PCM heredado, longitud par, tamaño máximo, versiones, secuencias, pérdidas, tardíos y duplicados. |
| `test_settings.py` | Valores por defecto, validación, ganancia no finita, archivos por rol, guardado atómico y `MICRO_REMOTE_HOME`. |
| `test_net.py` | Validación y normalización de IP/puerto, respuestas malformadas, orden de IPs y descubrimiento en `127.0.0.1`. |
| `test_formatting.py` | Formatos de ganancia, nivel en dBFS, fracción logarítmica del medidor, bitrate, duración y bytes. |
| `test_audio.py` | Dispositivos, errores de PortAudio/red, estadísticas y carrera de reinicio de sesiones. |
| `test_entrypoints.py` | Lanzador posicional de la v1 y validación de argumentos de la CLI. |
| `test_ui_logic.py` | Autoescala del osciloscopio y centrado de la ventana en pantallas normales y pequeñas. |

### 16.2 Características

- No requieren `sounddevice` ni tarjeta de sonido: el backend se importa de forma diferida y las pruebas lo sustituyen por un doble.
- La prueba de `load_sounddevice()` simula la ausencia del módulo con `sys.modules`.
- El descubrimiento se prueba contra un respondedor real en un puerto UDP efímero (anunciando audio en 6123) y contra un puerto sin respondedor.
- Usan `tempfile` y `MICRO_REMOTE_HOME` para no tocar los ajustes reales.

### 16.3 Añadir pruebas

Crea `tests/test_mimodulo.py` con `unittest.TestCase`. Los módulos del paquete se importan como `micro_remote.*`; ejecuta desde la raíz del proyecto para que `tests` y el paquete estén en el camino.

---

## 17. Iconos

- Los iconos finales están en `icons/ico/emisor.ico` y `icons/ico/receptor.ico`.
- También se copian a `micro_remote/assets/` para que funcionen al instalar el paquete.
- `micro_remote/tools/icons.py` convierte `.jpg`, `.jpeg` o `.png` a `.ico` multi-resolución (16, 24, 32, 48, 64, 128 y 256 px), centrado sobre un lienzo transparente de 256 × 256.

```powershell
python convert_to_ico.py
python -m micro_remote.tools.icons --source icons --output icons/ico
```

Requiere Pillow (`requirements-dev.txt`). Si un icono no existe, la ventana arranca sin él (no es un error fatal).

---

## 18. Empaquetado con PyInstaller

### 18.1 Especificaciones

- `emisor.spec` → `dist/emisor.exe` (sin consola).
- `receptor.spec` → `dist/receptor.exe` (sin consola).

Ambas incluyen:

- `pathex` con la raíz del proyecto.
- `datas`: `icons/`, `micro_remote/assets/` y las DLL de PortAudio de `sounddevice` (`_sounddevice_data/portaudio-binaries/*.dll`).
- `hiddenimports`: `sounddevice` y `_sounddevice_data`.
- `excludes`: `numpy`, `matplotlib`, `PIL`, `pytest`, `tests` (no se usan en ejecución).
- Icono del ejecutable desde `icons/ico/`.

### 18.2 Compilación

```powershell
pip install -r requirements-dev.txt
.\build.ps1
```

Opciones:

```powershell
.\build.ps1 emisor       # solo el emisor
.\build.ps1 receptor     # solo el receptor
.\build.ps1 -Clean       # borra build/ y dist/ antes
```

O directamente:

```powershell
pyinstaller --noconfirm --clean emisor.spec
pyinstaller --noconfirm --clean receptor.spec
```

### 18.3 Notas

- `sounddevice` se importa dentro de una función, así que los `.spec` lo declaran en `hiddenimports` y copian la DLL de PortAudio con `collect_data_files("_sounddevice_data", includes=["portaudio-binaries/*.dll"])`. Si el ejecutable falla al abrir el audio, comprueba que `_sounddevice_data` esté en `hiddenimports` y que el `.spec` se ejecute en el mismo entorno donde está instalado `sounddevice`.
- Los ejecutables se distribuyen juntos si se quiere que el descubrimiento funcione: el receptor debe estar en ejecución.
- El `.spec` no incrusta ajustes: cada usuario guarda los suyos en `%APPDATA%`.

---

## 19. Solución de problemas

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| «sounddevice no está disponible» | Falta la dependencia o el entorno virtual no está activado. | `pip install -r requirements.txt` dentro del entorno correcto. |
| «No se pudo cargar PortAudio» | DLL ausente o bloqueada (antivirus, instalación incompleta). | Reinstala `sounddevice`; en Linux instala `libportaudio2`. |
| «El dispositivo de audio seleccionado no está disponible» | Índice obsoleto tras cambiar de hardware o de backend. | Elige «Sistema (predeterminado)» o vuelve a seleccionar el dispositivo. |
| «El dispositivo no admite este formato» | El dispositivo no acepta 44,1 kHz mono 16 bits. | Prueba otra entrada/salida o los ajustes de sonido de Windows. |
| «El puerto ya está en uso» | Otra instancia o programa usa el puerto. | Cambia el puerto UDP en ambos extremos o cierra la otra instancia. |
| No se oye nada | Receptor sin sesión, IP/puerto incorrectos o firewall. | Inicia la recepción, revisa IP/puerto y permite UDP 5000/5001. |
| «Buscar» no encuentra nada | Broadcast bloqueado, receptor inactivo o redes distintas. | Inicia la recepción en el receptor, escribe la IP a mano o usa `scan` (barrido ICMP). |
| El audio se corta o suena metálico | Wi-Fi congestionada, pérdida de paquetes o búfer pequeño. | Usa cable, acerca los equipos al router o baja la carga de la red. |
| El medidor no se mueve | Micrófono silenciado o dispositivo equivocado. | Revisa la entrada y la ganancia; prueba con `devices`. |
| La ventana muestra «Error» al arrancar | Fallo de audio o de red. | Lee el registro y el cuadro de diálogo; pulsa Iniciar de nuevo tras corregir. |
| Los ajustes no se guardan | Permisos en `%APPDATA%` o `MICRO_REMOTE_HOME` no escribible. | Revisa la carpeta o elimina la variable de entorno. |
| `invalid command name "..._poll"` al cerrar | Ya corregido en 2.0 (se cancela el `after`). | Actualiza a la versión actual. |

### Diagnóstico rápido

```powershell
python -m micro_remote devices     # ¿ve el micrófono y los altavoces?
python -m micro_remote receptor --cli --duration 5
python -m micro_remote emisor --cli --host 127.0.0.1 --duration 5
python -m micro_remote scan
```

La prueba en `127.0.0.1` permite verificar el flujo completo en un solo equipo (con dos terminales).

---

## 20. Migración de la versión 1

### 20.1 Cambios principales

| Versión 1 | Versión 2 |
| --- | --- |
| `common.py`, `utils.py` | Repartidos en `micro_remote/` (config, dsp, net, protocol, settings, formatting). |
| Archivos monolíticos por interfaz | `micro_remote/ui/` con ventana base, widgets y tema compartidos. |
| NumPy para DSP | `array` y `math` de la biblioteca estándar. |
| Matplotlib para la onda | `tk.Canvas` (`ui/scope.py`). |
| PyAudio para captura y reproducción | `sounddevice` con streams «Raw» (sin NumPy; compatible con Python 3.14). |
| Sin descubrimiento | Broadcast UDP + barrido ICMP. |
| PCM crudo | Cabecera de 8 bytes (con lectura de PCM crudo para compatibilidad). |
| Ajustes dispersos | `settings-emisor.json` y `settings-receptor.json`, con validación, migración del archivo antiguo y guardado atómico. |
| Hilos que actualizaban la UI | Estado publicado + sondeo cada 50 ms y `queue.Queue`. |

### 20.2 Qué sigue funcionando

- `python interface_emisor.py` y `python interface_receptor.py`.
- `python cmd_emisor.py <IP>` y `python cmd_receptor.py`.
- `python convert_to_ico.py`.
- Un receptor nuevo acepta audio de un emisor antiguo (PCM sin cabecera).
- Los `.spec` de PyInstaller se mantienen, actualizados.

### 20.3 Qué eliminar de instalaciones antiguas

- `common.py`, `utils.py` y carpetas `__pycache__` (ya no se usan).
- Dependencias `numpy`, `matplotlib`, `PyAudio` y `pipwin` (sustituidas por `sounddevice`).

### 20.4 Ajustes

La versión 1 no guardaba ajustes en JSON. En la primera ejecución de la versión 2 se usan los valores por defecto; al cerrar se crean `%APPDATA%\MicroRemote\settings-emisor.json` y `settings-receptor.json`. Si existiera un `settings.json` de una versión 2 anterior, se usa como punto de partida.

Los índices de dispositivo son específicos del backend: si un ajuste guardado con PyAudio apunta a otro hardware bajo `sounddevice`, elige de nuevo el dispositivo en el desplegable. La aplicación muestra un error claro si el índice ya no es válido.

---

## 21. Limitaciones y mejoras futuras

Limitaciones actuales:

- **Sin cifrado ni autenticación:** cualquiera en la red puede escuchar o inyectar audio. Úsalo solo en redes de confianza.
- **Sin reordenación ni recuperación:** UDP no garantiza entrega; los paquetes perdidos producen huecos de ~23 ms.
- **Mono y 44,1 kHz fijos:** no hay negociación de formato ni estéreo.
- **Un emisor por receptor:** el receptor reproduce el último flujo que llega; no mezcla fuentes.
- **Descubrimiento limitado a /24** y a respuestas ICMP para el barrido.
- **Dependencia de `sounddevice`/PortAudio** para el audio real (incluido en los wheels de Windows y macOS).

Ideas para siguientes versiones:

- Códec con compresión (Opus) para reducir ancho de banda.
- Búfer de jitter y reordenación de paquetes.
- Estéreo y selección de frecuencia.
- Contraseña o token compartido y cifrado opcional.
- Historial de dispositivos y favoritos.
- Empaquetado multiplataforma y pruebas de integración de audio.

---

## Apéndice A. Constantes rápidas

| Constante | Valor |
| --- | --- |
| Versión | `2.0.0` |
| Puerto de audio | `5000/UDP` |
| Puerto de descubrimiento | `5001/UDP` |
| Magic de audio | `MR` |
| Magic de descubrimiento | `MRD1` |
| Cabecera de audio | 8 bytes (`!2sBBI`) |
| Audio | PCM 16 bits, mono, 44 100 Hz, LE |
| Bloque | 1024 muestras ≈ 23,2 ms |
| Paquete | 2056 bytes (8 + 2048) |
| Bitrate útil | ≈ 706 kbps |
| Ganancia | 0.0 – 5.0 |
| Sondeo de la UI | 50 ms |
| Ventana | 1120 × 860 (mín. 980 × 800) |

## Apéndice B. Variables de entorno

| Variable | Efecto |
| --- | --- |
| `MICRO_REMOTE_HOME` | Carpeta alternativa para los archivos de ajustes. |
| `APPDATA` | Base de la ruta de ajustes en Windows. |

## Apéndice C. Códigos de salida de la CLI

| Código | Significado |
| --- | --- |
| `0` | Correcto. |
| `1` | Error de audio, de red o de sesión. |
| `2` | Argumentos inválidos. |
