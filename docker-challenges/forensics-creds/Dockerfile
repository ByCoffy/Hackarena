# =============================================================
# CTFArena Challenge: Forense - Credenciales Ocultas
# Dificultad: Fácil (100 pts)
# Flag: FLAG{h1dd3n_cr3d3nt14ls_f0und}
# =============================================================
# Un administrador descuidado dejó credenciales en el historial
# de bash y en archivos de configuración.
# =============================================================

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    bash \
    nano \
    vim-tiny \
    less \
    file \
    grep \
    && rm -rf /var/lib/apt/lists/*

# Create users
RUN useradd -m -s /bin/bash ctfplayer && \
    echo "ctfplayer:ctfplayer" | chpasswd && \
    useradd -m -s /bin/bash sysadmin && \
    echo "sysadmin:Sup3rS3cr3t!" | chpasswd

# Create flag (owned by sysadmin)
RUN echo "FLAG{h1dd3n_cr3d3nt14ls_f0und}" > /home/sysadmin/flag.txt && \
    chmod 600 /home/sysadmin/flag.txt && \
    chown sysadmin:sysadmin /home/sysadmin/flag.txt

# --- VULNERABILITY: Password in bash_history ---
# The sysadmin's .bash_history contains their password
RUN mkdir -p /home/sysadmin && \
    echo 'ls -la\ncd /var/www\nnano config.php\nmysql -u root -p Sup3rS3cr3t!\ncat /etc/passwd\nexit' > /home/sysadmin/.bash_history && \
    chmod 644 /home/sysadmin/.bash_history && \
    chown sysadmin:sysadmin /home/sysadmin/.bash_history

# Also leave a credential in a "backup" config file
RUN mkdir -p /var/backups && \
    echo '[database]\nhost=localhost\nuser=admin\npassword=Sup3rS3cr3t!\ndb=webapp' > /var/backups/old_config.ini && \
    chmod 644 /var/backups/old_config.ini

# Solution: Read /home/sysadmin/.bash_history or /var/backups/old_config.ini
# Then: su sysadmin (password: Sup3rS3cr3t!)
# Then: cat /home/sysadmin/flag.txt

# Hints
RUN echo "PISTA: Los administradores de sistemas a veces olvidan limpiar su rastro." > /home/ctfplayer/README.txt && \
    echo "Investiga los archivos que otros usuarios dejan por el sistema." >> /home/ctfplayer/README.txt && \
    echo "" >> /home/ctfplayer/README.txt && \
    echo "La flag está en el home de otro usuario." >> /home/ctfplayer/README.txt && \
    chown ctfplayer:ctfplayer /home/ctfplayer/README.txt

# MOTD
RUN echo '#!/bin/bash\necho ""\necho "  ╔══════════════════════════════════════════╗"\necho "  ║   CTFArena - Credenciales Ocultas        ║"\necho "  ║   Objetivo: Encontrar la flag             ║"\necho "  ╚══════════════════════════════════════════╝"\necho ""\necho "  Eres: $(whoami)"\necho "  Lee README.txt para empezar."\necho ""' > /etc/profile.d/motd.sh && \
    chmod +x /etc/profile.d/motd.sh

USER ctfplayer
WORKDIR /home/ctfplayer

CMD ["/bin/bash", "-l"]
