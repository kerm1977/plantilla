import os
import uuid
from functools import wraps
from flask import session, flash, redirect, url_for, current_app
from werkzeug.utils import secure_filename

# --- DECORADORES DE AUTENTICACIÓN ---

def login_required(f):
    """
    Decorador que verifica si un usuario ha iniciado sesión.
    Si no, redirige a la página de login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'info')
            # CORREGIDO: Apunta al blueprint 'auth'
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    """
    Decorador para restringir el acceso a rutas basadas en roles.
    `roles` puede ser una cadena (un solo rol) o una lista de cadenas (múltiples roles).
    """
    if not isinstance(roles, list):
        roles = [roles]

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session or not session['logged_in']:
                flash('Por favor, inicia sesión para acceder a esta página.', 'info')
                # CORREGIDO: Apunta al blueprint 'auth'
                return redirect(url_for('auth.login'))

            user_role = session.get('role')
            if user_role not in roles:
                flash('No tienes permiso para acceder a esta página.', 'danger')
                # CORREGIDO: Apunta al blueprint 'main'
                return redirect(url_for('main.home')) 
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- UTILIDADES DE MANEJO DE ARCHIVOS ---

def allowed_file(filename):
    """Verifica si la extensión del archivo es una imagen permitida."""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file, subfolder='avatars'):
    """
    Guarda un archivo subido de forma segura en una subcarpeta de UPLOAD_FOLDER
    y devuelve la ruta relativa para la base de datos.
    """
    if file and file.filename != '' and allowed_file(file.filename):
        filename_base = secure_filename(file.filename)
        # Crear un nombre de archivo único para evitar colisiones
        unique_filename = str(uuid.uuid4()) + os.path.splitext(filename_base)[1]
        
        # Crear el directorio de subida si no existe
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Guardar el archivo
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        # Devolver la ruta relativa (ej: 'uploads/avatars/unique_id.png')
        return os.path.join('uploads', subfolder, unique_filename).replace('\\', '/')
        
    return None

