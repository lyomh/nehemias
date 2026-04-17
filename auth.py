import streamlit as st
import bcrypt
from database import obtener_conexion, traducir_sql
from registro_config import obtener_registrador

# Configuración de registro
logger = obtener_registrador("autenticacion")

def generar_hash_clave(clave: str) -> str:
    """Genera un hash seguro para la contraseña usando bcrypt directamente."""
    # Bcrypt requiere bytes
    sal = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(clave.encode('utf-8'), sal)
    return hash_bytes.decode('utf-8')

def verificar_clave(clave: str, clave_hasheada: str) -> bool:
    """Compara una contraseña con su hash usando bcrypt."""
    try:
        # Bcrypt requiere bytes para ambos argumentos
        return bcrypt.checkpw(
            clave.encode('utf-8'), 
            clave_hasheada.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Error en verificación de bcrypt: {str(e)}")
        return False

def autenticar_usuario(nombre_usuario, clave):
    """
    Valida las credenciales contra la base de datos.
    Retorna los datos del usuario si es exitoso, None si falla.
    """
    try:
        with obtener_conexion() as conexion:
            cursor = conexion.cursor()
            query = "SELECT id, username, password_hash, role, subregion_id FROM users WHERE username = ? AND is_active = 1"
            cursor.execute(
                traducir_sql(query),
                (nombre_usuario,)
            )
            usuario = cursor.fetchone()
            
            if usuario:
                # Intento de verificación directa
                if verificar_clave(clave, usuario['password_hash']):
                    logger.info(f"Autenticación exitosa: {nombre_usuario}")
                    return dict(usuario)
                else:
                    logger.warning(f"Clave incorrecta para: {nombre_usuario}")
            else:
                logger.warning(f"Usuario no existe o inactivo: {nombre_usuario}")
            return None
    except Exception as e:
        logger.error(f"Error crítico en autenticar_usuario: {str(e)}")
        return None

def iniciar_sesion(datos_usuario):
    """Establece las variables de sesión tras un login exitoso."""
    st.session_state['autenticado'] = True
    st.session_state['id_usuario'] = datos_usuario['id']
    st.session_state['nombre_usuario'] = datos_usuario['username']
    st.session_state['rol'] = datos_usuario['role']
    st.session_state['subregion_id'] = datos_usuario['subregion_id']
    logger.info(f"Sesión iniciada: {datos_usuario['username']} [ID: {datos_usuario['id']}]")

def cerrar_sesion():
    """Limpia las variables de sesión."""
    nombre = st.session_state.get('nombre_usuario', 'Desconocido')
    logger.info(f"Cerrando sesión: {nombre}")
    for llave in list(st.session_state.keys()):
        del st.session_state[llave]
    st.rerun()

def verificar_acceso(roles_permitidos):
    """Verifica si el usuario actual tiene permiso."""
    if not st.session_state.get('autenticado'):
        return False
    return st.session_state.get('rol') in roles_permitidos
