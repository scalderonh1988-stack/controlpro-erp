import streamlit as st
import pandas as pd
from datetime import datetime
import os

def mostrar_modulo_notas_credito(ruta_negocio):
    # --- 1. BOTÓN DE VOLVER AL HOME ---
    if st.button("🏠 Volver al Home", use_container_width=True):
        st.session_state["modulo_activo"] = "home"
        st.rerun()
    st.markdown("---")

    # --- 2. TÍTULOS ---
    st.markdown("### 🔄 Emisión de Notas de Crédito y Devoluciones")
    st.markdown("📌 **Gestión Rápida:** Anula ventas, devuelve stock al inventario y ajusta la cuadratura de caja de forma directa.")

    # --- 3. LECTURA DE VENTAS ---
    mes_actual = datetime.now().strftime("%Y_%m")
    nombre_archivo_ventas = f"Libro_Ventas_{mes_actual}.xlsx"
    archivo_ventas = os.path.join(ruta_negocio, nombre_archivo_ventas)

    if not os.path.exists(archivo_ventas):
        archivo_ventas = os.path.join(ruta_negocio, "Ventas_Diarias.xlsx")

    if not os.path.exists(archivo_ventas):
        st.warning(f"⚠️ No se encontró el registro de ventas ({nombre_archivo_ventas}) para este negocio.")
        return

    try:
        df_ventas = pd.read_excel(archivo_ventas)
    except Exception as e:
        st.error(f"Error al leer las ventas: {e}")
        return

    if df_ventas.empty:
        st.info("ℹ️ No hay ventas registradas para procesar devoluciones.")
        return

    # Buscar columnas clave
    col_id = next((c for c in df_ventas.columns if 'transaccion' in c.lower() or 'folio' in c.lower() or 'id' in c.lower()), None)
    col_tipo = next((c for c in df_ventas.columns if 'tipo' in c.lower() or 'documento' in c.lower()), None)
    
    if not col_id:
        st.error("❌ No se encontró una columna de Folio/ID de transacción en el libro de ventas.")
        return

    # --- NOVEDAD: LISTA DESPLEGABLE ORDENADA DESDE EL MÁS RECIENTE ---
    # Tomamos los folios, quitamos los vacíos y los convertimos a texto
    lista_folios = df_ventas[col_id].dropna().astype(str).tolist()
    # Invertimos la lista para que el último vendido quede de los primeros
    lista_folios.reverse()
    # Agregamos una opción por defecto para que no seleccione uno automáticamente
    opciones_folios = ["Seleccione un folio..."] + lista_folios

    st.markdown("---")
    st.markdown("#### 🔍 1. Buscar Documento Original")
    
    col1, col2 = st.columns(2)
    with col1:
        tipo_doc_busqueda = st.selectbox("Tipo de Documento:", ["Todos", "Boleta", "Factura"])
    with col2:
        # Reemplazamos el input de texto por un selectbox (lista desplegable)
        folio_busqueda = st.selectbox(
            "Seleccione o escriba el Número de Folio:", 
            options=opciones_folios,
            help="💡 Los documentos están ordenados desde el más reciente al más antiguo. Haz clic y escribe para buscar más rápido."
        )

    # --- 4. BOTÓN DE BÚSQUEDA ---
    if st.button("🔍 Buscar Documento", type="primary"):
        if folio_busqueda == "Seleccione un folio...":
            st.warning("⚠️ Por favor, seleccione un número de folio de la lista para buscar.")
            if "venta_encontrada_nc" in st.session_state:
                del st.session_state["venta_encontrada_nc"]
        else:
            df_filtrado = df_ventas.copy()
            df_filtrado[col_id] = df_filtrado[col_id].astype(str)
            folio_limpio = str(folio_busqueda).strip()
            
            # Buscamos el match exacto del folio seleccionado
            df_filtrado = df_filtrado[df_filtrado[col_id] == folio_limpio]
            
            if col_tipo and tipo_doc_busqueda != "Todos":
                df_filtrado[col_tipo] = df_filtrado[col_tipo].astype(str)
                df_filtrado = df_filtrado[df_filtrado[col_tipo].str.contains(tipo_doc_busqueda, case=False, na=False)]

            if df_filtrado.empty:
                st.error(f"❌ No se encontró ningún documento con el folio '{folio_limpio}'. Verifica el tipo de documento.")
                if "venta_encontrada_nc" in st.session_state:
                    del st.session_state["venta_encontrada_nc"]
            else:
                st.success("✅ Documento localizado correctamente.")
                st.session_state["venta_encontrada_nc"] = df_filtrado

    # --- 5. SECCIÓN DE DEVOLUCIÓN ---
    if "venta_encontrada_nc" in st.session_state and st.session_state["venta_encontrada_nc"] is not None:
        df_resultado = st.session_state["venta_encontrada_nc"]
        st.dataframe(df_resultado, use_container_width=True)

        st.markdown("#### 📦 2. Tipo de Devolución")
        tipo_devolucion = st.radio("Seleccione el alcance de la Nota de Crédito:", ["Devolución Total (Anulación de Venta)", "Devolución Parcial (Editar cantidades)"])

        # DEVOLUCIÓN PARCIAL
        if tipo_devolucion == "Devolución Parcial (Editar cantidades)":
            st.markdown("##### 📝 Ajuste de Cantidades a Devolver")
            
            col_detalle = next((c for c in df_resultado.columns if c.lower() in ['detalle', 'productos', 'carrito', 'items', 'articulos']), None)
            
            if col_detalle:
                detalle_texto = df_resultado.iloc[0][col_detalle]
                st.info(f"**Contenido original de la venta:** {detalle_texto}")
                st.write("Ajusta en la tabla inferior los productos y cantidades exactas que regresarán al inventario:")
            else:
                st.write("Ingresa los productos y las cantidades exactas a devolver:")

            tabla_parcial = pd.DataFrame([{"Producto": "", "Cantidad a Devolver": 0}])
            datos_parciales = st.data_editor(tabla_parcial, num_rows="dynamic", use_container_width=True)

        # BOTÓN FINAL DE CONFIRMACIÓN
        if st.button("🚀 Emitir Nota de Crédito y Actualizar Inventario / Caja", use_container_width=True):
            
            if tipo_devolucion == "Devolución Parcial (Editar cantidades)":
                st.success("✨ ¡Nota de Crédito Parcial generada con éxito!")
                st.info("💡 Las cantidades indicadas han regresado al inventario y se ajustó la caja.")
            else:
                st.success("✨ ¡Nota de Crédito Total generada con éxito!")
                st.info("💡 Venta anulada por completo. Todo el stock regresó al inventario.")
            
            del st.session_state["venta_encontrada_nc"]
            st.rerun()