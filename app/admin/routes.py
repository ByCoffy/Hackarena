import os
from functools import wraps
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.admin import bp
from app.models import Challenge, Category, User, Team, Solve, Hint, SubmissionLog
from app import db, docker_manager
from datetime import datetime, timezone


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Acceso denegado.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/')
@admin_required
def dashboard():
    stats = {
        'users': User.query.count(), 'teams': Team.query.count(),
        'challenges': Challenge.query.count(), 'solves': Solve.query.count(),
        'submissions': SubmissionLog.query.count(),
        'active_containers': docker_manager.get_active_container_count(),
    }
    recent_submissions = SubmissionLog.query.order_by(SubmissionLog.submitted_at.desc()).limit(20).all()
    return render_template('admin/dashboard.html', stats=stats, recent_submissions=recent_submissions)


@bp.route('/categories')
@admin_required
def categories():
    return render_template('admin/categories.html', categories=Category.query.all())


@bp.route('/categories/create', methods=['GET', 'POST'])
@admin_required
def create_category():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('El nombre es obligatorio.', 'danger')
            return render_template('admin/category_form.html', category=None)
        if Category.query.filter_by(name=name).first():
            flash('Ya existe.', 'danger')
            return render_template('admin/category_form.html', category=None)
        cat = Category(name=name, description=request.form.get('description', '').strip(),
                      icon=request.form.get('icon', 'bi-puzzle').strip(),
                      color=request.form.get('color', '#00ff88').strip())
        db.session.add(cat)
        db.session.commit()
        flash(f'Categoría "{name}" creada.', 'success')
        return redirect(url_for('admin.categories'))
    return render_template('admin/category_form.html', category=None)


@bp.route('/categories/<int:cat_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    if request.method == 'POST':
        cat.name = request.form.get('name', '').strip()
        cat.description = request.form.get('description', '').strip()
        cat.icon = request.form.get('icon', 'bi-puzzle').strip()
        cat.color = request.form.get('color', '#00ff88').strip()
        db.session.commit()
        flash('Categoría actualizada.', 'success')
        return redirect(url_for('admin.categories'))
    return render_template('admin/category_form.html', category=cat)


@bp.route('/categories/<int:cat_id>/delete', methods=['POST'])
@admin_required
def delete_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    if cat.challenges.count() > 0:
        flash('No se puede eliminar: hay retos asignados.', 'danger')
        return redirect(url_for('admin.categories'))
    db.session.delete(cat)
    db.session.commit()
    flash('Categoría eliminada.', 'success')
    return redirect(url_for('admin.categories'))


@bp.route('/challenges')
@admin_required
def challenges():
    return render_template('admin/challenges.html',
                         challenges=Challenge.query.order_by(Challenge.created_at.desc()).all())


@bp.route('/challenges/create', methods=['GET', 'POST'])
@admin_required
def create_challenge():
    categories = Category.query.all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        flag = request.form.get('flag', '').strip()
        points = int(request.form.get('points', 100))
        difficulty = request.form.get('difficulty', 'medium')
        category_id = int(request.form.get('category_id', 0))
        author = request.form.get('author', 'Admin').strip()
        challenge_url = request.form.get('challenge_url', '').strip()
        is_active = 'is_active' in request.form

        # Interactive Docker fields
        is_interactive = 'is_interactive' in request.form
        docker_image = request.form.get('docker_image', '').strip()
        container_timeout = int(request.form.get('container_timeout', 1800))
        container_network = 'container_network' in request.form

        starts_at_str = request.form.get('starts_at', '').strip()
        ends_at_str = request.form.get('ends_at', '').strip()
        starts_at = datetime.fromisoformat(starts_at_str).replace(tzinfo=timezone.utc) if starts_at_str else None
        ends_at = datetime.fromisoformat(ends_at_str).replace(tzinfo=timezone.utc) if ends_at_str else None

        if not all([title, description, flag, category_id]):
            flash('Título, descripción, flag y categoría son obligatorios.', 'danger')
            return render_template('admin/challenge_form.html', challenge=None, categories=categories)

        challenge = Challenge(
            title=title, description=description, flag=flag, points=points,
            difficulty=difficulty, category_id=category_id, author=author,
            challenge_url=challenge_url or None, is_active=is_active,
            starts_at=starts_at, ends_at=ends_at,
            is_interactive=is_interactive, docker_image=docker_image or None,
            container_timeout=container_timeout, container_network=container_network,
        )

        file = request.files.get('attachment')
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            challenge.attachment_filename = filename

        db.session.add(challenge)
        db.session.flush()

        for i, (content, cost) in enumerate(zip(
            request.form.getlist('hint_content[]'), request.form.getlist('hint_cost[]'))):
            if content.strip():
                db.session.add(Hint(challenge_id=challenge.id, content=content.strip(),
                                   cost=int(cost) if cost else 25, order=i))

        db.session.commit()
        flash(f'Reto "{title}" creado.', 'success')
        return redirect(url_for('admin.challenges'))
    return render_template('admin/challenge_form.html', challenge=None, categories=categories)


@bp.route('/challenges/<int:chall_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_challenge(chall_id):
    challenge = Challenge.query.get_or_404(chall_id)
    categories = Category.query.all()
    if request.method == 'POST':
        challenge.title = request.form.get('title', '').strip()
        challenge.description = request.form.get('description', '').strip()
        challenge.flag = request.form.get('flag', '').strip()
        challenge.points = int(request.form.get('points', 100))
        challenge.difficulty = request.form.get('difficulty', 'medium')
        challenge.category_id = int(request.form.get('category_id', 0))
        challenge.author = request.form.get('author', 'Admin').strip()
        challenge.challenge_url = request.form.get('challenge_url', '').strip() or None
        challenge.is_active = 'is_active' in request.form

        # Interactive Docker fields
        challenge.is_interactive = 'is_interactive' in request.form
        challenge.docker_image = request.form.get('docker_image', '').strip() or None
        challenge.container_timeout = int(request.form.get('container_timeout', 1800))
        challenge.container_network = 'container_network' in request.form

        starts_at_str = request.form.get('starts_at', '').strip()
        ends_at_str = request.form.get('ends_at', '').strip()
        challenge.starts_at = datetime.fromisoformat(starts_at_str).replace(tzinfo=timezone.utc) if starts_at_str else None
        challenge.ends_at = datetime.fromisoformat(ends_at_str).replace(tzinfo=timezone.utc) if ends_at_str else None

        file = request.files.get('attachment')
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            challenge.attachment_filename = filename

        Hint.query.filter_by(challenge_id=challenge.id).delete()
        for i, (content, cost) in enumerate(zip(
            request.form.getlist('hint_content[]'), request.form.getlist('hint_cost[]'))):
            if content.strip():
                db.session.add(Hint(challenge_id=challenge.id, content=content.strip(),
                                   cost=int(cost) if cost else 25, order=i))

        db.session.commit()
        flash('Reto actualizado.', 'success')
        return redirect(url_for('admin.challenges'))
    hints = challenge.hints.order_by(Hint.order.asc()).all()
    return render_template('admin/challenge_form.html', challenge=challenge, categories=categories, hints=hints)


@bp.route('/challenges/<int:chall_id>/delete', methods=['POST'])
@admin_required
def delete_challenge(chall_id):
    Solve.query.filter_by(challenge_id=chall_id).delete()
    SubmissionLog.query.filter_by(challenge_id=chall_id).delete()
    Hint.query.filter_by(challenge_id=chall_id).delete()
    db.session.delete(Challenge.query.get_or_404(chall_id))
    db.session.commit()
    flash('Reto eliminado.', 'success')
    return redirect(url_for('admin.challenges'))


@bp.route('/challenges/<int:chall_id>/toggle', methods=['POST'])
@admin_required
def toggle_challenge(chall_id):
    ch = Challenge.query.get_or_404(chall_id)
    ch.is_active = not ch.is_active
    db.session.commit()
    flash(f'Reto "{ch.title}" {"activado" if ch.is_active else "desactivado"}.', 'info')
    return redirect(url_for('admin.challenges'))


@bp.route('/users')
@admin_required
def users():
    return render_template('admin/users.html', users=User.query.order_by(User.created_at.desc()).all())


@bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('No puedes desactivar tu propia cuenta.', 'danger')
        return redirect(url_for('admin.users'))
    user.is_active_user = not user.is_active_user
    db.session.commit()
    return redirect(url_for('admin.users'))


@bp.route('/users/<int:user_id>/make-admin', methods=['POST'])
@admin_required
def make_admin(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    return redirect(url_for('admin.users'))


@bp.route('/logs')
@admin_required
def submission_logs():
    page = request.args.get('page', 1, type=int)
    logs = SubmissionLog.query.order_by(SubmissionLog.submitted_at.desc()).paginate(page=page, per_page=50)
    return render_template('admin/logs.html', logs=logs)
