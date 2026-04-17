import streamlit as st
import pandas as pd
from database import obtener_catalogo_eventos, agregar_evento, actualizar_evento, eliminar_evento, registrar_accion

def vista_gestionar_eventos(id_usuario_actual):
    """Interfaz para que el ARD gestione el catálogo de Grupos Funcionales (Eventos)."""
    st.subheader("Gestión de Grupos Funcionales (Eventos)")
    st.write("Administre las categorías temáticas de vigilancia epidemiológica.")

    # 1. Formulario para añadir nuevo evento
    with st.expander("Añadir Nuevo Grupo Funcional"):
        with st.form("formulario_agregar_evento", clear_on_submit=True):
            nuevo_nombre = st.text_input("Nombre del Evento / Grupo")
            enviar = st.form_submit_button("REGISTRAR EVENTO")
            if enviar:
                if not nuevo_nombre:
                    st.warning("El nombre es obligatorio.")
                else:
                    try:
                        agregar_evento(nuevo_nombre)
                        registrar_accion(id_usuario_actual, "CREACION_EVENTO", f"Nombre: {nuevo_nombre}")
                        st.success(f"Evento '{nuevo_nombre}' añadido correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    st.divider()

    # 2. Lista de eventos con opciones de edición y eliminación
    df_eventos = obtener_catalogo_eventos()
    if df_eventos.empty:
        st.info("No hay eventos registrados en el catálogo.")
    else:
        for idx, fila in df_eventos.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(f"**{fila['nombre']}**")
                
                # Editar nombre
                with col2:
                    with st.popover("✏️ EDITAR"):
                        nombre_editado = st.text_input("Nuevo nombre", value=fila['nombre'], key=f"edit_{fila['id']}")
                        if st.button("Guardar Cambios", key=f"save_{fila['id']}"):
                            actualizar_evento(fila['id'], nombre_editado)
                            registrar_accion(id_usuario_actual, "EDICION_EVENTO", f"ID: {fila['id']} a {nombre_editado}")
                            st.rerun()
                
                # Eliminar evento
                with col3:
                    if st.button("🗑️ ELIMINAR", key=f"del_{fila['id']}"):
                        try:
                            eliminar_evento(fila['id'])
                            registrar_accion(id_usuario_actual, "ELIMINACION_EVENTO", f"ID: {fila['id']}")
                            st.rerun()
                        except ValueError as ve:
                            st.error(ve)
                        except Exception as e:
                            st.error(f"Error inesperado: {e}")
