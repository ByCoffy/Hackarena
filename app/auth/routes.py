from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app.auth import bp
from app.models import User
from app import db
from datetime import datetime, timezone

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')
        errors = []
        if not username or len(username) < 3: errors.append('Username mínimo 3 caracteres.')
        if not email or '@' not in email: errors.append('Email inválido.')
        if len(password) < 8: errors.append('Contraseña mínimo 8 caracteres.')
        if password != password2: errors.append('Las contraseñas no coinciden.')
        if User.query.filter_by(username=username).first(): errors.append('Username en uso.')
        if User.query.filter_by(email=email).first(): errors.append('Email registrado.')
        if errors:
            for e in errors: flash(e, 'danger')
            return render_template('auth/register.html')
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user); db.session.commit()
        flash('¡Registro exitoso! Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        if user is None or not user.check_password(password):
            flash('Usuario o contraseña incorrectos.', 'danger')
            return render_template('auth/login.html')
        if not user.is_active_user:
            flash('Cuenta desactivada.', 'danger')
            return render_template('auth/login.html')
        login_user(user, remember=bool(request.form.get('remember')))
        user.last_seen = datetime.now(timezone.utc); db.session.commit()
        next_page = request.args.get('next')
        return redirect(next_page if next_page and next_page.startswith('/') else url_for('main.index'))
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user(); flash('Sesión cerrada.', 'info'); return redirect(url_for('main.index'))

@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.bio = request.form.get('bio', '').strip()[:500]
        email = request.form.get('email', '').strip().lower()
        if email != current_user.email:
            if User.query.filter_by(email=email).first():
                flash('Email en uso.', 'danger'); return render_template('auth/edit_profile.html')
            current_user.email = email
        pw = request.form.get('new_password', '')
        if pw:
            if len(pw) < 8: flash('Contraseña mínimo 8 caracteres.', 'danger'); return render_template('auth/edit_profile.html')
            current_user.set_password(pw)
        db.session.commit(); flash('Perfil actualizado.', 'success')
        return redirect(url_for('main.profile', username=current_user.username))
    return render_template('auth/edit_profile.html')
