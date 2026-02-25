#!/usr/bin/env python3
"""
Script de inicialización de la base de datos.
Crea las tablas, el usuario admin y categorías por defecto.

Uso: python setup_db.py
"""

from app import create_app, db
from app.models import User, Category

app = create_app()


def setup():
    with app.app_context():
        # Create all tables
        db.create_all()
        print("[+] Tablas creadas correctamente.")

        # Create admin user if not exists
        admin = User.query.filter_by(username=app.config['ADMIN_USERNAME']).first()
        if not admin:
            admin = User(
                username=app.config['ADMIN_USERNAME'],
                email=app.config['ADMIN_EMAIL'],
                is_admin=True
            )
            admin.set_password(app.config['ADMIN_PASSWORD'])
            db.session.add(admin)
            print(f"[+] Usuario admin creado: {app.config['ADMIN_USERNAME']}")
        else:
            print("[*] Usuario admin ya existe.")

        # Create default categories
        default_categories = [
            {'name': 'Web', 'description': 'Vulnerabilidades y exploits web', 'icon': 'bi-globe', 'color': '#00b4d8'},
            {'name': 'Crypto', 'description': 'Criptografía y descifrado', 'icon': 'bi-key', 'color': '#ffd60a'},
            {'name': 'Forensics', 'description': 'Análisis forense digital', 'icon': 'bi-search', 'color': '#e63946'},
            {'name': 'Reversing', 'description': 'Ingeniería inversa de binarios', 'icon': 'bi-cpu', 'color': '#a855f7'},
            {'name': 'Pwn', 'description': 'Explotación de binarios', 'icon': 'bi-terminal', 'color': '#ff6b35'},
            {'name': 'OSINT', 'description': 'Inteligencia de fuentes abiertas', 'icon': 'bi-binoculars', 'color': '#06d6a0'},
            {'name': 'Misc', 'description': 'Retos variados', 'icon': 'bi-puzzle', 'color': '#8ecae6'},
            {'name': 'Steganography', 'description': 'Datos ocultos en archivos', 'icon': 'bi-image', 'color': '#c77dff'},
            {'name': 'Networking', 'description': 'Análisis de redes y tráfico', 'icon': 'bi-diagram-3', 'color': '#48bfe3'},
        ]

        for cat_data in default_categories:
            existing = Category.query.filter_by(name=cat_data['name']).first()
            if not existing:
                cat = Category(**cat_data)
                db.session.add(cat)
                print(f"[+] Categoría creada: {cat_data['name']}")

        db.session.commit()
        print("\n[✓] Base de datos inicializada correctamente.")
        print(f"[i] Admin: {app.config['ADMIN_USERNAME']} / {app.config['ADMIN_PASSWORD']}")
        print(f"[i] Ejecuta: python run.py")


if __name__ == '__main__':
    setup()
