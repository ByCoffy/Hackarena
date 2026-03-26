from flask import render_template, request
from app.leaderboard import bp
from app.models import User, Team


@bp.route('/')
def scoreboard():
    view = request.args.get('view', 'individual')

    if view == 'teams':
        teams = Team.query.all()
        team_scores = []
        for team in teams:
            score = team.get_score()
            solve_count = team.get_solve_count()
            team_scores.append({
                'team': team,
                'score': score,
                'solves': solve_count,
                'members': team.member_count()
            })
        team_scores.sort(key=lambda x: x['score'], reverse=True)
        return render_template('leaderboard/scoreboard.html',
                             view=view, team_scores=team_scores)
    else:
        users = User.query.filter_by(is_admin=False).all()
        user_scores = []
        for user in users:
            score = user.get_score()
            solve_count = user.get_solve_count()
            # Get latest solve time for tiebreaker
            latest_solve = user.solves.order_by(
                db.text('solved_at DESC')).first()
            user_scores.append({
                'user': user,
                'score': score,
                'solves': solve_count,
                'latest_solve': latest_solve.solved_at if latest_solve else None,
                'team': user.team_ref
            })
        # Sort: highest score first, then earliest latest_solve for tiebreak
        user_scores.sort(
            key=lambda x: (-x['score'],
                          x['latest_solve'] or __import__('datetime').datetime.max))
        return render_template('leaderboard/scoreboard.html',
                             view=view, user_scores=user_scores)


# Need to import db for the text() function
from app import db
