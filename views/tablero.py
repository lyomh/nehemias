import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
from database import (
    obtener_conteos_estado, 
    obtener_productividad_eventos, 
    obtener_actividad_subregional, 
    obtener_anos_disponibles,
    obtener_resumen_ajustes,
    obtener_metricas_sla,
    obtener_subregiones,
    obtener_tendencia_mensual
)

def obtener_dias_calendario(ano_str, mes_int):
    """Calcula el número de días transcurridos en el periodo seleccionado."""
    ahora = datetime.now()
    ano = int(ano_str)
    
    # Si se selecciona un mes específico
    if mes_int:
        # Si es el mes actual del año actual, solo contar hasta hoy
        if ano == ahora.year and mes_int == ahora.month:
            return ahora.day
        # Si no, devolver los días completos del mes
        return calendar.monthrange(ano, mes_int)[1]
    
    # Si se selecciona "Todos" (Año completo)
    if ano == ahora.year:
        # Días transcurridos en el año actual hasta hoy
        return (ahora - datetime(ano, 1, 1)).days + 1
    
    # Año pasado completo
    return 366 if calendar.isleap(ano) else 365

def formatear_tiempo(dias):
    """Convierte una fracción de días en un formato legible (HH:MM:SS)."""
    if not dias or dias == 0: return "00:00:00"
    total_segundos = int(dias * 86400)
    horas = total_segundos // 3600
    minutos = (total_segundos % 3600) // 60
    segundos = total_segundos % 60
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

def vista_tablero(rol_usuario, id_usuario=None):
    """Tablero analítico profesional con enfoque en eficiencia y calidad técnica."""
    
    # 1. Filtros Estratégicos (Cabecera Superior)
    with st.container(border=True):
        st.markdown("### 🔍 Central de Análisis Situacional")
        cf1, cf2 = st.columns(2)
        with cf1:
            anos = obtener_anos_disponibles()
            ano_act = str(datetime.now().year)
            if not anos: anos = [ano_act]
            sel_ano = st.selectbox("📅 Período Anual", anos, index=anos.index(ano_act) if ano_act in anos else 0)
        with cf2:
            meses = {
                "Todos": None, "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, 
                "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9, 
                "Octubre": 10, "Noviembre": 11, "Diciembre": 12
            }
            sel_nombre_mes = st.selectbox("🗓️ Filtro Mensual", list(meses.keys()))
            sel_mes = meses[sel_nombre_mes]

        # 1.1 Filtro de Subregión (Solo para perfiles territoriales/auditores)
        if rol_usuario in ['ARD', 'ART', 'RED']:
            st.markdown("---")
            df_subs = obtener_subregiones()
            opciones_sub = ["Todas las Subregiones"] + df_subs['nombre'].tolist()
            sel_sub_nombre = st.selectbox("📍 Filtrar por Territorio Específico", opciones_sub)
            sel_id_sub = None
            if sel_sub_nombre != "Todas las Subregiones":
                sel_id_sub = int(df_subs[df_subs['nombre'] == sel_sub_nombre]['id'].values[0])
        else:
            sel_id_sub = None

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Métricas Macropas (Gestión Operativa)
    st.markdown("##### 📦 Gestión Operativa de Lotes")
    df_estado = obtener_conteos_estado(rol_usuario, id_usuario, ano=sel_ano, mes=sel_mes, id_subregion=sel_id_sub)
    conteos = {fila['status']: fila['total'] for _, fila in df_estado.iterrows()}
    
    c1, c2, c3, c4, c5 = st.columns(5)
    total_lotes = sum(conteos.values())
    c1.metric("Total Lotes", total_lotes)
    c2.metric("En Trabajo", conteos.get('En Proceso', 0) + conteos.get('Activa', 0))
    c3.metric("Cerrados", conteos.get('Cerrada', 0))
    c4.metric("Anulados", conteos.get('Anulada', 0))
    c5.metric("Calidad", f"{(conteos.get('Cerrada', 0)/total_lotes * 100):.1f}%" if total_lotes > 0 else "0%")

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Métricas Micro (Calidad Técnica Central)
    st.markdown("##### 🛡️ Calidad de Vigilancia (Auditoría RED)")
    df_resumen = obtener_resumen_ajustes(ano=sel_ano, mes=sel_mes, id_subregion=sel_id_sub)
    
    total_ajustes = df_resumen['total'].sum() if not df_resumen.empty else 0
    cumplidos_red = df_resumen[df_resumen['validacion_red'] == 'Cumplido']['total'].sum() if not df_resumen.empty else 0
    sin_cumplir_red = df_resumen[df_resumen['validacion_red'] == 'Sin Cumplir']['total'].sum() if not df_resumen.empty else 0
    
    auditados = cumplidos_red + sin_cumplir_red
    porcentaje_cumplimiento = (cumplidos_red / auditados * 100) if auditados > 0 else 0

    ca1, ca2, ca3, ca4, ca5 = st.columns(5)
    ca1.metric("Ajustes Totales", total_ajustes)
    ca2.metric("En Auditoría", auditados)
    ca3.metric("Cumplidos", cumplidos_red)
    ca4.metric("Sin Cumplir", sin_cumplir_red)
    ca5.metric("Porcentaje Cumplimiento", f"{porcentaje_cumplimiento:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Gráficos de Análisis Avanzado
    st.markdown("##### 📊 Análisis de Desempeño")
    g_col1, g_col2 = st.columns(2)
    
    with g_col1:
        with st.container(border=True):
            st.markdown("**Resultado de Auditoría Técnica**")
            if not df_resumen.empty:
                df_grafico = df_resumen.groupby('validacion_red')['total'].sum().reset_index()
                st.bar_chart(df_grafico.set_index('validacion_red'), color="#018d38")
            else:
                st.info("Sin registros auditados en el período.")
    
    with g_col2:
        if rol_usuario in ['ARD', 'ART']:
            with st.container(border=True):
                st.markdown("**Carga de Trabajo Territorial**")
                df_sub = obtener_actividad_subregional(ano=sel_ano, mes=sel_mes)
                if not df_sub.empty:
                    st.bar_chart(df_sub.set_index('subregion'), color="#3561ab")
                else:
                    st.info("No hay datos territoriales disponibles.")

    if rol_usuario in ['ARD', 'RED', 'ART']:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("**Productividad por Grupo Funcional (Vigilancia)**")
            df_prod = obtener_productividad_eventos(ano=sel_ano, mes=sel_mes, id_subregion=sel_id_sub)
            if not df_prod.empty:
                st.bar_chart(df_prod.set_index('evento'), color="#f28e18")
            else:
                st.info("Datos de productividad no encontrados.")

    # 5. Métricas de Oportunidad y SLA
    st.divider()
    st.markdown("##### 📉 Análisis de Oportunidad y SLA (Tiempos de Respuesta)")
    df_sla = obtener_metricas_sla(ano=sel_ano, mes=sel_mes, id_subregion=sel_id_sub)
    
    if not df_sla.empty:
        cs1, cs2, cs3 = st.columns(3)
        prom_reaccion = df_sla['dias_reaccion'].mean()
        prom_gestion = df_sla['dias_gestion'].mean()
        prom_auditoria = df_sla['dias_auditoria'].mean()
        
        cs1.metric("Prom. Reacción", formatear_tiempo(prom_reaccion), help="Tiempo promedio desde carga hasta toma RS")
        cs2.metric("Prom. Gestión", formatear_tiempo(prom_gestion), help="Tiempo promedio de resolución técnica")
        cs3.metric("Prom. Auditoría", formatear_tiempo(prom_auditoria), help="Tiempo promedio desde respuesta hasta cierre RED")
        
        # --- NUEVAS MÉTRICAS DE PRODUCTIVIDAD ---
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### ⚡ Indicadores de Productividad Ponderada")
        cp1, cp2, cp3 = st.columns(3)
        
        # Calcular totales para métricas globales
        registros_totales = df_sla['total_registros'].sum()
        tiempo_gestion_total = df_sla['dias_gestion'].sum()
        
        # 1. Productividad del Periodo (Bruta - Incluye tiempos muertos)
        dias_periodo = obtener_dias_calendario(sel_ano, sel_mes)
        prod_periodo = registros_totales / dias_periodo if dias_periodo > 0 else 0
        cp1.metric(
            "Productividad del Periodo", 
            f"{prod_periodo:.1f} reg/día", 
            help=f"Rendimiento real sobre los {dias_periodo} días del calendario (incluye tiempos sin actividad)."
        )
        
        # 2. Velocidad de Procesamiento (Neta - Solo tiempo de trabajo)
        velocidad = (registros_totales / tiempo_gestion_total) if tiempo_gestion_total > 0 else 0
        cp2.metric(
            "Velocidad de Procesamiento", 
            f"{velocidad:.1f} reg/día", 
            help="Agilidad del equipo mientras tuvo el lote en sus manos (tiempo neto de gestión)."
        )
        
        # 3. Esfuerzo Unitario
        segundos_totales = tiempo_gestion_total * 86400
        intensidad = (segundos_totales / registros_totales) if registros_totales > 0 else 0
        txt_intensidad = f"{intensidad:.1f} seg/reg" if intensidad < 60 else f"{intensidad/60:.1f} min/reg"
        cp3.metric(
            "Esfuerzo Unitario", 
            txt_intensidad, 
            help="Tiempo promedio invertido en cada ajuste certificado como Cumplido."
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Desempeño Cronológico por Subregión (Días)**")
        df_sla_view = df_sla.set_index('subregion')[['dias_reaccion', 'dias_gestion', 'dias_auditoria']]
        df_sla_view.columns = ['Reacción (RED->RS)', 'Gestión (RS)', 'Auditoría (RS->RED)']
        st.bar_chart(df_sla_view)
        
        with st.expander("Ver detalle de métricas por subregión"):
            # Preparar un DF amigable para el usuario
            df_detalle = df_sla.copy()
            df_detalle['productividad'] = (df_detalle['total_registros'] / df_detalle['dias_gestion']).round(1)
            df_detalle['seg_por_ajuste'] = ((df_detalle['dias_gestion'] * 86400) / df_detalle['total_registros']).round(1)
            st.dataframe(df_detalle, use_container_width=True, hide_index=True)

        # --- NUEVO MÓDULO: TENDENCIA ANUAL (Solo si sel_mes es None) ---
        if sel_mes is None:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("##### 📈 Evolución Mensual de la Calidad (Ajustes Cumplidos)")
                df_tendencia = obtener_tendencia_mensual(sel_ano, id_subregion=sel_id_sub)
                if not df_tendencia.empty:
                    # Preparar datos para el gráfico
                    st.area_chart(df_tendencia.set_index('mes')['total'], color="#007bff")
                    st.caption(f"Visualización de la carga técnica resuelta mes a mes durante el año {sel_ano}.")
                else:
                    st.info("Aún no hay datos históricos suficientes para mostrar la tendencia anual.")
    else:
        st.info("No hay suficientes lotes cerrados con traza completa para calcular el SLA en este periodo.")
