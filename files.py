from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_from_directory
import os
import uuid # Para generar nombres de archivo únicos
from datetime import datetime
from werkzeug.utils import secure_filename
import mimetypes # Para determinar el tipo MIME de los archivos

# Importa db, File y User desde models.py
from models import db, File, User

# Importa el decorador role_required desde app.py o perfil.py
# Asumiendo que role_required está disponible globalmente o se importa desde app.py
# Si no, necesitarías importarlo de donde lo tengas definido (ej: from app import role_required)
# Para este ejemplo, lo definiremos aquí si no está accesible globalmente, o asumiremos que se importa.
from functools import wraps

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
                return redirect(url_for('login'))
            
            user_role = session.get('role')
            if user_role not in roles:
                flash('No tienes permiso para acceder a esta página.', 'danger')
                return redirect(url_for('home')) # O a una página de "Acceso Denegado"
            return f(*args, **kwargs)
        return decorated_function
    return decorator


files_bp = Blueprint('files', __name__)

# Configuración de extensiones permitidas y carpetas de subida
# Estas se adjuntarán desde app.py, pero las definimos aquí para referencia
# y para la función allowed_file_extension
ALLOWED_FILE_EXTENSIONS = {
    'pdf', 'jpg', 'jpeg', 'png', 'gif', 'mp3', 'mp4', 'aiff', 'txt', 'docx',
    'xls', 'odf', 'xml', 'gpx', 'kml', 'kmz', 'ico', 'icon', 'wma', 'wmv', 'avi'
}

# Función auxiliar para verificar la extensión del archivo
def allowed_file_extension(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_FILE_EXTENSIONS

# Función auxiliar para determinar el tipo de archivo para categorización
def get_file_category(mime_type):
    if mime_type.startswith('image/'):
        return 'image'
    elif mime_type.startswith('audio/'):
        return 'audio'
    elif mime_type.startswith('video/'):
        return 'video'
    elif mime_type.startswith('application/pdf') or \
         mime_type == 'text/plain' or \
         mime_type.startswith('application/msword') or \
         mime_type.startswith('application/vnd.openxmlformats-officedocument.wordprocessingml') or \
         mime_type.startswith('application/vnd.ms-excel') or \
         mime_type.startswith('application/vnd.oasis.opendocument.spreadsheet') or \
         mime_type.startswith('application/xml') or \
         mime_type.startswith('text/xml'):
        return 'document'
    elif mime_type in ['application/gpx+xml', 'application/vnd.google-earth.kml+xml', 'application/vnd.google-earth.kmz']:
        return 'map'
    elif mime_type.startswith('image/x-icon') or mime_type.startswith('image/vnd.microsoft.icon'): # .ico, .icon
        return 'icon'
    else:
        return 'other'

def get_all_app_assets():
    """
    Escanea las carpetas de subida predefinidas de la aplicación (excluyendo la de 'files')
    y devuelve una lista de diccionarios de archivos.
    Estos archivos no están necesariamente en el modelo de base de datos 'File'.
    """
    app_assets = []
    # Obtener todas las carpetas de subida relevantes de app.config
    # Asegúrate de que estas rutas se pasen correctamente desde app.py
    upload_folders_config = {
        'avatars': current_app.config.get('UPLOAD_FOLDER'),
        'project_images': current_app.config.get('PROJECT_IMAGE_UPLOAD_FOLDER'),
        'note_images': current_app.config.get('NOTE_IMAGE_UPLOAD_FOLDER'),
        'caminata_images': current_app.config.get('CAMINATA_IMAGE_UPLOAD_FOLDER'),
        'pagos_images': current_app.config.get('PAGOS_IMAGE_UPLOAD_FOLDER'),
        'calendar_images': current_app.config.get('CALENDAR_IMAGE_UPLOAD_FOLDER'),
        'songs': current_app.config.get('SONGS_UPLOAD_FOLDER'),
        'covers': current_app.config.get('COVERS_UPLOAD_FOLDER'),
        'aboutus_images': current_app.config.get('ABOUTUS_IMAGE_UPLOAD_FOLDER'),
        # La carpeta 'files' es gestionada por el modelo File, así que la excluimos aquí
        # 'files': current_app.config.get('UPLOAD_FILES_FOLDER'),
    }

    for folder_name, folder_path in upload_folders_config.items():
        if folder_path and os.path.exists(folder_path):
            for root, _, filenames in os.walk(folder_path):
                for filename in filenames:
                    full_path = os.path.join(root, filename)
                    # La ruta relativa debe ser desde 'static/' para que url_for('static', filename=...) funcione
                    relative_path_from_static = os.path.relpath(full_path, os.path.join(current_app.root_path, 'static'))
                    
                    mime_type, _ = mimetypes.guess_type(full_path)
                    if not mime_type:
                        mime_type = 'application/octet-stream'

                    file_category = get_file_category(mime_type)

                    # Crear un diccionario que imita la estructura del modelo File
                    # Se asigna un ID de cadena único para estos archivos virtuales (activos de la aplicación)
                    app_assets.append({
                        'id': f"app_asset_{uuid.uuid4()}", # ID único de cadena para activos de la aplicación
                        'original_filename': filename,
                        'unique_filename': filename, # Para activos de la aplicación, original y único pueden ser lo mismo para mostrar
                        'file_path': relative_path_from_static.replace('\\', '/'), # Asegura barras diagonales para URLs
                        'file_type': file_category,
                        'mime_type': mime_type,
                        'upload_date': datetime.fromtimestamp(os.path.getmtime(full_path)), # Usar la fecha de última modificación
                        'user_id': None, # Sin usuario específico para activos de la aplicación
                        'is_visible': True,
                        'is_used': True, # Asumimos que los activos de la aplicación están en uso
                        'is_app_asset': True, # Bandera para distinguirlos de los archivos de la base de datos
                        'folder_name': folder_name # Nombre de la carpeta de origen para mostrar
                    })
    return app_assets


@files_bp.route('/files', methods=['GET', 'POST'])
@role_required(['Superuser', 'Usuario Regular']) # Permite a Superuser y Usuario Regular acceder
def ver_files():
    if 'user_id' not in session:
        flash('Por favor, inicia sesión para acceder a la gestión de archivos.', 'info')
        return redirect(url_for('login'))

    user_id = session['user_id']
    
    # Lógica de búsqueda
    search_query = request.args.get('search', '').strip()
    file_type_filter = request.args.get('file_type', '').strip()
    date_filter = request.args.get('date', '').strip()

    # 1. Obtener archivos de la base de datos (archivos subidos por el usuario)
    db_files_query = File.query.filter_by(user_id=user_id) # Solo archivos del usuario logueado

    if search_query:
        db_files_query = db_files_query.filter(File.original_filename.ilike(f'%{search_query}%'))
    
    # Si el filtro de tipo es 'application_assets', no aplicar a db_files
    if file_type_filter and file_type_filter != 'application_assets':
        db_files_query = db_files_query.filter_by(file_type=file_type_filter)
    
    if date_filter:
        try:
            # Asume formato YYYY-MM-DD para la fecha de búsqueda
            search_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            db_files_query = db_files_query.filter(db.func.date(File.upload_date) == search_date)
        except ValueError:
            flash('Formato de fecha de búsqueda inválido. Usa YYYY-MM-DD.', 'danger')

    db_files = db_files_query.order_by(File.upload_date.desc()).all()

    # Convertir objetos SQLAlchemy a diccionarios para un manejo consistente con los activos de la aplicación
    all_files = []
    for f in db_files:
        file_dict = {
            'id': f.id,
            'original_filename': f.original_filename,
            'unique_filename': f.unique_filename,
            'file_path': f.file_path,
            'file_type': f.file_type,
            'mime_type': f.mime_type,
            'upload_date': f.upload_date,
            'user_id': f.user_id,
            'is_visible': f.is_visible,
            'is_used': f.is_used,
            'is_app_asset': False, # Bandera para archivos de la base de datos
            'folder_name': 'files' # Indicar que provienen de la carpeta 'files'
        }
        all_files.append(file_dict)

    # 2. Obtener activos de la aplicación (archivos escaneados dinámicamente)
    app_assets = get_all_app_assets()

    # Aplicar filtros a los activos de la aplicación manualmente
    filtered_app_assets = []
    if file_type_filter == 'application_assets' or not file_type_filter: # Si se filtra por app_assets o no hay filtro de tipo
        for asset in app_assets:
            match_search = True
            match_type = True
            match_date = True

            if search_query and search_query.lower() not in asset['original_filename'].lower():
                match_search = False
            
            # Si se ha seleccionado un tipo de archivo específico (que no sea 'application_assets')
            # entonces los activos de la aplicación solo deben coincidir si su tipo coincide con el filtro.
            if file_type_filter and file_type_filter != 'application_assets' and asset['file_type'] != file_type_filter:
                match_type = False
            
            if date_filter:
                try:
                    search_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                    if asset['upload_date'].date() != search_date:
                        match_date = False
                except ValueError:
                    pass # El error de formato de fecha ya se manejó para los archivos de la BD

            if match_search and match_type and match_date:
                filtered_app_assets.append(asset)
    
    # Combinar todos los archivos (archivos de la base de datos + activos de la aplicación filtrados)
    all_files.extend(filtered_app_assets)
    all_files.sort(key=lambda x: x['upload_date'], reverse=True) # Ordenar por fecha descendente

    # Categorizar todos los archivos para la vista
    categorized_files = {
        'image': [], 'audio': [], 'video': [], 'document': [],
        'map': [], 'icon': [], 'other': [], 'application_assets': [] # Nueva categoría para activos genéricos de la aplicación
    }
    for file_data in all_files:
        if file_data['is_app_asset']:
            categorized_files['application_assets'].append(file_data)
        else:
            category = get_file_category(file_data['mime_type'])
            if category in categorized_files:
                categorized_files[category].append(file_data)
            else:
                categorized_files['other'].append(file_data)

    # Opciones para el filtro de tipo de archivo en la plantilla (incluir 'application_assets')
    all_file_types_options = set([f['file_type'] for f in all_files])
    all_file_types_options.add('application_assets') # Añadir la nueva categoría
    file_type_options = sorted(list(all_file_types_options))
    
    return render_template(
        'ver_files.html',
        categorized_files=categorized_files,
        search_query=search_query,
        file_type_filter=file_type_filter,
        date_filter=date_filter,
        file_type_options=file_type_options
    )


@files_bp.route('/upload_file', methods=['POST'])
@role_required(['Superuser', 'Usuario Regular'])
def upload_file():
    if 'user_id' not in session:
        flash('Necesitas iniciar sesión para subir archivos.', 'danger')
        return redirect(url_for('login'))

    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo.', 'danger')
        return redirect(url_for('files.ver_files'))

    uploaded_file = request.files['file']

    if uploaded_file.filename == '':
        flash('No se seleccionó ningún archivo.', 'danger')
        return redirect(url_for('files.ver_files'))

    if uploaded_file and allowed_file_extension(uploaded_file.filename):
        original_filename = secure_filename(uploaded_file.filename)
        # Generar un nombre de archivo único para evitar colisiones
        unique_filename = str(uuid.uuid4()) + os.path.splitext(original_filename)[1]
        
        # Define la carpeta de subida para archivos generales (asegúrate de que exista en app.py)
        upload_folder = current_app.config.get('UPLOAD_FILES_FOLDER')
        if not upload_folder:
            flash('Error de configuración: Carpeta de subida de archivos no definida.', 'danger')
            current_app.logger.error("UPLOAD_FILES_FOLDER no está definido en app.config")
            return redirect(url_for('files.ver_files'))

        file_path_on_disk = os.path.join(upload_folder, unique_filename)
        uploaded_file.save(file_path_on_disk)

        # Determinar el tipo MIME y la categoría del archivo
        mime_type, _ = mimetypes.guess_type(file_path_on_disk)
        if not mime_type:
            mime_type = 'application/octet-stream' # Tipo genérico si no se puede adivinar

        file_category = get_file_category(mime_type)

        # Guardar información en la base de datos
        new_file = File(
            original_filename=original_filename,
            unique_filename=unique_filename,
            file_path=os.path.join('uploads', 'files', unique_filename), # Ruta relativa para URL
            file_type=file_category,
            mime_type=mime_type,
            upload_date=datetime.utcnow(),
            user_id=session['user_id']
        )
        db.session.add(new_file)
        db.session.commit()
        flash('Archivo subido exitosamente.', 'success')
    else:
        flash('Tipo de archivo no permitido o archivo inválido.', 'danger')

    return redirect(url_for('files.ver_files'))

@files_bp.route('/download_file/<int:file_id>') # Solo IDs enteros para archivos de BD
@role_required(['Superuser', 'Usuario Regular'])
def download_file(file_id):
    if 'user_id' not in session:
        flash('Necesitas iniciar sesión para descargar archivos.', 'danger')
        return redirect(url_for('login'))
    
    file_record = db.session.get(File, file_id)

    if not file_record:
        flash('Archivo no encontrado.', 'danger')
        return redirect(url_for('files.ver_files'))
    
    # Asegurarse de que el usuario solo pueda descargar sus propios archivos si es Usuario Regular
    if session.get('role') == 'Usuario Regular' and file_record.user_id != session['user_id']:
        flash('No tienes permiso para descargar este archivo.', 'danger')
        return redirect(url_for('files.ver_files'))

    # La ruta completa en el sistema de archivos
    full_path = os.path.join(current_app.root_path, 'static', file_record.file_path)

    if os.path.exists(full_path):
        # send_from_directory requiere la ruta del directorio y el nombre del archivo
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        return send_from_directory(directory, filename, as_attachment=True, download_name=file_record.original_filename)
    else:
        flash('El archivo no existe en el servidor.', 'danger')
        return redirect(url_for('files.ver_files'))

@files_bp.route('/delete_file/<int:file_id>', methods=['POST']) # Solo IDs enteros para archivos de BD
@role_required(['Superuser', 'Usuario Regular'])
def delete_file(file_id):
    if 'user_id' not in session:
        flash('Necesitas iniciar sesión para eliminar archivos.', 'danger')
        return redirect(url_for('login'))

    file_record = db.session.get(File, file_id)

    if not file_record:
        flash('Archivo no encontrado.', 'danger')
        return redirect(url_for('files.ver_files'))

    # Asegurarse de que el usuario solo pueda eliminar sus propios archivos si es Usuario Regular
    if session.get('role') == 'Usuario Regular' and file_record.user_id != session['user_id']:
        flash('No tienes permiso para eliminar este archivo.', 'danger')
        return redirect(url_for('files.ver_files'))

    try:
        # Eliminar el archivo del sistema de archivos
        full_path = os.path.join(current_app.root_path, 'static', file_record.file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            flash(f'Archivo "{file_record.original_filename}" eliminado del servidor.', 'info')
        else:
            flash(f'Advertencia: El archivo "{file_record.original_filename}" no se encontró en el servidor, pero se eliminará de la base de datos.', 'warning')

        # Eliminar el registro de la base de datos
        db.session.delete(file_record)
        db.session.commit()
        flash('Archivo eliminado exitosamente de la base de datos.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el archivo: {e}', 'danger')
        current_app.logger.error(f"Error al eliminar archivo {file_id}: {e}")

    return redirect(url_for('files.ver_files'))

# Rutas para exportar (estas son más complejas y requerirían librerías adicionales)
# Por ahora, solo se proporciona una estructura básica y una nota.
@files_bp.route('/export_file/<int:file_id>/<string:export_type>')
@role_required(['Superuser', 'Usuario Regular'])
def export_file(file_id, export_type):
    file_record = db.session.get(File, file_id)
    if not file_record:
        flash('Archivo no encontrado para exportar.', 'danger')
        return redirect(url_for('files.ver_files'))

    # Lógica de exportación (requiere librerías como Pillow para JPG, reportlab/fpdf para PDF)
    # y manejo de contenido para TXT (asegurando UTF-8)
    
    # Ejemplo muy básico para TXT (solo si el archivo original es TXT)
    if export_type == 'txt' and file_record.mime_type == 'text/plain':
        full_path = os.path.join(current_app.root_path, 'static', file_record.file_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Puedes devolver el contenido como un archivo de texto
            response = current_app.response_class(
                content,
                mimetype='text/plain; charset=utf-8',
                headers={"Content-Disposition": f"attachment;filename={file_record.original_filename.rsplit('.', 1)[0]}.txt"}
            )
            return response
        except Exception as e:
            flash(f'Error al exportar a TXT: {e}', 'danger')
            current_app.logger.error(f"Error exportando TXT: {e}")
            return redirect(url_for('files.ver_files'))
    
    # Para JPG y PDF, necesitarías librerías específicas:
    # - Para JPG: Si el archivo es una imagen, podrías reescalarla y guardarla como JPG.
    #   Si es un documento, necesitarías renderizarlo a una imagen primero.
    # - Para PDF: Si el archivo es un documento (docx, xls, txt), necesitarías librerías
    #   que puedan convertir esos formatos a PDF.
    
    flash(f'La exportación a {export_type.upper()} para este tipo de archivo no está implementada completamente o requiere librerías adicionales.', 'warning')
    return redirect(url_for('files.ver_files'))
