from flask import Blueprint

bp = Blueprint('interactive', __name__)

from app.interactive import routes
