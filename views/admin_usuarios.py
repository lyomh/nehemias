import streamlit as st
import pandas as pd
from database import (
    obtener_conexion, 
    registrar_accion, 
    obtener_usuarios_por_creador, 
    obtener_catalogo_eventos, 
    obtener_subregiones,
    crear_usuario,
    actualizar_perfil_usuario,
    alternar_estado_usuario,
    restablecer_clave_usuario,
    traducir_sql
)
from auth import generar_hash_clave

def vista_gestionar_usuarios(id_usuario_actual, rol_actual):
    """Interfaz avanzada para la gestión de usuarios: Creación, Edición y Control de Acceso."""
    
    # Determinar qué rol puede crear el usuario actual
    rol_a_crear = 'RED' if rol_actual == 'ARD' else 'RS' if rol_actual == 'ART' else None
    
    if not rol_a_crear:
        st.error("Usted no tiene permisos para gestionar usuarios.")
        return

    # 1. Registro de Nuevos Usuarios
    st.subheader(f"Registro de nuevos {rol_a_crear}")
    with st.expander(f"Formulario de Alta: {rol_a_crear}"):
        with st.form("formulario_crear_usuario", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nuevo_nombre_usuario = st.text_input("Usuario (Correo o ID)")
                nueva_clave = st.text_input("Contraseña Temporal", type="password")
            
            with col2:
                id_sub = None
                id_evento = None
                
                if rol_a_crear == 'RS':
                    df_sub = obtener_subregiones()
                    if not df_sub.empty:
                        seleccion_sub = st.selectbox("Seleccione Subregión", df_sub['nombre'])
                        id_sub = int(df_sub[df_sub['nombre'] == seleccion_sub]['id'].values[0])
                    else:
                        st.error("No hay subregiones configuradas. Contacte al administrador.")
                else:
                    df_eventos = obtener_catalogo_eventos()
                    if not df_eventos.empty:
                        seleccion_evento = st.selectbox("Asignar Grupo Funcional (Evento)", df_eventos['nombre'])
                        id_evento = int(df_eventos[df_eventos['nombre'] == seleccion_evento]['id'].values[0])
                    else:
                        st.error("No hay grupos funcionales configurados. Contacte al administrador.")
            
            enviar = st.form_submit_button(f"REGISTRAR {rol_a_crear}")
            
            if enviar:
                if not nuevo_nombre_usuario or not nueva_clave:
                    st.warning("Complete todos los campos.")
                else:
                    try:
                        clave_hasheada = generar_hash_clave(nueva_clave)
                        crear_usuario(nuevo_nombre_usuario, clave_hasheada, rol_a_crear, id_sub, id_evento, id_usuario_actual)
                        registrar_accion(id_usuario_actual, f"CREACION_USUARIO_{rol_a_crear}", f"Usuario: {nuevo_nombre_usuario}")
                        st.success(f"Usuario {nuevo_nombre_usuario} registrado exitosamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al crear usuario: {e}")

    st.divider()

    # 2. Gestión de Usuarios Existentes (Lista con Acciones)
    st.subheader(f"Administración de {rol_a_crear}")
    
    with obtener_conexion() as conexion:
        # Nota: La tabla de grupos funcionales se llama 'catalog_eventos' en la DB real
        consulta = "SELECT u.*, e.nombre as evento_nombre FROM users u LEFT JOIN catalog_eventos e ON u.evento_id = e.id WHERE u.created_by = ? AND u.role = ?"
        df_usuarios = pd.read_sql_query(traducir_sql(consulta), conexion, params=[id_usuario_actual, rol_a_crear])
    
    if df_usuarios.empty:
        st.info(f"No hay usuarios {rol_a_crear} registrados.")
    else:
        for indice, registro in df_usuarios.iterrows():
            with st.container(border=True):
                color_estado = "green" if registro['is_active'] else "red"
                st.markdown(f"**Usuario:** {registro['username']} | **Estado:** <span style='color:{color_estado};'>{('ACTIVO' if registro['is_active'] else 'INACTIVO')}</span>", unsafe_allow_html=True)
                
                col_acc1, col_acc2 = st.columns(2)
                with col_acc1:
                    with st.popover("✏️ EDITAR"):
                        edit_nombre = st.text_input("Usuario", value=registro['username'], key=f"un_{registro['id']}")
                        edit_id_evento = registro['evento_id']
                        if rol_a_crear == 'RED':
                            df_ev = obtener_catalogo_eventos()
                            # Encontrar index actual
                            idx_actual = int(df_ev[df_ev['id'] == registro['evento_id']].index[0]) if registro['evento_id'] in df_ev['id'].values else 0
                            seleccion_ev = st.selectbox("Grupo Funcional", df_ev['nombre'], index=idx_actual, key=f"ev_{registro['id']}")
                            edit_id_evento = int(df_ev[df_ev['nombre'] == seleccion_ev]['id'].values[0])
                        
                        if st.button("Guardar Cambios", key=f"upd_{registro['id']}"):
                            actualizar_perfil_usuario(registro['id'], edit_nombre, id_evento=edit_id_evento, id_subregion=registro['subregion_id'])
                            registrar_accion(id_usuario_actual, "EDICION_PERFIL_USUARIO", f"ID: {registro['id']}")
                            st.rerun()

                with col_acc2:
                    with st.popover("🔐 RESET CLAVE"):
                        st.warning("Se restablecerá a la clave institucional: Nehemias2026*")
                        if st.button("Confirmar Reset", key=f"rst_{registro['id']}"):
                            nueva_hasheada = generar_hash_clave("Nehemias2026*")
                            restablecer_clave_usuario(registro['id'], nueva_hasheada)
                            registrar_accion(id_usuario_actual, "RESET_PASSWORD_USUARIO", f"ID: {registro['id']}")
                            st.success("Contraseña restablecida.")

                with col_acc3:
                    etiqueta = "🚫 DESACTIVAR" if registro['is_active'] else "✅ ACTIVAR"
                    if st.button(etiqueta, key=f"tog_{registro['id']}"):
                        alternar_estado_usuario(registro['id'], registro['is_active'])
                        st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)
