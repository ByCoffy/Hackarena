#!/bin/bash
# =============================================================
# CTFArena - Parche para Retos Interactivos con Docker
# =============================================================
# Este script integra el sistema de retos interactivos en una
# instalación existente de CTFArena.
#
# Uso: cd /ruta/a/CTFArena && sudo bash integrate_interactive.sh
# =============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║  CTFArena - Integración de Retos Interactivos   ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

APP_DIR="$(pwd)"

# --- 1. Install Docker ---
echo -e "${YELLOW}[1/7] Instalando Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    # Add the web user to docker group
    usermod -aG docker www-data
    echo -e "${GREEN}[+] Docker instalado.${NC}"
else
    echo -e "${GREEN}[+] Docker ya está instalado.${NC}"
fi

# --- 2. Install Python dependencies ---
echo -e "${YELLOW}[2/7] Instalando dependencias Python...${NC}"
source "${APP_DIR}/venv/bin/activate"
pip install docker flask-socketio eventlet
echo "docker>=7.0.0" >> "${APP_DIR}/requirements.txt"
echo "flask-socketio>=5.3.0" >> "${APP_DIR}/requirements.txt"
echo "eventlet>=0.36.0" >> "${APP_DIR}/requirements.txt"

# --- 3. Add new model fields ---
echo -e "${YELLOW}[3/7] Añadiendo campos a la base de datos...${NC}"

# Use Python to add columns (safe for existing data)
python3 << 'PYEOF'
import pymysql
import os
from dotenv import load_dotenv
load_dotenv()

db_url = os.environ.get('DATABASE_URL', 'mysql+pymysql://ctf_user:ctf_password@localhost/ctf_platform')
# Parse the URL
parts = db_url.replace('mysql+pymysql://', '').split('@')
user_pass = parts[0].split(':')
host_db = parts[1].split('/')

conn = pymysql.connect(
    host=host_db[0],
    user=user_pass[0],
    password=user_pass[1],
    database=host_db[1]
)

cursor = conn.cursor()

# Add interactive challenge columns if they don't exist
columns_to_add = [
    ("is_interactive", "BOOLEAN DEFAULT FALSE"),
    ("docker_image", "VARCHAR(256) DEFAULT NULL"),
    ("container_timeout", "INTEGER DEFAULT 1800"),
    ("container_network", "BOOLEAN DEFAULT FALSE"),
]

for col_name, col_def in columns_to_add:
    try:
        cursor.execute(f"ALTER TABLE challenges ADD COLUMN {col_name} {col_def}")
        print(f"[+] Columna añadida: {col_name}")
    except pymysql.err.OperationalError as e:
        if "Duplicate column" in str(e):
            print(f"[*] Columna ya existe: {col_name}")
        else:
            raise

conn.commit()
conn.close()
print("[+] Base de datos actualizada.")
PYEOF

# --- 4. Copy interactive module files ---
echo -e "${YELLOW}[4/7] Copiando módulos interactivos...${NC}"

# docker_manager.py
cp docker_manager.py "${APP_DIR}/app/docker_manager.py" 2>/dev/null || true

# terminal_handler.py
cp terminal_handler.py "${APP_DIR}/app/terminal_handler.py" 2>/dev/null || true

# interactive blueprint
mkdir -p "${APP_DIR}/app/interactive"
cp interactive/__init__.py "${APP_DIR}/app/interactive/" 2>/dev/null || true
cp interactive/routes.py "${APP_DIR}/app/interactive/" 2>/dev/null || true

# terminal template
mkdir -p "${APP_DIR}/app/templates/interactive"
cp templates/interactive/terminal.html "${APP_DIR}/app/templates/interactive/" 2>/dev/null || true

echo -e "${GREEN}[+] Módulos copiados.${NC}"

# --- 5. Patch app/__init__.py ---
echo -e "${YELLOW}[5/7] Parcheando app/__init__.py...${NC}"

python3 << 'PYEOF'
init_file = "app/__init__.py"

with open(init_file, 'r') as f:
    content = f.read()

# Add flask_socketio import
if 'flask_socketio' not in content:
    content = content.replace(
        'from flask_migrate import Migrate',
        'from flask_migrate import Migrate\nfrom flask_socketio import SocketIO'
    )

# Add socketio initialization
if 'socketio = SocketIO()' not in content:
    content = content.replace(
        'migrate = Migrate()',
        'migrate = Migrate()\nsocketio = SocketIO()'
    )

# Add socketio.init_app
if 'socketio.init_app' not in content:
    content = content.replace(
        '    migrate.init_app(app, db)',
        '    migrate.init_app(app, db)\n    socketio.init_app(app, cors_allowed_origins="*", async_mode="eventlet")'
    )

# Add interactive blueprint registration
if 'interactive' not in content:
    content = content.replace(
        "    from app.admin import bp as admin_bp\n    app.register_blueprint(admin_bp, url_prefix='/admin')",
        "    from app.admin import bp as admin_bp\n    app.register_blueprint(admin_bp, url_prefix='/admin')\n\n    from app.interactive import bp as interactive_bp\n    app.register_blueprint(interactive_bp, url_prefix='/interactive')"
    )

# Add terminal events and cleanup thread
if 'terminal_handler' not in content:
    content = content.replace(
        '    return app',
        '    # Register WebSocket terminal events\n    from app.terminal_handler import register_terminal_events\n    register_terminal_events(socketio)\n\n    # Start Docker container cleanup thread\n    from app import docker_manager\n    docker_manager.start_cleanup_thread()\n\n    return app'
    )

with open(init_file, 'w') as f:
    f.write(content)

print("[+] app/__init__.py parcheado.")
PYEOF

# --- 6. Patch models.py ---
echo -e "${YELLOW}[6/7] Parcheando models.py...${NC}"

python3 << 'PYEOF'
models_file = "app/models.py"

with open(models_file, 'r') as f:
    content = f.read()

# Add interactive fields to Challenge model if not present
if 'is_interactive' not in content:
    content = content.replace(
        "    # URL for external challenge (e.g., Docker container)\n    challenge_url = db.Column(db.String(512), nullable=True)",
        """    # URL for external challenge (e.g., Docker container)
    challenge_url = db.Column(db.String(512), nullable=True)

    # Interactive challenge (Docker-based)
    is_interactive = db.Column(db.Boolean, default=False)
    docker_image = db.Column(db.String(256), nullable=True)
    container_timeout = db.Column(db.Integer, default=1800)  # seconds
    container_network = db.Column(db.Boolean, default=False)"""
    )
    print("[+] models.py parcheado con campos interactivos.")
else:
    print("[*] models.py ya tiene campos interactivos.")

with open(models_file, 'w') as f:
    f.write(content)
PYEOF

# --- 7. Patch run.py for SocketIO ---
echo -e "${YELLOW}[7/7] Parcheando run.py para SocketIO...${NC}"

cat > "${APP_DIR}/run.py" << 'PYEOF'
from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
PYEOF

echo -e "${GREEN}[+] run.py actualizado.${NC}"

# --- 8. Update systemd service for eventlet ---
echo -e "${YELLOW}[*] Actualizando servicio systemd...${NC}"

# Detect the service name
if systemctl list-units --type=service | grep -q "hackarena"; then
    SERVICE_NAME="hackarena-ctf"
elif systemctl list-units --type=service | grep -q "ctfarena"; then
    SERVICE_NAME="ctfarena"
else
    SERVICE_NAME="hackarena-ctf"
fi

cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=CTFArena Platform
After=network.target mariadb.service docker.service

[Service]
User=root
Group=root
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/venv/bin"
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Note: Changed to root to allow Docker access
# In production, configure Docker socket permissions instead

systemctl daemon-reload
systemctl restart "${SERVICE_NAME}"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ ¡Retos interactivos integrados correctamente!       ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║  Siguiente paso: construir las imágenes de retos         ║${NC}"
echo -e "${GREEN}║  sudo bash build_challenges.sh                           ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║  Luego en el Admin Panel:                                ║${NC}"
echo -e "${GREEN}║  1. Crear/Editar un reto                                 ║${NC}"
echo -e "${GREEN}║  2. Marcar 'Reto Interactivo'                            ║${NC}"
echo -e "${GREEN}║  3. Imagen Docker: ctfarena/privesc-suid                 ║${NC}"
echo -e "${GREEN}║  4. ¡Listo! Los usuarios verán el botón de terminal      ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
