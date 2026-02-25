# 🖥️ CTFArena - Retos Interactivos con Docker

Extensión para CTFArena que permite crear **retos interactivos** donde cada usuario
obtiene una terminal web conectada a su propio contenedor Docker aislado.

## 🏗️ Arquitectura

```
┌──────────────┐     WebSocket      ┌──────────────┐     Docker API     ┌──────────────┐
│   Navegador  │ ◄──────────────► │    Flask +    │ ◄──────────────► │  Contenedor   │
│   xterm.js   │   (socket.io)     │  SocketIO    │   (exec/attach)   │  del usuario  │
└──────────────┘                    └──────────────┘                    └──────────────┘
                                         │
                                    Nginx reverse
                                    proxy + WS
```

Flujo:
1. Usuario pulsa **"Iniciar Instancia"** en un reto interactivo
2. Flask crea un contenedor Docker aislado desde la imagen del reto
3. Se abre la **terminal web** (xterm.js) conectada por WebSocket
4. Flask-SocketIO hace de proxy entre xterm.js y el exec session de Docker
5. El contenedor se auto-destruye al expirar el timeout

## ⚡ Instalación Rápida

```bash
cd /ruta/a/CTFArena
sudo bash integrate_interactive.sh
sudo bash build_challenges.sh
```

## 📦 Retos de Ejemplo Incluidos

| Reto | Categoría | Dificultad | Imagen Docker | Flag |
|---|---|---|---|---|
| Escalada SUID | Pwn | Fácil | `ctfarena/privesc-suid` | `FLAG{su1d_pr1v3sc_m4st3r}` |
| Cron Job Hijack | Pwn | Media | `ctfarena/privesc-cron` | `FLAG{cr0n_j0b_h1j4ck3d}` |
| Credenciales Ocultas | Forensics | Fácil | `ctfarena/forensics-creds` | `FLAG{h1dd3n_cr3d3nt14ls_f0und}` |

## 🔧 Crear tu Propio Reto Interactivo

### 1. Crear el Dockerfile

```bash
mkdir docker-challenges/mi-reto/
nano docker-challenges/mi-reto/Dockerfile
```

Estructura básica:
```dockerfile
FROM ubuntu:22.04

# Instalar herramientas necesarias
RUN apt-get update && apt-get install -y bash nano

# Crear usuario del jugador
RUN useradd -m -s /bin/bash ctfplayer

# Crear la flag
RUN echo "FLAG{mi_flag}" > /root/flag.txt && chmod 600 /root/flag.txt

# Configurar la vulnerabilidad aquí...

USER ctfplayer
CMD ["/bin/bash", "-l"]
```

### 2. Construir la imagen

```bash
# Añadir al build_challenges.sh:
build_challenge "mi-reto" "mi-reto"

# Ejecutar:
sudo bash build_challenges.sh
```

### 3. Configurar en el Admin Panel

1. Ir a **Admin → Gestionar Retos → Nuevo Reto**
2. Rellenar título, descripción, flag, puntos, categoría
3. Marcar **☑ Reto Interactivo**
4. Imagen Docker: `ctfarena/mi-reto`
5. Configurar timeout y red según necesidad
6. Guardar

## 🔒 Seguridad de los Contenedores

Cada contenedor se crea con estas restricciones:
- **Memoria**: 256MB máximo
- **CPU**: 50% de un core
- **PIDs**: máximo 100 procesos (previene fork bombs)
- **Red**: deshabilitada por defecto
- **Capabilities**: todas eliminadas excepto SETUID/SETGID
- **Privilegios**: no-new-privileges activado
- **Timeout**: auto-destrucción a los 30 min (configurable)
- **Límite**: 1 contenedor por usuario simultáneo

## 📁 Estructura de Archivos

```
├── integrate_interactive.sh      # Script de integración
├── build_challenges.sh           # Construye imágenes Docker
├── nginx_websocket.conf          # Config Nginx con WebSocket
├── app/
│   ├── docker_manager.py         # Gestión del ciclo de vida Docker
│   ├── terminal_handler.py       # WebSocket ↔ Docker I/O
│   └── interactive/
│       ├── __init__.py
│       └── routes.py             # Rutas: start/stop/terminal
├── templates/
│   └── interactive/
│       └── terminal.html         # Terminal web con xterm.js
├── docker-challenges/
│   ├── privesc-suid/Dockerfile
│   ├── privesc-cron/Dockerfile
│   └── forensics-creds/Dockerfile
└── patches/                      # Parches para archivos existentes
    ├── admin_challenge_form_patch.html
    ├── challenge_detail_patch.html
    └── python_patches.py
```

## 🛠️ Troubleshooting

**El terminal no conecta:**
- Verifica que Nginx tiene la config de WebSocket: `cat /etc/nginx/sites-enabled/hackarena-ctf`
- Debe tener el bloque `location /socket.io/` con `proxy_set_header Upgrade`

**Error "imagen no encontrada":**
- Ejecuta `sudo bash build_challenges.sh`
- Verifica: `docker images | grep ctfarena`

**Contenedores no se crean:**
- El servicio debe correr como root o el usuario debe estar en el grupo docker
- Verifica: `sudo systemctl status hackarena-ctf`

**Contenedores zombi:**
- Limpiar manualmente: `docker ps -a --filter "label=ctf.session_key" | docker rm -f`
