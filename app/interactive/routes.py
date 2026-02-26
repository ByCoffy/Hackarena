from flask import render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.interactive import bp
from app.models import Challenge
from app import docker_manager


@bp.route('/<int:challenge_id>/start', methods=['POST'])
@login_required
def start_instance(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    if not challenge.is_interactive or not challenge.docker_image:
        flash('Este reto no es interactivo.', 'danger')
        return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))
    if not docker_manager.is_image_available(challenge.docker_image):
        flash('Imagen Docker no disponible. Contacta al administrador.', 'danger')
        return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))

    info = docker_manager.create_container(
        user_id=current_user.id, challenge_id=challenge.id,
        image_name=challenge.docker_image,
        timeout=challenge.container_timeout or 1800,
        network_enabled=challenge.container_network or False
    )
    if info:
        flash(f'🖥️ Instancia iniciada. Tienes {(challenge.container_timeout or 1800) // 60} minutos.', 'success')
    else:
        flash('Error al crear la instancia.', 'danger')
    return redirect(url_for('interactive.terminal', challenge_id=challenge_id))


@bp.route('/<int:challenge_id>/stop', methods=['POST'])
@login_required
def stop_instance(challenge_id):
    docker_manager.stop_container(current_user.id, challenge_id)
    flash('Instancia detenida.', 'info')
    return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))


@bp.route('/<int:challenge_id>/terminal')
@login_required
def terminal(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    info = docker_manager.get_container_info(current_user.id, challenge_id)
    if not info:
        flash('No hay instancia activa. Inicia una primero.', 'warning')
        return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))
    return render_template('interactive/terminal.html', challenge=challenge,
                         container_info=info,
                         time_remaining=docker_manager.get_time_remaining(current_user.id, challenge_id))


@bp.route('/<int:challenge_id>/status')
@login_required
def instance_status(challenge_id):
    info = docker_manager.get_container_info(current_user.id, challenge_id)
    if not info:
        return jsonify({'active': False})
    return jsonify({
        'active': docker_manager.get_container(current_user.id, challenge_id) is not None,
        'time_remaining': docker_manager.get_time_remaining(current_user.id, challenge_id),
    })
