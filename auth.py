# auth.py
# Un nuevo Blueprint que ahora contiene toda la lógica de register, login, logout y reseteo de contraseña.

import re
import uuid
import os
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, current_app
)
from flask_mail import Message
from models import db, bcrypt, User
from app import mail  # Importar la instancia global 'mail' desde app.py
from app_utils import login_required, save_upload # Importar utilidades

# Crear el Blueprint de autenticación
auth_bp = Blueprint('auth', __name__)

# --- RUTAS DE AUTENTICACIÓN Y REGISTRO ---

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Opciones para los campos de selección (solo los necesarios para el registro)
    provincia_opciones = ["Cartago", "Limón", "Puntarenas", "San José", "Heredia", "Guanacaste", "Alajuela"]

    if request.method == 'POST':
        # --- Implementando Optimización #2: Registro Simplificado ---
        username = request.form['username_registro']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        nombre = request.form['nombre']
        primer_apellido = request.form['primer_apellido']
        telefono = request.form['telefono']
        email = request.form.get('email')
        segundo_apellido = request.form.get('segundo_apellido')

        # --- Bloque de Validación (Ideal para WTForms) ---
        if not (username and password and confirm_password and nombre and primer_apellido and telefono):
            flash('Por favor, completa todos los campos obligatorios.', 'danger')
            return render_template('register.html', provincia_opciones=provincia_opciones)

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('register.html', provincia_opciones=provincia_opciones)

        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return render_template('register.html', provincia_opciones=provincia_opciones)

        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe. Por favor, elige otro.', 'danger')
            return render_template('register.html', provincia_opciones=provincia_opciones)

        if email:
            if User.query.filter_by(email=email.lower()).first():
                flash('Ese correo electrónico ya está registrado. Por favor, usa otro.', 'danger')
                return render_template('register.html', provincia_opciones=provincia_opciones)
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                flash('Formato de correo electrónico inválido.', 'danger')
                return render_template('register.html', provincia_opciones=provincia_opciones)
        # --- Fin Bloque de Validación ---

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # --- Usando la utilidad save_upload (Optimización #6) ---
        avatar_url = 'uploads/avatars/default.png' # Por defecto
        if 'avatar' in request.files and request.files['avatar'].filename != '':
            saved_path = save_upload(request.files['avatar'], 'avatars')
            if saved_path:
                avatar_url = saved_path
            else:
                # save_upload falló (ej. tipo de archivo)
                return render_template('register.html', provincia_opciones=provincia_opciones)

        # --- Lógica de Superusuario (Reemplazar con CLI) ---
        # Implementando Optimización #7 (parcialmente): Eliminado before_request.
        # Esto es más simple y seguro que el check de before_request.
        role = 'Usuario Regular'
        if User.query.count() == 0:
            role = 'Superuser'
            current_app.logger.info(f"Registrando al primer usuario {username} como Superuser.")
        
        new_user = User(
            username=username,
            password=hashed_password,
            nombre=nombre,
            primer_apellido=primer_apellido,
            segundo_apellido=segundo_apellido,
            telefono=telefono,
            email=email.lower() if email else None,
            role=role,
            avatar_url=avatar_url
            # Todos los demás campos (salud, emergencia, etc.) se llenan en 'editar_perfil'
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('¡Registro exitoso! Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar el usuario: {e}', 'danger')
            current_app.logger.error(f"Error al registrar usuario {username}: {e}")
            return render_template('register.html', provincia_opciones=provincia_opciones)

    return render_template('register.html', provincia_opciones=provincia_opciones)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form['username_or_email']
        password = request.form['password']
        remember_me = request.form.get('remember_me')

        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email.lower())).first()

        # Comprobar si el usuario existe Y tiene una contraseña (para cuentas OAuth sin pass)
        if user and user.password and bcrypt.check_password_hash(user.password, password):
            if remember_me:
                session.permanent = True

            session['logged_in'] = True
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['theme'] = user.theme or 'light'
            session['lang'] = session.get('lang', 'es') # Asumir 'es' o usar get_locale
            
            user.last_login_at = datetime.utcnow()
            db.session.commit()

            flash(f'¡Bienvenido, {user.username}!', 'success')
            return redirect(url_for('perfil.perfil'))
        else:
            flash('Nombre de usuario, correo electrónico o contraseña incorrectos.', 'danger')
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('auth.login'))


# --- RUTAS DE RESETEO DE CONTRASEÑA ---

def send_reset_email(user):
    """Función helper para enviar el correo de reseteo."""
    token = user.get_reset_token()
    msg = Message('Solicitud de Restablecimiento de Contraseña',
                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[user.email])
    msg.body = f'''Para restablecer tu contraseña, visita el siguiente enlace:
{url_for('auth.reset_password', token=token, _external=True)}

Si no solicitaste este cambio, simplemente ignora este correo.
'''
    try:
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Error al enviar email de reseteo: {e}")
        return False

@auth_bp.route('/request_password_reset', methods=['GET', 'POST'])
def request_password_reset():
    if session.get('logged_in'):
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            if send_reset_email(user):
                flash('Se ha enviado un correo con las instrucciones para restablecer tu contraseña.', 'info')
            else:
                flash('Error al enviar el correo. Por favor, intenta de nuevo más tarde.', 'danger')
            return redirect(url_for('auth.login'))
        else:
            flash('No se encontró una cuenta con ese correo electrónico.', 'warning')
    return render_template('request_password_reset.html')


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if session.get('logged_in'):
        return redirect(url_for('main.home'))
    
    user = User.verify_reset_token(token)
    if not user:
        flash('El token es inválido o ha expirado.', 'warning')
        return redirect(url_for('auth.request_password_reset'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not password or not confirm_password or password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('reset_password.html', token=token)

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Tu contraseña ha sido actualizada. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', token=token)
