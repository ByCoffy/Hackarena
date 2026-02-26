# =============================================================
# CTFArena Challenge: Escalada de Privilegios - SUID
# Dificultad: Fácil (100 pts)
# Flag: FLAG{su1d_pr1v3sc_m4st3r}
# =============================================================
# El usuario "ctfplayer" debe escalar privilegios a root
# explotando un binario con SUID mal configurado.
# =============================================================

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    bash \
    coreutils \
    findutils \
    nano \
    vim-tiny \
    less \
    && rm -rf /var/lib/apt/lists/*

# Create the CTF player user
RUN useradd -m -s /bin/bash ctfplayer && \
    echo "ctfplayer:ctfplayer" | chpasswd

# Create root flag
RUN echo "FLAG{su1d_pr1v3sc_m4st3r}" > /root/flag.txt && \
    chmod 600 /root/flag.txt

# --- VULNERABILITY: SUID on find ---
# The 'find' command has SUID set, allowing privilege escalation
# Solution: find / -exec /bin/bash -p \; 2>/dev/null
# Or: find . -exec /bin/sh -p \; -quit
RUN chmod u+s /usr/bin/find

# Create a hint file
RUN echo "PISTA: A veces los binarios tienen más permisos de los que deberían..." > /home/ctfplayer/README.txt && \
    echo "Busca binarios con permisos especiales en el sistema." >> /home/ctfplayer/README.txt && \
    echo "" >> /home/ctfplayer/README.txt && \
    echo "La flag está en /root/flag.txt" >> /home/ctfplayer/README.txt && \
    chown ctfplayer:ctfplayer /home/ctfplayer/README.txt

# Add some fake users/services to make it realistic
RUN useradd -m -s /bin/bash webadmin && \
    echo "webadmin:$(openssl rand -base64 32)" | chpasswd

# Add a decoy flag
RUN echo "Esto no es la flag... sigue buscando ;)" > /home/webadmin/not_the_flag.txt

# MOTD banner
RUN echo '#!/bin/bash\necho ""\necho "  ╔══════════════════════════════════════╗"\necho "  ║     CTFArena - Escalada SUID         ║"\necho "  ║     Objetivo: Leer /root/flag.txt    ║"\necho "  ╚══════════════════════════════════════╝"\necho ""\necho "  Eres: $(whoami)"\necho "  Lee README.txt para empezar."\necho ""' > /etc/profile.d/motd.sh && \
    chmod +x /etc/profile.d/motd.sh

USER ctfplayer
WORKDIR /home/ctfplayer

CMD ["/bin/bash", "-l"]
