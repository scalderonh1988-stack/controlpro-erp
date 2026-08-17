import streamlit as st
import pandas as pd
from datetime import date
import os

def mostrar_modulo_historial_ventas(ruta_negocio):
    st.markdown("### 📚 Historial de Documentos y Ventas Emitidas")
    st.markdown("📌 **Archivo General:** Explora el registro histórico con filtros avanzados por tipo de documento, cliente, fechas y estados.")

    # Archivo base de ventas
    archivo_ventas = os.path.join(ruta_negocio, "Ventas_Diarias.xlsx")
    if not os.path.exists(archivo_ventas):
        archivo_ventas = os.path.join(ruta_negocio, "Libro_Ventas_2026_07.xlsx")

    if not os.path.exists(archivo_ventas):
        st.warning("⚠️ No se encontró un archivo de ventas activo para este negocio.")
        return

    try:
        df_ventas = pd.read_excel(archivo_ventas)
    except Exception as e:
        st.error(f"Error al leer el archivo de registros: {e}")
        return

    if df_ventas.empty:
        st.info("ℹ️ El historial de ventas está vacío actualmente.")
        return

    # Normalizar columnas de fecha si existen
    if 'Fecha' in df_ventas.columns:
        df_ventas['Fecha_dt'] = pd.to_datetime(df_ventas['Fecha'], errors='coerce')

    # 📂 PESTAÑAS O CARPETAS DE NAVEGACIÓN
    tab_gen, tab_doc, tab_cli, tab_pag = st.tabs([
        "📂 Vista General", 
        "📄 Por Tipo de Documento", 
        "👤 Por Cliente", 
        "💳 Estado de Pago"
    ])

    st.markdown("---")
    st.markdown("#### 🔍 Panel de Filtros Dinámicos")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        busqueda_libre = st.text_input("🔎 Buscar palabra clave (folio, producto, etc.)", value="")
    with col_f2:
        limite_filas = st.slider("📄 Mostrar cantidad máxima de registros", min_value=10, max_value=500, value=50, step=10, format="%d")

    # Filtrado base por texto libre
    df_filtrado = df_ventas.copy()
    if busqueda_libre:
        mask = df_filtrado.astype(str).apply(lambda x: x.str.contains(busqueda_libre, case=False, na=False)).any(axis=1)
        df_filtrado = df_filtrado[mask]

    with tab_gen:
        st.markdown("#### 📋 Todos los Documentos Emitidos")
        st.dataframe(df_filtrado.tail(limite_filas), use_container_width=True)

    with tab_doc:
        st.markdown("#### 📄 Filtrar por Tipo de Documento")
        col_doc = next((c for c in df_ventas.columns if 'tipo' in c.lower() or 'documento' in c.lower()), None)
        if col_doc:
            tipos_disponibles = df_ventas[col_doc].dropna().unique().tolist()
            doc_seleccionado = st.selectbox("Seleccione el Tipo de Documento", options=["Todos"] + tipos_disponibles)
            
            df_doc = df_filtrado.copy()
            if doc_seleccionado != "Todos":
                df_doc = df_doc[df_doc[col_doc] == doc_seleccionado]
            st.dataframe(df_doc.tail(limite_filas), use_container_width=True)
        else:
            st.info("ℹ️ No se detectó una columna específica de 'Tipo de Documento'. Mostrando vista general.")
            st.dataframe(df_filtrado.tail(limite_filas), use_container_width=True)

    with tab_cli:
        st.markdown("#### 👤 Filtrar por Cliente")
        col_cli = next((c for c in df_ventas.columns if 'cliente' in c.lower() or 'razon' in c.lower() or 'nombre' in c.lower()), None)
        if col_cli:
            clientes_disponibles = df_ventas[col_cli].dropna().unique().tolist()
            cli_seleccionado = st.selectbox("Seleccione el Cliente", options=["Todos"] + clientes_disponibles)
            
            df_cli = df_filtrado.copy()
            if cli_seleccionado != "Todos":
                df_cli = df_cli[df_cli[col_cli] == cli_seleccionado]
            st.dataframe(df_cli.tail(limite_filas), use_container_width=True)
        else:
            st.info("ℹ️ No se detectó una columna específica de 'Cliente'.")
            st.dataframe(df_filtrado.tail(limite_filas), use_container_width=True)

    with tab_pag:
        st.markdown("#### 💳 Filtrar por Estado de Pago")
        col_pag = next((c for c in df_ventas.columns if 'estado' in c.lower() or 'pago' in c.lower() or 'condicion' in c.lower()), None)
        if col_pag:
            estados_disponibles = df_ventas[col_pag].dropna().unique().tolist()
            pag_seleccionado = st.selectbox("Seleccione el Estado de Pago", options=["Todos"] + estados_disponibles)
            
            df_pag = df_filtrado.copy()
            if pag_seleccionado != "Todos":
                df_pag = df_pag[df_pag[col_pag] == pag_seleccionado]
            st.dataframe(df_pag.tail(limite_filas), use_container_width=True)
        else:
            st.info("ℹ️ No se detectó una columna específica de 'Estado de Pago'.")
            st.dataframe(df_filtrado.tail(limite_filas), use_container_width=True)

    # Botón global de descarga
    st.divider()
    st.download_button(
        label="📥 Descargar Reporte Filtrado en Excel",
        data=df_filtrado.to_excel(index=False),
        file_name="Historial_Documentos_Filtrado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )