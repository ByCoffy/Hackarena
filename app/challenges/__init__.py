from flask import Blueprint
bp = Blueprint('challenges', __name__)
from app.challenges import routes
