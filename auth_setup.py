# oauth.py
import os
from flask import Blueprint, url_for, redirect, flash
from flask_login import login_user
from authlib.integrations.flask_client import OAuth
from werkzeug.security import generate_password_hash

# Importa tus modelos y la sesión de la base de datos.
# Asegúrate de que la ruta de importación sea correcta desde donde ejecutas tu app.
from models import db, User, OAuthSignIn

# 1. Crear el Blueprint y la instancia de OAuth
oauth_bp = Blueprint('oauth_bp', __name__, url_prefix='/oauth')
oauth = OAuth()

# 2. Función para inicializar los proveedores de OAuth con la app de Flask
def init_oauth(app):
    """Inicializa los proveedores de OAuth con la configuración de la app."""
    oauth.init_app(app)
    
    # Registrar GitHub
    oauth.register(
        name='github',
        client_id=app.config.get('GITHUB_CLIENT_ID'),
        client_secret=app.config.get('GITHUB_CLIENT_SECRET'),
        api_base_url='https://api.github.com/',
        access_token_url='https://github.com/login/oauth/access_token',
        authorize_url='https://github.com/login/oauth/authorize',
        client_kwargs={'scope': 'user:email'},
    )
    
    # Registrar Google (opcional, si también lo quieres)
    oauth.register(
        name='google',
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_id=app.config.get('GOOGLE_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        client_kwargs={'scope': 'openid email profile'}
    )

    # Registrar Facebook (opcional, si también lo quieres)
    oauth.register(
        name='facebook',
        client_id=app.config.get('FACEBOOK_CLIENT_ID'),
        client_secret=app.config.get('FACEBOOK_CLIENT_SECRET'),
        api_base_url='https://graph.facebook.com/v12.0/',
        access_token_url='https://graph.facebook.com/v12.0/oauth/access_token',
        authorize_url='https://www.facebook.com/v12.0/dialog/oauth',
        client_kwargs={'scope': 'email public_profile'},
    )

# 3. Rutas de Autenticación
@oauth_bp.route('/login/<provider>')
def login(provider):
    """
    Redirige al usuario a la página de autorización del proveedor (ej. GitHub).
    """
    redirect_uri = url_for('oauth_bp.authorize', provider=provider, _external=True)
    return oauth.create_client(provider).authorize_redirect(redirect_uri)

@oauth_bp.route('/authorize/<provider>')
def authorize(provider):
    """
    Maneja la respuesta del proveedor después de que el usuario autoriza la app.
    """
    client = oauth.create_client(provider)
    try:
        token = client.authorize_access_token()
    except Exception as e:
        flash(f"Error al autorizar con {provider.capitalize()}: {str(e)}", 'danger')
        return redirect(url_for('login')) # Redirige a tu página de login principal

    user_info = get_user_info(client, provider)
    if not user_info or not user_info.get('email'):
        flash(f'No se pudo obtener el email de {provider.capitalize()}. Por favor, asegúrate de que tu cuenta tiene un email público o intenta con otro método.', 'danger')
        return redirect(url_for('login'))

    # Llama a la función auxiliar para manejar la lógica de la base de datos
    user = get_or_create_oauth_user(provider, user_info)

    if user:
        login_user(user)
        flash('¡Has iniciado sesión correctamente!', 'success')
    else:
        flash('Ocurrió un error inesperado durante el inicio de sesión.', 'danger')
        return redirect(url_for('login'))

    return redirect(url_for('index')) # Redirige a la página principal de tu app

# 4. Funciones Auxiliares
def get_or_create_oauth_user(provider, user_info):
    """
    Busca un usuario existente por su vinculación OAuth o por su email.
    Si no existe, crea un nuevo usuario y su vinculación.
    Devuelve el objeto User.
    """
    provider_user_id = user_info.get('id') or user_info.get('sub')
    user_email = user_info.get('email')

    # 1. Buscar si ya existe la vinculación OAuth
    oauth_link = OAuthSignIn.query.filter_by(
        provider=provider,
        provider_user_id=str(provider_user_id)
    ).first()

    if oauth_link:
        return oauth_link.user

    # 2. Si no hay vinculación, buscar si el usuario ya existe por su email
    user = User.query.filter_by(email=user_email).first()

    if not user:
        # 3. Si el usuario no existe en absoluto, crearlo
        user = User(
            email=user_email,
            username=f"{user_email.split('@')[0]}_{provider[:3]}{str(provider_user_id)[:4]}",
            nombre=user_info.get('name', '').split()[0] or user_info.get('given_name') or 'Usuario',
            primer_apellido=user_info.get('name', '').split()[-1] or user_info.get('family_name') or 'Social',
            password=generate_password_hash(os.urandom(24).hex()),
            telefono="00000000", # Valor por defecto, el usuario debería actualizarlo
        )
        db.session.add(user)
        db.session.flush()

    # 4. Crear la nueva vinculación OAuth para el usuario (nuevo o existente)
    new_oauth_link = OAuthSignIn(
        provider=provider,
        provider_user_id=str(provider_user_id),
        user_id=user.id
    )
    db.session.add(new_oauth_link)
    db.session.commit()

    return user

def get_user_info(client, provider):
    """Obtiene la información del usuario del proveedor de manera consistente."""
    if provider == 'github':
        resp = client.get('user').json()
        if not resp.get('email'):
            emails = client.get('user/emails').json()
            if emails:
                primary_email = next((e['email'] for e in emails if e.get('primary')), None)
                resp['email'] = primary_email or (emails[0]['email'] if emails else None)
        return resp
    if provider == 'google':
        return client.get('https://www.googleapis.com/oauth2/v3/userinfo').json()
    if provider == 'facebook':
        return client.get('me?fields=id,name,email,first_name,last_name').json()
    return None
