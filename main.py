# main.py
# Un nuevo Blueprint para las rutas generales que no son de un módulo específico, como la página de inicio (/) y los cambiadores de tema e idioma

from flask import (
    Blueprint, render_template, redirect, url_for, session, jsonify
)
from models import db, User

# Crear el Blueprint principal
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/home')
def home():
    # Redirige a la página 'Acerca de nosotros' como la nueva página de inicio
    return redirect(url_for('aboutus.ver_aboutus'))

@main_bp.route('/change_theme/<theme>')
def change_theme(theme):
    """Actualiza el tema en la sesión y en la base de datos si el usuario está logueado."""
    if theme in ['light', 'dark', 'sepia']:
        session['theme'] = theme
        if 'user_id' in session:
            try:
                user = User.query.get(session['user_id'])
                if user:
                    user.theme = theme
                    db.session.commit()
            except Exception as e:
                # No es crítico, solo loggear
                current_app.logger.warn(f"No se pudo guardar el tema para user_id {session['user_id']}: {e}")
    # El JS ahora maneja la recarga, solo devolvemos éxito
    return jsonify(success=True)


@main_bp.route('/change_language/<lang>')
def change_language(lang):
    """Actualiza el idioma en la sesión."""
    LANGUAGES = ['es', 'en'] # Mover a config si es necesario
    if lang in LANGUAGES:
        session['lang'] = lang
    # El JS ahora maneja la recarga, solo devolvemos éxito
    return jsonify(success=True)
