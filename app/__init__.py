from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
import os

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'warning'


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.challenges import bp as challenges_bp
    app.register_blueprint(challenges_bp, url_prefix='/challenges')

    from app.teams import bp as teams_bp
    app.register_blueprint(teams_bp, url_prefix='/teams')

    from app.leaderboard import bp as leaderboard_bp
    app.register_blueprint(leaderboard_bp, url_prefix='/leaderboard')

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Main routes
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Context processor for templates
    @app.context_processor
    def inject_ctf_info():
        return {
            'ctf_name': app.config['CTF_NAME'],
            'ctf_description': app.config['CTF_DESCRIPTION']
        }

    return app


from app import models
