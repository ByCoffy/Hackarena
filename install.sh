#!/bin/bash
set -e
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${GREEN}"
echo "  ╔══════════════════════════════════════════╗"
echo "  ║       CTFArena - Instalación Completa     ║"
echo "  ╚══════════════════════════════════════════╝"
echo -e "${NC}"

if [ "$EUID" -ne 0 ]; then echo "[!] Ejecuta como root: sudo bash install.sh"; exit 1; fi

DB_NAME="ctf_platform"
DB_USER="ctf_user"
DB_PASS="ctf_password_$(openssl rand -hex 8)"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
ADMIN_PASS="Admin_$(openssl rand -hex 6)!"
APP_DIR="/opt/ctfarena"

echo -e "${YELLOW}[1/6] Actualizando sistema e instalando dependencias...${NC}"
apt update && apt install -y python3 python3-pip python3-venv mariadb-server mariadb-client nginx git

echo -e "${YELLOW}[2/6] Instalando Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker && systemctl start docker
fi

echo -e "${YELLOW}[3/6] Configurando MariaDB...${NC}"
systemctl start mariadb && systemctl enable mariadb
mysql -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';"
mysql -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost'; FLUSH PRIVILEGES;"

echo -e "${YELLOW}[4/6] Configurando aplicación...${NC}"
mkdir -p ${APP_DIR}
cp -r . ${APP_DIR}/
cd ${APP_DIR}

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cat > .env << EOF
SECRET_KEY=${SECRET_KEY}
DATABASE_URL=mysql+pymysql://${DB_USER}:${DB_PASS}@localhost/${DB_NAME}
CTF_NAME=CTFArena
CTF_DESCRIPTION=Plataforma de Capture The Flag - Hacking Ético
FIRST_BLOOD_BONUS=50
MAX_TEAM_SIZE=5
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@ctfarena.local
ADMIN_PASSWORD=${ADMIN_PASS}
EOF

pip install python-dotenv
# Add dotenv loading to config
sed -i '1s/^/from dotenv import load_dotenv\nload_dotenv()\n\n/' config.py

python setup_db.py
mkdir -p app/static/uploads
chown -R root:root ${APP_DIR}

echo -e "${YELLOW}[5/6] Configurando servicio systemd...${NC}"
cat > /etc/systemd/system/ctfarena.service << EOF
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

systemctl daemon-reload
systemctl enable ctfarena
systemctl start ctfarena

echo -e "${YELLOW}[6/6] Configurando Nginx con WebSocket...${NC}"
cat > /etc/nginx/sites-available/ctfarena << 'NGEOF'
server {
    listen 80;
    server_name _;
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    location /static {
        alias /opt/ctfarena/app/static;
        expires 1d;
    }
}
NGEOF

ln -sf /etc/nginx/sites-available/ctfarena /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ ¡CTFArena instalado correctamente!               ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  URL:    http://$(hostname -I | awk '{print $1}')${NC}"
echo -e "${GREEN}║  Admin:  admin / ${ADMIN_PASS}${NC}"
echo -e "${GREEN}║  DB:     ${DB_USER} / ${DB_PASS}${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Siguiente: sudo bash build_challenges.sh            ║${NC}"
echo -e "${GREEN}║  Servicio:  systemctl status ctfarena                ║${NC}"
echo -e "${GREEN}║  Logs:      journalctl -u ctfarena -f                ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
