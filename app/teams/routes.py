import secrets
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.teams import bp
from app.models import Team, User
from app import db


@bp.route('/')
def team_list():
    teams = Team.query.all()
    teams_with_scores = sorted([(t, t.get_score()) for t in teams], key=lambda x: x[1], reverse=True)
    return render_template('teams/list.html', teams_with_scores=teams_with_scores)


@bp.route('/<int:team_id>')
def team_detail(team_id):
    team = Team.query.get_or_404(team_id)
    return render_template('teams/detail.html', team=team, members=team.members.all(), score=team.get_score())


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_team():
    if current_user.team_id:
        flash('Ya perteneces a un equipo.', 'warning')
        return redirect(url_for('teams.team_list'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()[:500]
        if not name or len(name) < 3:
            flash('El nombre debe tener al menos 3 caracteres.', 'danger')
            return render_template('teams/create.html')
        if Team.query.filter_by(name=name).first():
            flash('Este nombre ya existe.', 'danger')
            return render_template('teams/create.html')
        team = Team(name=name, description=description, invite_code=secrets.token_hex(8), owner_id=current_user.id)
        db.session.add(team)
        db.session.flush()
        current_user.team_id = team.id
        db.session.commit()
        flash(f'¡Equipo "{name}" creado! Código: {team.invite_code}', 'success')
        return redirect(url_for('teams.team_detail', team_id=team.id))
    return render_template('teams/create.html')


@bp.route('/join', methods=['GET', 'POST'])
@login_required
def join_team():
    if current_user.team_id:
        flash('Ya perteneces a un equipo.', 'warning')
        return redirect(url_for('teams.team_list'))
    if request.method == 'POST':
        invite_code = request.form.get('invite_code', '').strip()
        team = Team.query.filter_by(invite_code=invite_code).first()
        if not team:
            flash('Código inválido.', 'danger')
            return render_template('teams/join.html')
        if team.member_count() >= current_app.config.get('MAX_TEAM_SIZE', 5):
            flash('Equipo lleno.', 'danger')
            return render_template('teams/join.html')
        current_user.team_id = team.id
        db.session.commit()
        flash(f'¡Te has unido a "{team.name}"!', 'success')
        return redirect(url_for('teams.team_detail', team_id=team.id))
    return render_template('teams/join.html')


@bp.route('/leave', methods=['POST'])
@login_required
def leave_team():
    if not current_user.team_id:
        return redirect(url_for('teams.team_list'))
    team = Team.query.get(current_user.team_id)
    if team and team.owner_id == current_user.id and team.member_count() <= 1:
        current_user.team_id = None
        db.session.delete(team)
    else:
        if team and team.owner_id == current_user.id:
            new_owner = team.members.filter(User.id != current_user.id).first()
            if new_owner:
                team.owner_id = new_owner.id
        current_user.team_id = None
    db.session.commit()
    flash('Has abandonado el equipo.', 'info')
    return redirect(url_for('teams.team_list'))
