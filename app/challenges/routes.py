from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.challenges import bp
from app.models import Challenge, Category, Solve, Hint, SubmissionLog
from app import db

@bp.route('/')
def challenge_list():
    categories = Category.query.all()
    cat = request.args.get('category', 'all')
    diff = request.args.get('difficulty', 'all')
    q = Challenge.query.filter_by(is_active=True)
    if cat != 'all': q = q.filter_by(category_id=int(cat))
    if diff != 'all': q = q.filter_by(difficulty=diff)
    return render_template('challenges/list.html', challenges=q.order_by(Challenge.points.asc()).all(),
                         categories=categories, selected_cat=cat, selected_diff=diff)

@bp.route('/<int:challenge_id>')
@login_required
def challenge_detail(challenge_id):
    ch = Challenge.query.get_or_404(challenge_id)
    if not ch.is_active: flash('Reto no disponible.', 'warning'); return redirect(url_for('challenges.challenge_list'))
    active_container = False
    if ch.is_interactive and ch.docker_image:
        from app import docker_manager
        active_container = docker_manager.get_container(current_user.id, ch.id) is not None
    return render_template('challenges/detail.html', challenge=ch, solved=current_user.has_solved(ch),
                         solvers=ch.get_solvers(), first_blood=ch.get_first_blood(),
                         hints=ch.hints.order_by(Hint.order.asc()).all(),
                         unlocked_hint_ids=[h.id for h in current_user.unlocked_hints.all()],
                         active_container=active_container)

@bp.route('/<int:challenge_id>/submit', methods=['POST'])
@login_required
def submit_flag(challenge_id):
    ch = Challenge.query.get_or_404(challenge_id)
    if not ch.is_available(): flash('Reto no disponible.', 'warning'); return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))
    if current_user.has_solved(ch): flash('Ya resuelto.', 'info'); return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))
    flag = request.form.get('flag', '').strip()
    log = SubmissionLog(user_id=current_user.id, challenge_id=ch.id, submitted_flag=flag, is_correct=(flag == ch.flag), ip_address=request.remote_addr)
    db.session.add(log)
    if flag == ch.flag:
        is_first = ch.solve_count() == 0
        db.session.add(Solve(user_id=current_user.id, challenge_id=ch.id, is_first_blood=is_first))
        db.session.commit()
        bonus = current_app.config.get('FIRST_BLOOD_BONUS', 50)
        flash(f'🩸 FIRST BLOOD! +{ch.points}+{bonus} pts' if is_first else f'🚩 ¡Correcto! +{ch.points} pts', 'success')
    else:
        db.session.commit(); flash('❌ Flag incorrecta.', 'danger')
    return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))

@bp.route('/<int:challenge_id>/hint/<int:hint_id>/unlock', methods=['POST'])
@login_required
def unlock_hint(challenge_id, hint_id):
    hint = Hint.query.get_or_404(hint_id)
    if hint.challenge_id != challenge_id: flash('Pista inválida.', 'danger'); return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))
    if hint in current_user.unlocked_hints.all(): flash('Ya desbloqueada.', 'info'); return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))
    current_user.unlocked_hints.append(hint); db.session.commit()
    flash(f'🔓 Pista desbloqueada. -{hint.cost} pts.', 'warning')
    return redirect(url_for('challenges.challenge_detail', challenge_id=challenge_id))
