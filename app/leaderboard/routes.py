from flask import render_template, request
from app.leaderboard import bp
from app.models import User, Team
from app import db
from datetime import datetime


@bp.route('/')
def scoreboard():
    view = request.args.get('view', 'individual')
    if view == 'teams':
        teams = Team.query.all()
        team_scores = sorted([{'team': t, 'score': t.get_score(), 'solves': t.get_solve_count(),
                               'members': t.member_count()} for t in teams],
                            key=lambda x: x['score'], reverse=True)
        return render_template('leaderboard/scoreboard.html', view=view, team_scores=team_scores)
    else:
        users = User.query.filter_by(is_admin=False).all()
        user_scores = []
        for user in users:
            latest = user.solves.order_by(db.text('solved_at DESC')).first()
            user_scores.append({'user': user, 'score': user.get_score(), 'solves': user.get_solve_count(),
                               'latest_solve': latest.solved_at if latest else None, 'team': user.team_ref})
        user_scores.sort(key=lambda x: (-x['score'], x['latest_solve'] or datetime.max))
        return render_template('leaderboard/scoreboard.html', view=view, user_scores=user_scores)
