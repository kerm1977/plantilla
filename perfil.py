from flask import Blueprint, render_template, request, flash, redirect, url_for, session, current_app, send_from_directory
from models import db, bcrypt, User
# Ya no se necesita 'wraps' aquí si no se define el decorador
import os
# Ya no se necesita 'shutil'
# Ya no se necesita 'secure_filename'
from datetime import datetime
# Ya no se necesita 'uuid'

# --- Importar utilidades ---
from app_utils import login_required, save_upload

perfil_bp = Blueprint('perfil', __name__)

# --- Decorador 'login_required' ELIMINADO ---
# Se importa desde app_utils

# --- RUTA PRINCIPAL DEL PERFIL (SOLO MUESTRA INFORMACIÓN) ---
@perfil_bp.route('/')
@login_required
def perfil():
    user = User.query.get_or_404(session['user_id'])
    
    # Implementando Optimización #9: Mover lógica de plantilla a la ruta
    sections = {
        "Información de Contacto": [
            ("Teléfono", user.telefono), ("Email", user.email), ("Empresa", user.empresa),
            ("Dirección (Provincia)", user.direccion), ("Rol", user.role), ("Cédula", user.cedula)
        ],
        "Información Adicional": [
            ("Fecha de Registro", user.fecha_registro.strftime('%d/%m/%Y %H:%M') if user.fecha_registro else None),
            ("Fecha de Cumpleaños", user.fecha_cumpleanos.strftime('%d/%m/%Y') if user.fecha_cumpleanos else None)
        ],
        "Información de Salud": [
            ("Tipo de Sangre", user.tipo_sangre), ("Póliza", user.poliza), ("Aseguradora", user.aseguradora),
            ("Alergias", user.alergias), ("Enfermedades Crónicas", user.enfermedades_cronicas)
        ],
        "Contacto de Emergencia": [
            ("Nombre", user.nombre_emergencia), ("Teléfono", user.telefono_emergencia)
        ]
    }
    
    return render_template('perfil.html', user=user, sections=sections)

# --- NUEVA RUTA DEDICADA PARA EDITAR EL PERFIL ---
@perfil_bp.route('/editar', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    user = User.query.get_or_404(session['user_id'])
    
    # Opciones para los <select> del formulario
    provincia_opciones = ["Cartago", "Limón", "Puntarenas", "San José", "Heredia", "Guanacaste", "Alajuela"]
    tipo_sangre_opciones = ["Seleccionar Tipo", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

    if request.method == 'POST':
        # --- Lógica para actualizar el perfil ---
        # Validar unicidad de username y email si cambian
        new_username = request.form.get('username')
        new_email = request.form.get('email')

        if new_username != user.username and User.query.filter_by(username=new_username).first():
            flash('Ese nombre de usuario ya está en uso. Por favor, elige otro.', 'danger')
        elif new_email and new_email != user.email and User.query.filter_by(email=new_email).first():
            flash('Ese correo electrónico ya está registrado. Por favor, usa otro.', 'danger')
        else:
            user.username = new_username
            user.email = new_email
            user.nombre = request.form.get('nombre')
            user.primer_apellido = request.form.get('primer_apellido')
            user.segundo_apellido = request.form.get('segundo_apellido')
            user.telefono = request.form.get('telefono')
            user.cedula = request.form.get('cedula')
            user.direccion = request.form.get('direccion')
            user.nombre_emergencia = request.form.get('nombre_emergencia')
            user.telefono_emergencia = request.form.get('telefono_emergencia')
            user.tipo_sangre = request.form.get('tipo_sangre')
            user.empresa = request.form.get('empresa')
            user.poliza = request.form.get('poliza')
            user.aseguradora = request.form.get('aseguradora')
            user.alergias = request.form.get('alergias')
            user.enfermedades_cronicas = request.form.get('enfermedades_cronicas')

            fecha_cumpleanos_str = request.form.get('fecha_cumpleanos')
            if fecha_cumpleanos_str:
                user.fecha_cumpleanos = datetime.strptime(fecha_cumpleanos_str, '%Y-%m-%d').date()
            else:
                user.fecha_cumpleanos = None

            # --- Lógica para actualizar el avatar (Usando Optimización #6) ---
            if 'avatar' in request.files and request.files['avatar'].filename != '':
                saved_path = save_upload(request.files['avatar'], 'avatars')
                if saved_path:
                    # Opcional: Eliminar avatar anterior si no es el default
                    if user.avatar_url and user.avatar_url != 'uploads/avatars/default.png':
                        try:
                            old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], os.path.basename(user.avatar_url))
                            if os.path.exists(old_path):
                                os.remove(old_path)
                        except Exception as e:
                            current_app.logger.error(f"No se pudo eliminar el avatar anterior: {e}")
                    
                    user.avatar_url = saved_path
                else:
                    # save_upload falló (ej. tipo de archivo)
                    # Renderizar de nuevo la plantilla de edición
                    return render_template('editar_perfil.html', 
                                           user=user, 
                                           provincia_opciones=provincia_opciones, 
                                           tipo_sangre_opciones=tipo_sangre_opciones)


            db.session.commit()
            flash('¡Perfil actualizado con éxito!', 'success')
            return redirect(url_for('perfil.perfil'))

    return render_template('editar_perfil.html', 
                           user=user, 
                           provincia_opciones=provincia_opciones, 
                           tipo_sangre_opciones=tipo_sangre_opciones)


@perfil_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    # TODO: Implementar WTForms (ChangePasswordForm)
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        user = User.query.get(session['user_id'])
        
        if not user.password:
            flash('No puedes cambiar la contraseña de una cuenta creada con un proveedor externo (ej. Google).', 'danger')
            return redirect(url_for('perfil.perfil'))

        if not bcrypt.check_password_hash(user.password, current_password):
            flash('La contraseña actual es incorrecta.', 'danger')
        elif new_password != confirm_password:
            flash('Las nuevas contraseñas no coinciden.', 'danger')
        else:
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            user.password = hashed_password
            db.session.commit()
            flash('Contraseña actualizada con éxito.', 'success')
            return redirect(url_for('perfil.perfil'))
    return render_template('change_password.html')

# (El resto de tus rutas como backup_database, etc. pueden permanecer aquí sin cambios)
