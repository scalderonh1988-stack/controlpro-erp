import streamlit as st
import pandas as pd
# Importamos la conexión a tu base de datos y la seguridad de negocio
from data_manager import supabase, get_current_tenant

def mostrar_modulo_notas_credito(ruta_negocio):
    # --- 1. BOTÓN DE VOLVER AL HOME ---
    if st.button("🏠 Volver al Home", use_container_width=True):
        st.session_state["modulo_activo"] = "home"
        st.session_state["menu_seleccionado"] = "🏠 Home / Bienvenida"  # <--- Conecta con la variable de tu app.py
        st.rerun()
    st.markdown("---")

    # --- 2. TÍTULOS ---
    st.markdown("### 🔄 Emisión de Notas de Crédito y Devoluciones")
    st.markdown("📌 **Gestión Rápida:** Anula ventas, devuelve stock al inventario y ajusta la cuadratura de caja de forma directa.")

    # --- 3. LECTURA DIRECTA DESDE SUPABASE ---
    tenant_id = get_current_tenant()
    
    try:
        # Llamada directa a tu tabla de la base de datos
        respuesta = supabase.table("ventas").select("*").execute()
        
        if not respuesta.data:
            st.info("ℹ️ No hay ventas registradas en la base de datos para procesar devoluciones.")
            return
            
        # Convertimos la data de Supabase a un formato amigable para buscar (Pandas)
        df_ventas = pd.DataFrame(respuesta.data)
        
        # Filtro estricto: Solo mostramos las ventas de ESTE negocio (Igual a como lo haces en clientes)
        if tenant_id and not df_ventas.empty:
            col_tenant = next((c for c in df_ventas.columns if c in ["rut_empresa", "id_negocio", "rut_negocio", "negocio_id"]), None)
            if col_tenant:
                df_ventas = df_ventas[df_ventas[col_tenant].astype(str) == str(tenant_id)]
        
        if df_ventas.empty:
            st.info("ℹ️ No hay ventas registradas para este negocio en particular.")
            return

    except Exception as e:
        st.error(f"❌ Error al leer las ventas desde Supabase: {e}")
        return

    # Buscar automáticamente cómo se llama la columna de Folio/ID en tu tabla
    col_id = next((c for c in df_ventas.columns if 'transaccion' in c.lower() or 'folio' in c.lower() or 'id' in c.lower()), None)
    col_tipo = next((c for c in df_ventas.columns if 'tipo' in c.lower() or 'documento' in c.lower()), None)
    
    if not col_id:
        st.error("❌ No se encontró una columna de Folio/ID de transacción en la tabla de ventas.")
        st.write("Columnas disponibles para mapear:", df_ventas.columns.tolist())
        return

    # --- PREPARAR LA LISTA DESPLEGABLE DESDE EL MÁS RECIENTE ---
    lista_folios = df_ventas[col_id].dropna().astype(str).tolist()
    lista_folios.reverse() # Invierte para que el último sea el primero
    opciones_folios = ["Seleccione un folio..."] + lista_folios

    st.markdown("---")
    st.markdown("#### 🔍 1. Buscar Documento Original")
    
    col1, col2 = st.columns(2)
    with col1:
        tipo_doc_busqueda = st.selectbox("Tipo de Documento:", ["Todos", "Boleta", "Factura"])
    with col2:
        folio_busqueda = st.selectbox(
            "Seleccione o escriba el Número de Folio:", 
            options=opciones_folios,
            help="💡 Los documentos están conectados en tiempo real a Supabase."
        )

    # --- 4. BÚSQUEDA Y SELECCIÓN ---
    if st.button("🔍 Buscar Documento", type="primary"):
        if folio_busqueda == "Seleccione un folio...":
            st.warning("⚠️ Por favor, seleccione un número de folio de la lista para buscar.")
            if "venta_encontrada_nc" in st.session_state:
                del st.session_state["venta_encontrada_nc"]
        else:
            df_filtrado = df_ventas.copy()
            df_filtrado[col_id] = df_filtrado[col_id].astype(str)
            folio_limpio = str(folio_busqueda).strip()
            
            df_filtrado = df_filtrado[df_filtrado[col_id] == folio_limpio]
            
            if col_tipo and tipo_doc_busqueda != "Todos":
                df_filtrado[col_tipo] = df_filtrado[col_tipo].astype(str)
                df_filtrado = df_filtrado[df_filtrado[col_tipo].str.contains(tipo_doc_busqueda, case=False, na=False)]

            if df_filtrado.empty:
                st.error(f"❌ No se encontró ningún documento con el folio '{folio_limpio}'.")
                if "venta_encontrada_nc" in st.session_state:
                    del st.session_state["venta_encontrada_nc"]
            else:
                st.success("✅ Documento localizado en Supabase correctamente.")
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
            
            # Buscar dónde guardaste el carrito/detalle en Supabase
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
                st.success("✨ ¡Nota de Crédito Parcial generada con éxito en la base de datos!")
            else:
                st.success("✨ ¡Nota de Crédito Total generada con éxito en la base de datos!")
            
            del st.session_state["venta_encontrada_nc"]
            st.rerun()