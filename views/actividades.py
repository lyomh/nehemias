import streamlit as st
import pandas as pd
from datetime import datetime
from database import (
    obtener_actividades_filtradas, 
    crear_actividad, 
    tomar_actividad,
    responder_actividad,
    cerrar_actividad,
    anular_actividad,
    obtener_subregiones,
    guardar_ajustes_lote,
    obtener_ajustes_por_actividad,
    guardar_gestion_granular,
    guardar_validacion_red,
    obtener_anos_disponibles
)

def vista_nueva_solicitud(id_usuario):
    """Módulo exclusivo para crear y lanzar nuevos lotes de ajustes."""
    st.markdown('<div class="stContainer">', unsafe_allow_html=True)
    st.markdown("### 📤 Lanzar Nuevo Lote")
    st.caption("Cargue el archivo consolidado de ajustes para asignarlo a una subregión.")
    
    with st.form("formulario_crear_actividad", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            titulo = st.text_input("📍 Título del Lote", placeholder="Ej: Ajustes Enero - Subregión Norte")
            descripcion = st.text_area("📝 Instrucciones Técnicas", placeholder="Instrucciones para el referente subregional...")
        with col2:
            df_sub = obtener_subregiones()
            seleccion_sub = st.selectbox("🎯 Subregión Destino", df_sub['nombre'])
            id_sub = int(df_sub[df_sub['nombre'] == seleccion_sub]['id'].values[0])
            archivo_cargado = st.file_uploader("📎 Base de Datos (.xlsx)", type=["xlsx"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        enviar = st.form_submit_button("🚀 DESPLEGAR SOLICITUD")
        
        if enviar:
            if not titulo: st.warning("El título es obligatorio para el seguimiento.")
            else:
                try:
                    id_actividad = crear_actividad(titulo, descripcion, id_sub, id_usuario)
                    if archivo_cargado:
                        df_ajustes = pd.read_excel(archivo_cargado)
                        guardar_ajustes_lote(id_actividad, df_ajustes)
                        st.toast(f"Lote '{titulo}' desplegado con éxito.", icon="✅")
                    else:
                        st.success(f"Solicitud '{titulo}' lanzada con éxito.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error en el despliegue: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

def vista_seguimiento_red(id_usuario, estados, titulo_panel):
    """Bandeja de seguimiento profesional para el nivel RED."""
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            anos = obtener_anos_disponibles()
            ano_actual = str(datetime.now().year)
            if not anos: anos = [ano_actual]
            sel_ano = st.selectbox("📅 Año Fiscal", anos, key=f"y_{titulo_panel}")
        with c2:
            meses = {"Todos": None, "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}
            sel_nombre_mes = st.selectbox("🗓️ Mes de Reporte", list(meses.keys()), key=f"m_{titulo_panel}")
            sel_mes = meses[sel_nombre_mes]
        with c3:
            df_sub = obtener_subregiones()
            opciones_sub = ["🌍 Todas las Subregiones"] + df_sub['nombre'].tolist()
            sel_nombre_sub = st.selectbox("📍 Territorio", opciones_sub, key=f"s_{titulo_panel}")
            sel_id_sub = None
            if sel_nombre_sub != "🌍 Todas las Subregiones":
                sel_id_sub = int(df_sub[df_sub['nombre'] == sel_nombre_sub]['id'].values[0])

    st.markdown("<br>", unsafe_allow_html=True)
    df_act = obtener_actividades_filtradas(rol_usuario='RED', id_usuario=id_usuario, estados=estados, ano=sel_ano, mes=sel_mes, id_subregion=sel_id_sub)
    
    if df_act.empty:
        st.info("No se encontraron registros.")
    else:
        for idx, fila in df_act.iterrows():
            mapa_estados = {'Activa': 'badge-activa', 'En Proceso': 'badge-revision', 'En Revisión': 'badge-revision', 'Cerrada': 'badge-cerrada', 'Anulada': 'badge-anulada'}
            clase_badge = mapa_estados.get(fila['status'], 'badge-activa')
            with st.container(border=True):
                h1, h2 = st.columns([3, 1])
                h1.markdown(f"#### {fila['titulo']}")
                h2.markdown(f'<div style="text-align: right;"><span class="badge {clase_badge}">{fila["status"].upper()}</span></div>', unsafe_allow_html=True)
                st.markdown(f"**Ubicación:** {fila['subregion_nombre']} | **Creada:** {fila['created_at']}")
                df_detalles = obtener_ajustes_por_actividad(fila['id'])
                if not df_detalles.empty:
                    with st.expander(f"📦 Ver Detalle ({len(df_detalles)} ajustes)"):
                        if fila['status'] == 'En Revisión':
                            st.markdown("---")
                            st.markdown("##### 🛡️ Auditoría Técnica Central")
                            cv1, cv2 = st.columns([2, 1])
                            with cv1: todo_cumplido = st.checkbox("🎯 Validar CUMPLIMIENTO TOTAL", key=f"todo_{fila['id']}")
                            with cv2:
                                if st.button("🚀 APLICAR VALIDACIÓN MASIVA", key=f"masiv_{fila['id']}"):
                                    if todo_cumplido: df_detalles['validacion_red'] = 'Cumplido'
                                    else:
                                        m = df_detalles['resultado_rs'] == 'Logrado'
                                        df_detalles.loc[m, 'validacion_red'] = 'Cumplido'
                                        df_detalles.loc[~m, 'validacion_red'] = 'Sin Cumplir'
                                    guardar_validacion_red(df_detalles); st.rerun()
                            df_editado = st.data_editor(
                                df_detalles, 
                                column_config={
                                    "id": None, "actividad_id": None, "status_ajuste": None,
                                    "validacion_red": st.column_config.SelectboxColumn(
                                        "Certificación RED", 
                                        options=["Pendiente", "Cumplido", "Sin Cumplir"], 
                                        required=True
                                    )
                                }, 
                                disabled=[c for c in df_detalles.columns if c != "validacion_red"], 
                                hide_index=True, 
                                key=f"red_edit_{fila['id']}", 
                                use_container_width=True
                            )
                            if st.button("💾 GUARDAR AUDITORÍA", key=f"guardar_red_{fila['id']}"): guardar_validacion_red(df_editado); st.rerun()
                        else:
                            # Mostrar todas las columnas relevantes ocultando solo IDs internos
                            columnas_ocultas = ["id", "actividad_id", "status_ajuste"]
                            st.dataframe(
                                df_detalles, 
                                column_config={c: None for c in columnas_ocultas},
                                use_container_width=True, 
                                hide_index=True
                            )
                if fila['status'] == 'En Revisión':
                    if st.button("✅ CERRAR SOLICITUD", key=f"cerrar_{fila['id']}"): cerrar_actividad(fila['id'], id_usuario); st.rerun()
                if fila['status'] in ['Activa', 'En Proceso', 'En Revisión']:
                    with st.expander("❌ Opciones de Anulación"):
                        motivo = st.text_input("Motivo", key=f"mot_{fila['id']}")
                        if st.button("🚨 CONFIRMAR ANULACIÓN", key=f"anular_{fila['id']}"): anular_actividad(fila['id'], motivo, id_usuario); st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)

def vista_listado_rs(id_usuario, id_subregion, estados, titulo_panel):
    """Bandeja de gestión para el nivel RS (Subregional)."""
    st.subheader(titulo_panel)
    if 'Historial' in titulo_panel:
        with st.container(border=True):
            ct1, ct2 = st.columns(2)
            anos = obtener_anos_disponibles()
            ano_act = str(datetime.now().year)
            if not anos: anos = [ano_act]
            sel_ano = ct1.selectbox("📅 Año", anos, key=f"yr_rs_{titulo_panel}")
            meses = {"Todos": None, "Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6, "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}
            sel_nombre_mes = ct2.selectbox("🗓️ Mes", list(meses.keys()), key=f"mr_rs_{titulo_panel}")
            sel_mes = meses[sel_nombre_mes]
    else:
        sel_ano, sel_mes = None, None

    df_act = obtener_actividades_filtradas(rol_usuario='RS', id_usuario=id_usuario, id_subregion=id_subregion, estados=estados, ano=sel_ano, mes=sel_mes)
    
    if df_act.empty:
        st.info("No hay actividades registradas en esta sección.")
    else:
        for idx, fila in df_act.iterrows():
            with st.container(border=True):
                st.markdown(f"#### {fila['titulo']}")
                st.caption(f"📅 Creada: {fila['created_at']} | 👤 Creador: {fila['creador_nombre']}")
                st.markdown(f"**Instrucciones:** {fila['descripcion'] or 'Revisar ajustes adjuntos.'}")
                
                df_ajustes = obtener_ajustes_por_actividad(fila['id'])
                if not df_ajustes.empty:
                    st.markdown("---")
                    es_editable = (fila['status'] == 'En Proceso')
                    df_editado = st.data_editor(
                        df_ajustes,
                        column_config={
                            "id": None, "actividad_id": None, "status_ajuste": None, "validacion_red": None,
                            "resultado_rs": st.column_config.SelectboxColumn("Resultado RS", options=["Pendiente", "Logrado", "No Logrado"], required=True),
                            "nota_tecnica": st.column_config.TextColumn("Nota"),
                            "evidencia_rs": st.column_config.TextColumn("Evidencia"),
                            "RegIniFec": st.column_config.TextColumn("RegIniFec", disabled=True)
                        },
                        disabled=True if not es_editable else [c for c in df_ajustes.columns if c not in ["resultado_rs", "nota_tecnica", "evidencia_rs"]],
                        hide_index=True, key=f"edit_rs_{fila['id']}", use_container_width=True
                    )
                    if es_editable:
                        if st.button("💾 GUARDAR AVANCE", key=f"guardar_rs_{fila['id']}"):
                            guardar_gestion_granular(df_editado); st.toast("Guardado."); st.rerun()
                
                if fila['status'] == 'Activa':
                    if st.button("🚀 TOMAR LOTE PARA TRABAJAR", key=f"tomar_rs_{fila['id']}"):
                        tomar_actividad(fila['id'], id_usuario); st.rerun()
                elif fila['status'] == 'En Proceso':
                    with st.form(f"formulario_rs_{fila['id']}"):
                        resp = st.text_area("Reporte Final Consolidado")
                        if st.form_submit_button("📦 ENVIAR A REVISIÓN DEPARTAMENTAL"):
                            if not resp: st.warning("Requerido.")
                            else: responder_actividad(fila['id'], resp, id_usuario); st.rerun()
                elif fila['status'] == 'En Revisión':
                    st.info("🕒 Esperando validación final por el Referente Departamental.")
            st.markdown("<br>", unsafe_allow_html=True)
