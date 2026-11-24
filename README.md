# Micro Remote

**Audio en vivo por tu red local.** Un emisor toma el micrófono y lo transmite por UDP a un receptor que lo reproduce en sus altavoces. Pensado para redes de confianza (casa, oficina, aula) y para latencia baja: ~23 ms por paquete.

- Dos interfaces Tkinter independientes: **emisor** y **receptor**.
- Descubrimiento automático de receptores en la red (con barrido ICMP de reserva).
- Interfaz oscura tipo *slate/indigo* con osciloscopio de autoescala para señales débiles, medidor de nivel en dBFS, bitrate, paquetes perdidos y registro en vivo.
- Modo consola para probar sin interfaz.
- Sin NumPy ni Matplotlib: solo la biblioteca estándar, Tkinter y `sounddevice` (PortAudio).

> **Sobre el proyecto:** Micro Remote estuvo en desarrollo durante un tiempo y se concluyó con la ayuda de [OpenCode](https://opencode.ai/), que asistió en la revisión, las correcciones y la finalización del código, las pruebas y la documentación.

## Requisitos

- Python **3.10 o superior** (probado con 3.14 en Windows).
- **sounddevice ≥ 0.5.6** para capturar y reproducir audio (incluye PortAudio en Windows y macOS).
- Tkinter (incluido con el instalador oficial de Python en Windows).

## Instalación

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`sounddevice` trae PortAudio incluido en los wheels de Windows y macOS, así que no hace falta compilador ni una versión concreta de Python. En Linux, si falta la biblioteca del sistema:

```bash
sudo apt install libportaudio2
```

Para desarrollo y generación de ejecutables:

```powershell
pip install -r requirements-dev.txt
pip install -e .
```

## Uso rápido

### Interfaz gráfica

```powershell
python interface_receptor.py    # en el equipo que escucha
python interface_emisor.py      # en el equipo que habla
```

En el emisor escribe la IP del receptor (o pulsa **Buscar**) y **Iniciar transmisión** (`F5`). En el receptor pulsa **Iniciar recepción** (`F6` detiene en ambos).

También puedes usar el lanzador unificado:

```powershell
python -m micro_remote emisor
python -m micro_remote receptor
```

### Consola

```powershell
python -m micro_remote devices
python -m micro_remote scan
python -m micro_remote receptor --cli --port 5000
python -m micro_remote emisor --cli --host 192.168.1.42 --gain 1.2
```

## Estructura

```text
Micro_Remote/
├─ micro_remote/        paquete principal
│  ├─ audio/            capa de audio (PortAudio)
│  │  ├─ backend.py     carga de sounddevice, dispositivos y errores
│  │  ├─ engine.py      ciclo de vida y estadísticas
│  │  ├─ sender.py      captura y transmisión
│  │  └─ receiver.py    recepción y reproducción
│  ├─ net.py            IPs, descubrimiento y escaneo
│  ├─ protocol.py       cabecera de paquete y contador de secuencia
│  ├─ dsp.py            PCM, ganancia, RMS y envolvente
│  ├─ settings.py       preferencias en JSON
│  ├─ ui/               interfaz Tkinter
│  ├─ cli/              modos sin interfaz
│  └─ tools/            generador de iconos
├─ tests/               pruebas unittest
├─ interface_*.py       lanzadores de la interfaz
├─ cmd_*.py             lanzadores de consola
├─ emisor.spec          PyInstaller
└─ receptor.spec        PyInstaller
```

La documentación completa (arquitectura, protocolo, API, empaquetado y solución de problemas) está en **[DOC.md](DOC.md)**.

## Pruebas

```powershell
python -m unittest discover -s tests -t . -v
```

Las pruebas no necesitan tarjeta de sonido ni `sounddevice` instalado.

## Ejecutables

```powershell
.\build.ps1            # emisor y receptor en dist\
.\build.ps1 -Clean     # limpia build/ y dist/ antes
```
