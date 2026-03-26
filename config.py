import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ctf-platform-secret-key-change-in-production'

    # MySQL/MariaDB
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://ctf_user:ctf_password@localhost/ctf_platform'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

    # CTF Settings
    CTF_NAME = os.environ.get('CTF_NAME') or 'HackArena CTF'
    CTF_DESCRIPTION = os.environ.get('CTF_DESCRIPTION') or 'Plataforma de Capture The Flag'
    FIRST_BLOOD_BONUS = int(os.environ.get('FIRST_BLOOD_BONUS', 50))
    MAX_TEAM_SIZE = int(os.environ.get('MAX_TEAM_SIZE', 5))
    FLAG_FORMAT = os.environ.get('FLAG_FORMAT') or 'FLAG{}'

    # File uploads for challenge attachments
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max

    # Admin
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'admin@hackarena.local'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'AdminCTF2025!'
