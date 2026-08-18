import streamlit as st
import pandas as pd
from datetime import datetime
# Importamos la conexión a tu base de datos y la seguridad de negocio
from data_manager import supabase, get_current_tenant

def mostrar_modulo_compras(ruta_negocio):
    st.markdown("### 🛒 Módulo de Recepción de Compras (GRC) y Control de Lotes")
    st.markdown("Registra las facturas o guías de tus proveedores. El sistema sumará el stock, recalculará el Costo Promedio Ponderado (CPP) y creará el registro de compras.")

    tenant_id = get_current_tenant()
    if not tenant_id:
        st.error("❌ No se ha identificado el negocio. Por favor, inicia sesión nuevamente.")
        return

    # --- 1. LECTURA DE DATOS MAESTROS DESDE SUPABASE ---
    try:
        # Cargar Proveedores
        res_prov = supabase.table("proveedores").select("nombre").eq("rut_empresa", str(tenant_id)).execute()
        lista_proveedores = [p["nombre"] for p in res_prov.data] if res_prov.data else ["Proveedor General"]
        
        # Cargar Productos
        res_prod = supabase.table("productos").select("*").eq("rut_empresa", str(tenant_id)).execute()
        df_base = pd.DataFrame(res_prod.data) if res_prod.data else pd.DataFrame()
        codigos_disponibles = df_base['codigo'].astype(str).tolist() if not df_base.empty else []
    except Exception as e:
        st.error(f"❌ Error al conectar con los maestros en Supabase: {e}")
        lista_proveedores = ["Proveedor General"]
        codigos_disponibles = []
        df_base = pd.DataFrame()

    st.divider()
    st.markdown("#### 📄 1. Cabecera del Documento de Compra")
   
    col_h1, col_h2, col_h3 = st.columns(3)
    with col_h1:
        proveedor_factura = st.selectbox("Nombre del Proveedor", options=lista_proveedores)
        tipo_recepcion = st.selectbox("Tipo de Recepción", ["Factura Electrónica", "Guía de Despacho", "Boleta", "Otro"])
    with col_h2:
        num_factura = st.text_input("Número de Documento (Factura/Guía)", value="FAC-001")
        fecha_emision = st.date_input("Fecha de Emisión / Compra", value=datetime.today())
    with col_h3:
        condicion_pago = st.selectbox("Condición de Pago", ["Contado", "Crédito", "Cheque"])
        fecha_vencimiento_factura = st.date_input("Vencimiento del Pago (si es Crédito)", value=datetime.today())

    st.divider()
    st.markdown("#### 📦 2. Agregar Productos al Documento")
   
    # Usamos session_state para ir acumulando las múltiples líneas antes de grabar
    if 'items_compra_actual' not in st.session_state:
        st.session_state.items_compra_actual = []

    with st.form("form_agregar_item_compra"):
        c1, c2, c3 = st.columns(3)
        with c1:
            codigo_prod = st.selectbox("Código / Producto", options=codigos_disponibles) if codigos_disponibles else st.text_input("Código")
            lote = st.text_input("Lote de Producción", value="S/L")
        with c2:
            cant_comprada = st.number_input("Cantidad Recibida", min_value=0.0, value=1.0, step=1.0)
            venc_lote = st.text_input("Vencimiento del Lote (Ej: 2026-12-31)", value="Sin Vencimiento")
        with c3:
            neto_unit = st.number_input("Costo Neto Unitario ($)", min_value=0.0, value=0.0, step=100.0)

        btn_add = st.form_submit_button("➕ Añadir Línea al Documento")
        if btn_add:
            if codigo_prod:
                if not df_base.empty:
                    match_p = df_base[df_base['codigo'].astype(str).str.strip() == str(codigo_prod).strip()]
                    desc_p = match_p['descripcion'].values[0] if not match_p.empty else "Sin descripción"
                else:
                    desc_p = "Producto Nuevo"
               
                st.session_state.items_compra_actual.append({
                    'codigo': str(codigo_prod),
                    'descripcion': desc_p,
                    'cantidad': cant_comprada,
                    'neto_unitario': neto_unit,
                    'subtotal': cant_comprada * neto_unit,
                    'lote': lote,
                    'vencimiento_lote': venc_lote
                })
                st.success(f"Línea Agregada: {desc_p} x {cant_comprada}")

    # --- Mostrar tabla temporal de las líneas del documento ---
    if st.session_state.items_compra_actual:
        st.markdown(f"##### Productos en el Documento N° {num_factura}:")
        df_temp = pd.DataFrame(st.session_state.items_compra_actual)
        st.dataframe(df_temp[['codigo', 'descripcion', 'lote', 'cantidad', 'neto_unitario', 'subtotal']], use_container_width=True)
       
        monto_total_factura = df_temp['subtotal'].sum()
        st.markdown(f"### 💰 **Total Neto de este Documento: ${monto_total_factura:,.2f}**")

        col_acc1, col_acc2 = st.columns(2)
        with col_acc1:
            if st.button("🗑️ Limpiar / Cancelar Recepción"):
                st.session_state.items_compra_actual = []
                st.rerun()
        with col_acc2:
            if st.button("🚀 Guardar Recepción Definitiva (Nube)", type="primary"):
                try:
                    fecha_registro = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    # PROCESAR GUARDADO DEFINITIVO EN SUPABASE
                    for item in st.session_state.items_compra_actual:
                        
                        # 1. ACTUALIZAR PRODUCTO (STOCK Y CPP)
                        res_p = supabase.table("productos").select("stock, costo").eq("rut_empresa", str(tenant_id)).eq("codigo", item['codigo']).execute()
                        
                        if res_p.data:
                            prod_actual = res_p.data[0]
                            stock_actual = float(prod_actual.get('stock', 0) or 0)
                            costo_anterior = float(prod_actual.get('costo', 0) or 0)
                        else:
                            stock_actual = 0.0
                            costo_anterior = 0.0

                        # Cálculo del Costo Promedio Ponderado (CPP)
                        cant_n = float(item['cantidad'])
                        costo_n = float(item['neto_unitario'])
                        
                        if (stock_actual + cant_n) > 0:
                            nuevo_cpp = ((stock_actual * costo_anterior) + (cant_n * costo_n)) / (stock_actual + cant_n)
                        else:
                            nuevo_cpp = costo_n

                        nuevo_stock = stock_actual + cant_n

                        # Impactar tabla de productos
                        supabase.table("productos").update({
                            "stock": nuevo_stock,
                            "costo": nuevo_cpp
                        }).eq("rut_empresa", str(tenant_id)).eq("codigo", item['codigo']).execute()

                        # 2. REGISTRAR LÍNEA EN LA TABLA COMPRAS (Multi-línea con misma factura)
                        registro_compra = {
                            'fecha_hora': fecha_registro,
                            'tipo_recepcion': tipo_recepcion,
                            'proveedor': proveedor_factura,
                            'factura': num_factura,
                            'codigo': item['codigo'],
                            'descripcion': item['descripcion'],
                            'cantidad': cant_n,
                            'neto_unitario': costo_n,
                            'costo_total': item['subtotal'],
                            'lote': item['lote'],
                            'fecha_vencimiento_lote': item['vencimiento_lote'],
                            'condicion_pago': condicion_pago,
                            'id_negocio': str(tenant_id)
                        }
                        supabase.table("compras").insert(registro_compra).execute()

                    # 3. SI ES CRÉDITO O CHEQUE, CREAR LA DEUDA EN CUENTAS POR PAGAR
                    if condicion_pago in ["Crédito", "Cheque"]:
                        nueva_cuenta = {
                            'rut_empresa': str(tenant_id),
                            'proveedor': proveedor_factura,
                            'numero_factura': num_factura,
                            'fecha_emision': str(fecha_emision),
                            'fecha_vencimiento': str(fecha_vencimiento_factura),
                            'monto_total': float(monto_total_factura),
                            'estado': 'PENDIENTE'
                        }
                        supabase.table("cuentas_por_pagar").insert(nueva_cuenta).execute()

                    # Limpiar sesión y notificar éxito
                    st.session_state.items_compra_actual = []
                    st.success(f"🎉 ¡Recepción del documento {num_factura} exitosa! Stock y CPP actualizados en la Nube.")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error crítico al procesar la factura en Supabase: {e}")
    else:
        st.info("ℹ️ Añade al menos un producto (línea) para armar el documento de recepción.")