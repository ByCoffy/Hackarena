# =============================================================
# CTFArena Challenge: Escalada de Privilegios - Cron Job
# Dificultad: Media (200 pts)
# Flag: FLAG{cr0n_j0b_h1j4ck3d}
# =============================================================
# Un script de backup se ejecuta como root cada minuto.
# El usuario tiene permisos de escritura sobre el script.
# =============================================================

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    bash \
    coreutils \
    cron \
    nano \
    vim-tiny \
    less \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create CTF player
RUN useradd -m -s /bin/bash ctfplayer && \
    echo "ctfplayer:ctfplayer" | chpasswd

# Create the flag (only readable by root)
RUN echo "FLAG{cr0n_j0b_h1j4ck3d}" > /root/flag.txt && \
    chmod 600 /root/flag.txt

# --- VULNERABILITY: Writable cron script ---
# A backup script runs as root every minute, but ctfplayer can edit it
RUN mkdir -p /opt/scripts && \
    echo '#!/bin/bash\n# Backup script - runs every minute\ntar czf /tmp/backup.tar.gz /var/log 2>/dev/null' > /opt/scripts/backup.sh && \
    chmod 777 /opt/scripts/backup.sh

# Solution: echo "cp /root/flag.txt /tmp/flag.txt && chmod 644 /tmp/flag.txt" >> /opt/scripts/backup.sh
# Then wait ~1 minute and read /tmp/flag.txt

# Setup cron job
RUN echo "* * * * * root /opt/scripts/backup.sh" > /etc/cron.d/backup && \
    chmod 644 /etc/cron.d/backup

# Hint files
RUN echo "PISTA: Hay un servicio automatizado en el sistema que ejecuta tareas periódicas." > /home/ctfplayer/README.txt && \
    echo "Investiga qué se ejecuta y con qué permisos." >> /home/ctfplayer/README.txt && \
    echo "" >> /home/ctfplayer/README.txt && \
    echo "La flag está en /root/flag.txt (solo root puede leerla)" >> /home/ctfplayer/README.txt && \
    chown ctfplayer:ctfplayer /home/ctfplayer/README.txt

# MOTD
RUN echo '#!/bin/bash\necho ""\necho "  ╔══════════════════════════════════════╗"\necho "  ║   CTFArena - Cron Job Hijacking      ║"\necho "  ║   Objetivo: Leer /root/flag.txt      ║"\necho "  ╚══════════════════════════════════════╝"\necho ""\necho "  Eres: $(whoami)"\necho "  Lee README.txt para empezar."\necho ""' > /etc/profile.d/motd.sh && \
    chmod +x /etc/profile.d/motd.sh

# Start cron + bash
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
