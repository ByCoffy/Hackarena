from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
from config import Config
import os

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
socketio = SocketIO()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Inicia sesión para acceder.'
login_manager.login_message_category = 'warning'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="eventlet")
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
    from app.interactive import bp as interactive_bp
    app.register_blueprint(interactive_bp, url_prefix='/interactive')
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    from app.terminal_handler import register_terminal_events
    register_terminal_events(socketio)
    from app import docker_manager
    docker_manager.start_cleanup_thread()
    @app.context_processor
    def inject_ctf_info():
        return {'ctf_name': app.config['CTF_NAME'], 'ctf_description': app.config['CTF_DESCRIPTION']}
    return app
from app import models
