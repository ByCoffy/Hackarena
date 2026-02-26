from flask import Blueprint, render_template
from flask_login import current_user
from app.models import Challenge, Category, User, Team, Solve
from app import db
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    stats = {'total_challenges': Challenge.query.filter_by(is_active=True).count(),
             'total_users': User.query.count(), 'total_teams': Team.query.count(), 'total_solves': Solve.query.count()}
    categories = Category.query.all()
    recent_solves = Solve.query.order_by(Solve.solved_at.desc()).limit(10).all()
    return render_template('index.html', stats=stats, categories=categories, recent_solves=recent_solves)

@main_bp.route('/profile/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    solves = user.solves.order_by(Solve.solved_at.desc()).all()
    score = user.get_score()
    all_users = User.query.filter_by(is_admin=False).all()
    ranked = sorted(all_users, key=lambda u: u.get_score(), reverse=True)
    rank = next((i+1 for i, u in enumerate(ranked) if u.id == user.id), 0)
    return render_template('profile.html', user=user, solves=solves, score=score, rank=rank, total_users=len(ranked))
