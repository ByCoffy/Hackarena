# 🚩 CTFArena

**Plataforma web de Capture The Flag** con retos interactivos Docker.

🔗 [https://github.com/ByCoffy/CTFArena](https://github.com/ByCoffy/CTFArena)

## Características

- Registro/login de usuarios con perfiles
- Retos por categorías (Web, Crypto, Forensics, Reversing, Pwn, OSINT, Stego, Networking, Misc)
- 🩸 First Blood con bonus de puntos
- Equipos con código de invitación
- Pistas con penalización de puntos
- Challenges con tiempo límite
- 🖥️ **Retos interactivos con terminal Docker en el navegador**
- Leaderboard individual y por equipos
- Panel admin completo
- Tema oscuro estilo hacker

## Instalación (Ubuntu Server)

```bash
git clone https://github.com/ByCoffy/CTFArena.git
cd CTFArena
sudo bash install.sh
sudo bash build_challenges.sh
```

## Retos Docker incluidos

| Reto | Dificultad | Imagen | Flag |
|---|---|---|---|
| Escalada SUID | Fácil | `ctfarena/privesc-suid` | `FLAG{su1d_pr1v3sc_m4st3r}` |
| Cron Job Hijack | Media | `ctfarena/privesc-cron` | `FLAG{cr0n_j0b_h1j4ck3d}` |
| Credenciales Ocultas | Fácil | `ctfarena/forensics-creds` | `FLAG{h1dd3n_cr3d3nt14ls_f0und}` |

## Stack

Python Flask + MySQL/MariaDB + Docker + SocketIO + xterm.js + Bootstrap 5

## Autor

TFM de Hacking Ético — Campus Cámara Sevilla © 2025
