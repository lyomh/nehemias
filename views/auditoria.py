import streamlit as st
import pandas as pd
from database import obtener_conexion, traducir_sql

def vista_auditoria():
    """Interfaz para visualizar logs de auditoría (Regla de Trazabilidad)."""
    st.subheader("🕵️ Troncal de Auditoría")
    st.write("Registro histórico de acciones críticas realizadas en el sistema.")
    
    with obtener_conexion() as conexion:
        consulta = """
            SELECT l.id, u.username as usuario, l.accion, l.detalle, l.timestamp as fecha_hora
            FROM logs_auditoria l
            LEFT JOIN users u ON l.user_id = u.id
            ORDER BY l.timestamp DESC
            LIMIT 100
        """
        df = pd.read_sql_query(traducir_sql(consulta), conexion)
    
    if df.empty:
        st.info("No hay registros de auditoría todavía.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
