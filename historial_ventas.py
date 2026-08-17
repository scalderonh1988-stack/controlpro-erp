import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

def mostrar_modulo_historial_ventas(ruta_negocio):
    st.markdown("### 📚 Historial de Documentos y Ventas Emitidas")
    st.markdown("📌 **Archivo General:** Explora el registro histórico con filtros avanzados, tipos de documento y descarga de comprobantes individuales.")

    # Detectar automáticamente el libro de ventas del mes actual
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

    # Normalizar columnas de fecha si existen
    if 'Fecha' in df_ventas.columns:
        df_ventas['Fecha_dt'] = pd.to_datetime(df_ventas['Fecha'], errors='coerce')

    # 📂 PESTAÑAS DE NAVEGACIÓN
    tab_gen, tab_doc, tab_cli, tab_pag, tab_comprobante = st.tabs([
        "📂 Vista General", 
        "📄 Por Tipo de Documento", 
        "👤 Por Cliente", 
        "💳 Estado de Pago",
        "🖨️ Descargar Comprobante / Factura"
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
            tipos_disponibles = ["Todos"] + df_ventas[col_doc].dropna().unique().tolist()
            doc_seleccionado = st.selectbox("Seleccione el Tipo de Documento", options=tipos_disponibles)
            
            df_doc = df_filtrado.copy()
            if doc_seleccionado != "Todos":
                df_doc = df_doc[df_doc[col_doc] == doc_seleccionado]
            st.dataframe(df_doc.tail(limite_filas), use_container_width=True)
        else:
            st.info("ℹ️ No se detectó una columna específica de 'Tipo de Documento'.")
            st.dataframe(df_filtrado.tail(limite_filas), use_container_width=True)

    with tab_cli:
        st.markdown("#### 👤 Filtrar por Cliente")
        col_cli = next((c for c in df_ventas.columns if 'cliente' in c.lower() or 'razon' in c.lower() or 'nombre' in c.lower()), None)
        if col_cli:
            clientes_disponibles = ["Todos"] + df_ventas[col_cli].dropna().unique().tolist()
            cli_seleccionado = st.selectbox("Seleccione el Cliente", options=clientes_disponibles)
            
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
            estados_disponibles = ["Todos"] + df_ventas[col_pag].dropna().unique().tolist()
            pag_seleccionado = st.selectbox("Seleccione el Estado de Pago", options=estados_disponibles)
            
            df_pag = df_filtrado.copy()
            if pag_seleccionado != "Todos":
                df_pag = df_pag[df_pag[col_pag] == pag_seleccionado]
            st.dataframe(df_pag.tail(limite_filas), use_container_width=True)
        else:
            st.info("ℹ️ No se detectó una columna específica de 'Estado de Pago'.")
            st.dataframe(df_filtrado.tail(limite_filas), use_container_width=True)

    with tab_comprobante:
        st.markdown("#### 🖨️ Búsqueda y Descarga de Comprobante Individual")
        st.markdown("Ingresa o selecciona el ID de Transacción (ej. `TX_20260806172451`) para obtener el detalle exacto.")
        
        # Detectar columna de ID de transacción o folio
        col_id = next((c for c in df_ventas.columns if 'transaccion' in c.lower() or 'folio' in c.lower() or 'id' in c.lower()), None)
        
        if col_id:
            lista_ids = df_ventas[col_id].dropna().astype(str).tolist()
            id_elegido = st.selectbox("Seleccione el ID de Transacción", options=lista_ids)
            
            if id_elegido:
                # Filtrar la fila de esa venta específica
                fila_venta = df_ventas[df_ventas[col_id].astype(str) == id_elegido]
                
                if not fila_venta.empty:
                    st.success("✅ ¡Transacción encontrada con éxito!")
                    st.dataframe(fila_venta, use_container_width=True)
                    
                    # Generar texto resumen tipo comprobante para descargar como archivo de texto/factura simple
                    detalle_texto = "=== COMPROBANTE DE VENTA / FACTURA ===\n\n"
                    for col in fila_venta.columns:
                        detalle_texto += f"{col}: {fila_venta.iloc[0][col]}\n"
                    
                    st.download_button(
                        label=f"📥 Descargar Comprobante ({id_elegido})",
                        data=detalle_texto,
                        file_name=f"Comprobante_{id_elegido}.txt",
                        mime="text/plain"
                    )
        else:
            st.warning("⚠️ No se encontró una columna de ID de Transacción o Folio en el archivo de ventas.")

    # Botón global de descarga del reporte general
    st.divider()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_filtrado.to_excel(writer, index=False)
    excel_data = output.getvalue()

    st.download_button(
        label="📥 Descargar Reporte General Filtrado en Excel",
        data=excel_data,
        file_name="Historial_Documentos_Filtrado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )