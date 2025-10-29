import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, session, request, redirect, url_for, flash, jsonify
from flask_cors import CORS
from flask_mail import Mail
from flask_babel import Babel
import click
from flask.cli import with_appcontext

# --- CONFIGURACIÓN E IMPORTACIONES DE LA APP ---
from config import Config
from models import db, bcrypt, migrate, User, AboutUs
from auth_setup import oauth_bp, init_oauth

# --- INICIALIZACIÓN DE EXTENSIONES (SIN APP) ---
# Estas se inicializan globalmente para ser importadas por otros módulos
mail = Mail()
babel = Babel()

# --- SELECTOR DE IDIOMA PARA BABEL ---
LANGUAGES = ['es', 'en']
def get_locale():
    # Intenta obtener el idioma de la sesión
    lang = session.get('lang')
    if lang in LANGUAGES:
        return lang
    # Si no, usa el del navegador
    return request.accept_languages.best_match(LANGUAGES)

# ======================================================================
# --- APP FACTORY ---
# ======================================================================
def create_app(config_class=Config):
    """
    Crea y configura la instancia de la aplicación Flask.
    """
    app = Flask(__name__, instance_relative_config=True)
    CORS(app)

    # --- 1. Cargar Configuración ---
    app.config.from_object(config_class)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

    # --- 2. Asegurar Carpetas de Instancia y Subidas ---
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)
    
    # Usar la variable UPLOAD_FOLDER única de config.py
    base_upload_folder = app.config.get('UPLOAD_FOLDER')
    if not base_upload_folder:
        # Fallback si UPLOAD_FOLDER no está en config.py
        base_upload_folder = os.path.join(app.static_folder, 'uploads')
        app.config['UPLOAD_FOLDER'] = base_upload_folder
        
    os.makedirs(base_upload_folder, exist_ok=True)
    
    # Crear subcarpetas (opcional, 'save_upload' en app_utils también las crea)
    subfolders = [
        'avatars', 'projects', 'notes', 'caminatas', 'pagos', 'calendar',
        'songs', 'playlists', 'instructions', 'maps', 'covers', 'aboutus', 'files'
    ]
    for sub in subfolders:
        os.makedirs(os.path.join(base_upload_folder, sub), exist_ok=True)


    # --- 3. Inicializar Extensiones con la App ---
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    init_oauth(app) # Inicializar OAuth

    # --- 4. Registrar Blueprints ---
    # (Importar aquí para evitar importaciones circulares)
    
    # ¡¡ESTAS LÍNEAS SON LA CLAVE!!
    from main import main_bp
    from auth import auth_bp
    
    from contactos import contactos_bp
    from perfil import perfil_bp
    from aboutus import aboutus_bp
    from version import version_bp, Version
    from btns import btns_bp

    # ¡¡Y ESTAS LÍNEAS TAMBIÉN!!
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp) 
    
    app.register_blueprint(contactos_bp)
    app.register_blueprint(perfil_bp, url_prefix='/perfil')
    app.register_blueprint(aboutus_bp, url_prefix='/aboutus')
    app.register_blueprint(version_bp, url_prefix='/version')
    app.register_blueprint(btns_bp)
    app.register_blueprint(oauth_bp)

    # --- 5. Registrar Filtros de Jinja, Handlers de Error, etc. ---
    
    # Filtros de Jinja2
    @app.template_filter('format_currency')
    def format_currency_filter(value):
        if value is None: return "N/A"
        try: return f"${value:,.2f}"
        except (ValueError, TypeError): return str(value)

    @app.template_filter('from_json')
    def from_json_filter(value):
        if value:
            try: return json.loads(value)
            except json.JSONDecodeError: return []
        return []

    @app.template_filter('to_datetime')
    def to_datetime_filter(value):
        if isinstance(value, datetime): return value
        if isinstance(value, str):
            for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                try: return datetime.strptime(value, fmt)
                except ValueError: continue
            return None
        return value

    # Procesador de Contexto
    @app.context_processor
    def inject_latest_version():
        try:
            latest_version = Version.query.order_by(Version.fecha_creacion.desc()).first()
            if latest_version:
                return {'latest_version_number': latest_version.numero_version}
        except Exception as e:
            app.logger.warn(f"No se pudo inyectar la versión (la tabla puede no existir aún): {e}")
        return {'latest_version_number': 'N/A'}

    # Handlers de Error
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        db.session.rollback()
        return render_template('500.html'), 500

    # --- 6. Registrar Comandos CLI ---
    @app.cli.command('create-superuser')
    @click.argument('username')
    @click.argument('email')
    @click.argument('password')
    @click.argument('nombre')
    @click.argument('primer_apellido')
    @click.argument('telefono')
    @with_appcontext
    def create_superuser(username, email, password, nombre, primer_apellido, telefono):
        """Crea el primer usuario como Superuser."""
        if User.query.filter_by(role='Superuser').first():
            print('Error: Ya existe un Superuser.')
            return
        
        if User.query.filter((User.username == username) | (User.email == email)).first():
            print('Error: Ese nombre de usuario o email ya existen.')
            return

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        superuser = User(
            username=username, 
            email=email.lower(), 
            password=hashed_password,
            nombre=nombre, 
            primer_apellido=primer_apellido, 
            telefono=telefono,
            role='Superuser',
            avatar_url='uploads/avatars/default.png'
        )
        db.session.add(superuser)
        db.session.commit()
        print(f'Superuser {username} creado exitosamente.')


    # --- 7. Retornar la App Creada ---
    return app

# ======================================================================
# --- PUNTO DE ENTRADA (SOLO PARA EJECUCIÓN DIRECTA) ---
# ======================================================================
if __name__ == '__main__':
    # Crear la aplicación usando la factory
    app = create_app()
    
    # Crear tablas si no existen (solo para desarrollo local con sqlite)
    with app.app_context():
        db.create_all()
        
    app.run(host='0.0.0.0', debug=True, port=3030)

