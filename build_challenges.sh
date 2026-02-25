#!/bin/bash
# =============================================================
# Build all CTFArena challenge Docker images
# Uso: sudo bash build_challenges.sh
# =============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CHALLENGES_DIR="${SCRIPT_DIR}/docker-challenges"

echo -e "${GREEN}[CTFArena] Construyendo imágenes de retos Docker...${NC}"
echo ""

# Build each challenge
build_challenge() {
    local dir=$1
    local name=$2
    local challenge_name="ctfarena/${name}"

    if [ -d "${CHALLENGES_DIR}/${dir}" ]; then
        echo -e "${YELLOW}[*] Construyendo: ${challenge_name}${NC}"
        docker build -t "${challenge_name}" "${CHALLENGES_DIR}/${dir}"
        echo -e "${GREEN}[+] ${challenge_name} construida correctamente${NC}"
        echo ""
    else
        echo -e "${RED}[-] Directorio no encontrado: ${dir}${NC}"
    fi
}

# --- Build all challenges ---
build_challenge "privesc-suid"     "privesc-suid"
build_challenge "privesc-cron"     "privesc-cron"
build_challenge "forensics-creds"  "forensics-creds"

# --- Summary ---
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Imágenes construidas:                         ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════╣${NC}"
docker images --filter "reference=ctfarena/*" --format "  {{.Repository}}:{{.Tag}}  ({{.Size}})" | while read line; do
    echo -e "${GREEN}║  ${line}${NC}"
done
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Para añadir un reto interactivo en el panel admin:${NC}"
echo -e "  1. Marca la casilla 'Reto Interactivo'"
echo -e "  2. Imagen Docker: ctfarena/privesc-suid (por ejemplo)"
echo -e "  3. La flag del reto debe coincidir con la del Dockerfile"
echo ""
echo -e "${YELLOW}Para crear tu propio reto:${NC}"
echo -e "  1. Crea un directorio en docker-challenges/tu-reto/"
echo -e "  2. Añade un Dockerfile"
echo -e "  3. Añade la línea 'build_challenge' en este script"
echo -e "  4. Ejecuta: sudo bash build_challenges.sh"
