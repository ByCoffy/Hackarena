#!/usr/bin/env python3
from app import create_app, db
from app.models import User, Category

app = create_app()

def setup():
    with app.app_context():
        db.create_all()
        print("[+] Tablas creadas.")
        admin = User.query.filter_by(username=app.config['ADMIN_USERNAME']).first()
        if not admin:
            admin = User(username=app.config['ADMIN_USERNAME'], email=app.config['ADMIN_EMAIL'], is_admin=True)
            admin.set_password(app.config['ADMIN_PASSWORD'])
            db.session.add(admin)
            print(f"[+] Admin creado: {app.config['ADMIN_USERNAME']}")
        for cat_data in [
            {'name': 'Web', 'description': 'Vulnerabilidades web', 'icon': 'bi-globe', 'color': '#00b4d8'},
            {'name': 'Crypto', 'description': 'Criptografía', 'icon': 'bi-key', 'color': '#ffd60a'},
            {'name': 'Forensics', 'description': 'Análisis forense', 'icon': 'bi-search', 'color': '#e63946'},
            {'name': 'Reversing', 'description': 'Ingeniería inversa', 'icon': 'bi-cpu', 'color': '#a855f7'},
            {'name': 'Pwn', 'description': 'Explotación de binarios', 'icon': 'bi-terminal', 'color': '#ff6b35'},
            {'name': 'OSINT', 'description': 'Inteligencia de fuentes abiertas', 'icon': 'bi-binoculars', 'color': '#06d6a0'},
            {'name': 'Misc', 'description': 'Retos variados', 'icon': 'bi-puzzle', 'color': '#8ecae6'},
            {'name': 'Steganography', 'description': 'Datos ocultos', 'icon': 'bi-image', 'color': '#c77dff'},
            {'name': 'Networking', 'description': 'Análisis de redes', 'icon': 'bi-diagram-3', 'color': '#48bfe3'},
        ]:
            if not Category.query.filter_by(name=cat_data['name']).first():
                db.session.add(Category(**cat_data))
        db.session.commit()
        print(f"[✓] Listo. Admin: {app.config['ADMIN_USERNAME']} / {app.config['ADMIN_PASSWORD']}")

if __name__ == '__main__':
    setup()
