# main.py
# Un nuevo Blueprint para las rutas generales que no son de un módulo específico, como la página de inicio (/) y los cambiadores de tema e idioma

from flask import (
    Blueprint, render_template, redirect, url_for, session, jsonify, current_app
)
from models import db, User # Asegúrate de que User y db estén importados

# Crear el Blueprint principal
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/home')
def home():
    # Renderiza la plantilla 'home.html' directamente
    # Si usas _() para traducción, asegúrate de que esté disponible
    return render_template('home.html')

@main_bp.route('/change_theme/<theme>')
def change_theme(theme):
    """Actualiza el tema en la sesión y en la base de datos si el usuario está logueado."""
    if theme in ['light', 'dark', 'sepia']:
        session['theme'] = theme
        if 'user_id' in session:
            try:
                # current_app debe importarse si se usa fuera de un contexto directo
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
    # Asegúrate de importar 'current_app' si es necesario
    LANGUAGES = current_app.config.get('BABEL_LANGUAGES', ['es', 'en'])
    if lang in LANGUAGES:
        session['lang'] = lang
    return jsonify(success=True)