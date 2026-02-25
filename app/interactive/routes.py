from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.interactive import bp
from app.models import Challenge
from app import docker_manager


@bp.route('/<int:challenge_id>/start', methods=['POST'])
@login_required
def start_instance(challenge_id):
    """Start a Docker container for an interactive challenge."""
    challenge = Challenge.query.get_or_404(challenge_id)

    if not challenge.is_interactive or not challenge.docker_image:
        flash('Este reto no es interactivo.', 'danger')
        return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))

    if not challenge.is_available():
        flash('Este reto no está disponible.', 'warning')
        return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))

    # Check if image exists
    if not docker_manager.is_image_available(challenge.docker_image):
        flash('La imagen Docker del reto no está disponible. Contacta al administrador.', 'danger')
        return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))

    # Determine timeout (default 30 min)
    timeout = challenge.container_timeout or 1800

    # Network access
    network_enabled = challenge.container_network or False

    # Create container
    container_info = docker_manager.create_container(
        user_id=current_user.id,
        challenge_id=challenge.id,
        image_name=challenge.docker_image,
        timeout=timeout,
        network_enabled=network_enabled
    )

    if container_info:
        flash(f'🖥️ Instancia iniciada. Tienes {timeout // 60} minutos.', 'success')
    else:
        flash('Error al crear la instancia. Inténtalo de nuevo.', 'danger')

    return redirect(url_for('interactive.terminal', challenge_id=challenge_id))


@bp.route('/<int:challenge_id>/stop', methods=['POST'])
@login_required
def stop_instance(challenge_id):
    """Stop and remove the user's container."""
    docker_manager.stop_container(current_user.id, challenge_id)
    flash('Instancia detenida.', 'info')
    return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))


@bp.route('/<int:challenge_id>/terminal')
@login_required
def terminal(challenge_id):
    """Render the web terminal page with xterm.js."""
    challenge = Challenge.query.get_or_404(challenge_id)

    container_info = docker_manager.get_container_info(current_user.id, challenge_id)
    if not container_info:
        flash('No hay una instancia activa. Inicia una primero.', 'warning')
        return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))

    time_remaining = docker_manager.get_time_remaining(current_user.id, challenge_id)

    return render_template('interactive/terminal.html',
                         challenge=challenge,
                         container_info=container_info,
                         time_remaining=time_remaining)


@bp.route('/<int:challenge_id>/status')
@login_required
def instance_status(challenge_id):
    """API endpoint to check container status."""
    container_info = docker_manager.get_container_info(current_user.id, challenge_id)

    if not container_info:
        return jsonify({'active': False})

    container = docker_manager.get_container(current_user.id, challenge_id)

    return jsonify({
        'active': container is not None,
        'time_remaining': docker_manager.get_time_remaining(current_user.id, challenge_id),
        'container_id': container_info['container_id'][:12] if container_info else None
    })
