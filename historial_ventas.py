import streamlit as st
import pandas as pd
from datetime import datetime
import os

def mostrar_modulo_historial_ventas(ruta_negocio):
    st.markdown("### 📚 Historial de Documentos y Ventas Emitidas")
    st.markdown("📌 **Archivo General:** Explora el registro histórico con filtros avanzados por tipo de documento, cliente, fechas y estados.")

    # Detecta automáticamente el libro del mes (ej: Libro_Ventas_2026_08.xlsx)
    mes_actual = datetime.now().strftime("%Y_%m")
    nombre_archivo = f"Libro_Ventas_{mes_actual}.xlsx"
    archivo_ventas = os.path.join(ruta_negocio, nombre_archivo)

    if not os.path.exists(archivo_ventas):
        archivo_ventas = os.path.join(ruta_negocio, "Ventas_Diarias.xlsx")

    if not os.path.exists(archivo_ventas):
        st.warning(f"⚠️ No se encontró el archivo de ventas ({nombre_archivo}) para este negocio.")
        return

    try:
        df_ventas = pd.read_excel(archivo_ventas)
    except Exception as e:
        st.error(f"Error al leer el archivo de registros: {e}")
        return

    if df_ventas.empty:
        st.info("ℹ️ El historial de ventas está vacío actualmente.")
        return

    # Pestañas de navegación
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
        busqueda_libre = st.text_input("🔎 Buscar palabra clave", value="")
    with col_f2:
        limite_filas = st.slider("📄 Mostrar registros", min_value=10, max_value=500, value=50, step=10, format="%d")

    df_filtrado = df_ventas.copy()
    if busqueda_libre:
        mask = df_filtrado.astype(str).apply(lambda x: x.str.contains(busqueda_libre, case=False, na=False)).any(axis=1)
        df_filtrado = df_filtrado[mask]

    with tab_gen:
        st.dataframe(df_filtrado.tail(limite_filas), use_container_width=True)

    with tab_doc:
        col_doc = next((c for c in df_ventas.columns if 'tipo' in c.lower() or 'documento' in c.lower()), None)
        if col_doc:
            tipos = ["Todos"] + df_ventas[col_doc].dropna().unique().tolist()
            sel = st.selectbox("Tipo de Documento", options=tipos)
            df_d = df_filtrado.copy()
            if sel != "Todos": df_d = df_d[df_d[col_doc] == sel]
            st.dataframe(df_d.tail(limite_filas), use_container_width=True)
        else:
            st.dataframe(df_filtrado.tail(limite_filas), use_container_width=True)

    with tab_cli:
        col_cli = next((c for c in df_ventas.columns if 'cliente' in c.lower() or 'razon' in c.lower() or 'nombre' in c.lower()), None)
        if col_cli:
            clientes = ["Todos"] + df_ventas[col_cli].dropna().unique().tolist()
            sel_c = st.selectbox("Cliente", options=clientes)
            df_c = df_filtrado.copy()
            if sel_c != "Todos": df_c = df_c[df_c[col_cli] == sel_c]
            st.dataframe(df_c.tail(limite_filas), use_container_width=True)
        else:
            st.dataframe(df_filtrado.tail(limite_filas), use_container_width=True)

    with tab_pag:
        col_pag = next((c for c in df_ventas.columns if 'estado' in c.lower() or 'pago' in c.lower() or 'condicion' in c.lower()), None)
        if col_pag:
            estados = ["Todos"] + df_ventas[col_pag].dropna().unique().tolist()
            sel_p = st.selectbox("Estado de Pago", options=estados)
            df_p = df_filtrado.copy()
            if sel_p != "Todos": df_p = df_p[df_p[col_pag] == sel_p]
            st.dataframe(df_p.tail(limite_filas), use_container_width=True)
        else:
            st.dataframe(df_filtrado.tail(limite_filas), use_container_width=True)

    st.divider()
    st.download_button(
        label="📥 Descargar Reporte Filtrado en Excel",
        data=df_filtrado.to_excel(index=False),
        file_name="Historial_Documentos_Filtrado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )