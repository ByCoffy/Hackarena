"""
=============================================================
PARCHES PYTHON - Instrucciones de integración manual
=============================================================

Estos son los cambios necesarios en los archivos Python existentes.
El script integrate_interactive.sh aplica la mayoría automáticamente,
pero estos cambios en las rutas deben hacerse manualmente o copiando
este archivo.
=============================================================
"""

# =============================================================
# PARCHE 1: app/admin/routes.py
# En la función create_challenge() y edit_challenge()
# Añadir después de las líneas de challenge_url:
# =============================================================

"""
# --- En create_challenge(), después de: challenge_url = request.form.get(...) ---

        is_interactive = 'is_interactive' in request.form
        docker_image = request.form.get('docker_image', '').strip()
        container_timeout = int(request.form.get('container_timeout', 1800))
        container_network = 'container_network' in request.form

# --- En el Challenge() constructor, añadir: ---

            is_interactive=is_interactive,
            docker_image=docker_image or None,
            container_timeout=container_timeout,
            container_network=container_network,

# --- En edit_challenge(), después de: challenge.challenge_url = ... ---

        challenge.is_interactive = 'is_interactive' in request.form
        challenge.docker_image = request.form.get('docker_image', '').strip() or None
        challenge.container_timeout = int(request.form.get('container_timeout', 1800))
        challenge.container_network = 'container_network' in request.form
"""


# =============================================================
# PARCHE 2: app/challenges/routes.py
# En la función challenge_detail(), añadir la variable active_container
# =============================================================

"""
# --- Añadir al final de challenge_detail(), antes del return ---

    # Check for active Docker container
    active_container = False
    if challenge.is_interactive and challenge.docker_image:
        from app import docker_manager
        active_container = docker_manager.get_container(current_user.id, challenge.id) is not None

# --- En el render_template, añadir: ---

    return render_template('challenges/detail.html',
                         ...
                         active_container=active_container)
"""


# =============================================================
# PARCHE 3: app/admin/routes.py (dashboard)
# Añadir estadísticas de contenedores Docker activos
# =============================================================

"""
# --- En dashboard(), añadir al dict stats: ---

    from app import docker_manager
    stats['active_containers'] = docker_manager.get_active_container_count()
"""
