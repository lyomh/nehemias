import streamlit as st
from auth import autenticar_usuario, iniciar_sesion, cerrar_sesion, verificar_acceso
from database import registrar_accion, obtener_conteos_estado
from views.admin_usuarios import vista_gestionar_usuarios
from views.admin_catalogos import vista_gestionar_eventos
from views.auditoria import vista_auditoria
from views.actividades import vista_nueva_solicitud, vista_seguimiento_red, vista_listado_rs
from views.tablero import vista_tablero
from estilos import aplicar_estilos_personalizados
from registro_config import obtener_registrador

# Configuración de página e indicadores técnicos
logger = obtener_registrador("aplicacion_principal")

st.set_page_config(
    page_title="Proyecto Nehemías - Vigilancia Epidemiológica",
    page_icon="🛡️",
    layout="wide"
)

# Aplicar Estilos Premium (Centralizado en Python)
aplicar_estilos_personalizados()

def pantalla_login():
    """Pantalla de inicio de sesión con estética institucional limpia."""
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    _, col_centro, _ = st.columns([1, 1.2, 1])
    
    with col_centro:
        st.markdown('<div class="stContainer">', unsafe_allow_html=True)
        st.image("assets/logo_egreisp.png", width=220)
        st.markdown("## ACCESO AL SISTEMA")
        st.markdown("**Proyecto Nehemías** - Gestión de Vigilancia")
        nombre_usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("INGRESAR AL PORTAL"):
            usuario = autenticar_usuario(nombre_usuario, clave)
            if usuario:
                iniciar_sesion(usuario)
                registrar_accion(usuario['id'], "LOGIN_EXITOSO")
                st.rerun()
            else:
                st.error("Credenciales no válidas. Por favor verifique.")
        st.markdown('</div>', unsafe_allow_html=True)

def aplicacion_principal():
    """Estructura principal de la aplicación con navegación profesional."""
    st.sidebar.image("assets/logo_egreisp.png", width=180)
    id_usuario = st.session_state['id_usuario']
    nombre_usuario = st.session_state['nombre_usuario']
    rol = st.session_state['rol']
    id_subregion = st.session_state.get('subregion_id')
    
    st.sidebar.markdown(f"### 👤 {nombre_usuario}")
    st.sidebar.caption(f"Nivel de Acceso: {rol}")
    st.sidebar.divider()
    
    if st.sidebar.button("🔓 SALIR DEL SISTEMA"):
        registrar_accion(id_usuario, "LOGOUT")
        cerrar_sesion()
    
    # 1. Definición de Menús e Indicadores Dinámicos
    if rol == 'ARD':
        menu = ["Panel ARD (Central)", "Gestión de RED", "Gestión de Catálogos", "Auditoría de Logs"]
        seleccion = st.sidebar.radio("MENÚ PRINCIPAL", menu)
    elif rol == 'ART':
        menu = ["Panel ART (Territorial)", "Gestión de RS"]
        seleccion = st.sidebar.radio("GESTIÓN TERRITORIAL", menu)
    elif rol == 'RED':
        df_conteos = obtener_conteos_estado(rol, id_usuario)
        conteos = {fila['status']: fila['total'] for _, fila in df_conteos.iterrows()}
        c_tramite = conteos.get('Activa', 0) + conteos.get('En Proceso', 0)
        c_aprobacion = conteos.get('En Revisión', 0)
        c_historico = conteos.get('Cerrada', 0) + conteos.get('Anulada', 0)
        
        opciones_menu = {
            f"Solicitud Nueva": "Solicitud Nueva", 
            f"En Trámite ({c_tramite})": "En Trámite", 
            f"A Aprobación ({c_aprobacion})": "A Aprobación", 
            f"Histórico ({c_historico})": "Histórico", 
            "Mi Perfil": "Mi Perfil"
        }
        seleccion_fila = st.sidebar.radio("FLUJO DE TRABAJO", list(opciones_menu.keys()))
        seleccion = opciones_menu[seleccion_fila]
    elif rol == 'RS':
        df_conteos = obtener_conteos_estado(rol, id_usuario, id_subregion=id_subregion)
        conteos = {fila['status']: fila['total'] for _, fila in df_conteos.iterrows()}
        c_entrada = conteos.get('Activa', 0)
        c_tramite = conteos.get('En Proceso', 0)
        c_revision = conteos.get('En Revisión', 0)
        c_historial = conteos.get('Cerrada', 0) + conteos.get('Anulada', 0)
        
        opciones_menu = {
            f"Bandeja de Entrada ({c_entrada})": "Bandeja de Entrada", 
            f"Lotes en Trámite ({c_tramite})": "Lotes en Trámite", 
            f"En Revisión ({c_revision})": "En Revisión", 
            f"Historial RS ({c_historial})": "Historial RS"
        }
        seleccion_fila = st.sidebar.radio("OPERACIÓN SUBREGIONAL", list(opciones_menu.keys()))
        seleccion = opciones_menu[seleccion_fila]
    else:
        menu = ["Inicio"]
        seleccion = st.sidebar.radio("Navegación", menu)
    
    st.sidebar.divider()
    
    # Título de Sección con Breadcrumb Visual
    st.markdown(f"#### 🏠 Sistema / {rol} / {seleccion}")
    st.header(f"{seleccion}", divider='green')
    
    # 2. Renderizado de Vistas
    try:
        if seleccion in ["Panel ARD (Central)", "Panel ART (Territorial)"]:
            vista_tablero(rol, id_usuario)
        elif seleccion in ["Gestión de RED", "Gestión de RS"]:
            vista_gestionar_usuarios(id_usuario, rol)
        elif seleccion == "Gestión de Catálogos":
            vista_gestionar_eventos(id_usuario)
        elif seleccion == "Auditoría de Logs":
            vista_auditoria()
        elif seleccion == "Solicitud Nueva":
            vista_nueva_solicitud(id_usuario)
        elif seleccion == "En Trámite":
            vista_seguimiento_red(id_usuario, ['Activa', 'En Proceso'], "Seguimiento de Gestión Subregional")
        elif seleccion == "A Aprobación":
            vista_seguimiento_red(id_usuario, ['En Revisión'], "Auditoría Técnica Departamental")
        elif seleccion == "Histórico":
            vista_seguimiento_red(id_usuario, ['Cerrada', 'Anulada'], "Histórico de Gestiones Finalizadas")
        
        # Vistas RS
        elif seleccion == "Bandeja de Entrada":
            vista_listado_rs(id_usuario, id_subregion, ['Activa'], "Nuevas Solicitudes Asignadas")
        elif seleccion == "Lotes en Trámite":
            vista_listado_rs(id_usuario, id_subregion, ['En Proceso'], "Gestión de Lotes en Ejecución")
        elif seleccion == "En Revisión":
            vista_listado_rs(id_usuario, id_subregion, ['En Revisión'], "Solicitudes en Proceso de Aprobación")
        elif seleccion == "Historial RS":
            vista_listado_rs(id_usuario, id_subregion, ['Cerrada', 'Anulada'], "Histórico de Gestión Subregional")
        else:
            st.info("Módulo en desarrollo.")
    except Exception as e:
        logger.error(f"Error fatal renderizando la vista '{seleccion}' para el usuario {id_usuario}: {str(e)}")
        st.error("Ha ocurrido un error inesperado al cargar esta sección. El equipo técnico ha sido notificado vía logs.")

if __name__ == "__main__":
    if not st.session_state.get('autenticado'):
        pantalla_login()
    else:
        aplicacion_principal()
