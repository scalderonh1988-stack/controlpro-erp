import streamlit as st
import pandas as pd
from datetime import datetime
import uuid
# Importamos la conexión a tu base de datos y la seguridad de negocio
from data_manager import supabase, get_current_tenant

def mostrar_modulo_ventas(ruta_negocio):
    # --- BOTÓN DE VOLVER AL HOME ---
    if st.button("🏠 Volver al Home", use_container_width=True):
        st.session_state["modulo_activo"] = "home"
        st.rerun()
    st.markdown("---")

    st.markdown("### 💰 Módulo de Ventas (POS)")
    st.write("Registra tus ventas y actualiza tu inventario en tiempo real (100% Nube).")

    tenant_id = get_current_tenant()
    if not tenant_id:
        st.error("❌ No se ha identificado el negocio. Por favor, inicia sesión nuevamente.")
        return

    # 1. Inicializar el Carrito de Compras en la memoria temporal
    if "carrito_pos" not in st.session_state:
        st.session_state["carrito_pos"] = []

    # 2. Interfaz del Buscador
    col1, col2 = st.columns([3, 1])
    with col1:
        codigo_ingresado = st.text_input("🔍 Escanea o escribe el código de barras:", key="input_codigo_pos")
    with col2:
        st.write("") # Espaciador para alinear el botón
        st.write("")
        btn_buscar = st.button("Agregar al Carrito 🛒", use_container_width=True)

    # 3. Lógica para buscar el producto en Supabase
    if btn_buscar and codigo_ingresado:
        try:
            # Consulta directa a la nube (solo busca productos de este local)
            res = supabase.table("productos").select("*").eq("rut_empresa", str(tenant_id)).eq("codigo", str(codigo_ingresado).strip()).execute()
            
            if res.data and len(res.data) > 0:
                producto = res.data[0]
                stock_actual = float(producto.get("stock", 0))
                
                if stock_actual <= 0:
                    st.warning(f"⚠️ El producto '{producto.get('descripcion')}' está sin stock en el inventario.")
                else:
                    # Agregamos el producto al carrito virtual
                    nuevo_item = {
                        "id_temp": str(uuid.uuid4()), # ID interno para que no se mezclen
                        "codigo": producto.get("codigo"),
                        "descripcion": producto.get("descripcion", "Sin descripción"),
                        "precio": float(producto.get("precio_venta", 0)),
                        "cantidad": 1.0,
                        "subtotal": float(producto.get("precio_venta", 0)),
                        "stock_actual": stock_actual
                    }
                    st.session_state["carrito_pos"].append(nuevo_item)
                    st.success(f"✅ {nuevo_item['descripcion']} agregado.")
            else:
                st.error("❌ Producto no encontrado en la base de datos.")
        except Exception as e:
            st.error(f"❌ Error al conectar con Supabase: {e}")

    # 4. Mostrar el Carrito y procesar el Pago
    if st.session_state["carrito_pos"]:
        st.markdown("#### 🛒 Detalle del Ticket")
        
        # Transformamos el carrito en una tabla visual
        df_carrito = pd.DataFrame(st.session_state["carrito_pos"])
        st.dataframe(df_carrito[["descripcion", "precio", "cantidad", "subtotal"]], use_container_width=True)

        total_venta = df_carrito["subtotal"].sum()
        st.markdown(f"### 💵 Total a Pagar: ${total_venta:,.0f}")

        st.markdown("---")
        
        # Opciones de pago
        col_pago, col_doc, col_cobrar = st.columns(3)
        with col_pago:
            metodo_pago = st.selectbox("Método de Pago", ["Efectivo", "Tarjeta / Transbank", "Transferencia"])
        with col_doc:
            tipo_doc = st.selectbox("Documento", ["Boleta", "Factura"])
        with col_cobrar:
            st.write("")
            st.write("")
            
            # --- EL BOTÓN MÁGICO QUE ENVÍA A SUPABASE ---
            if st.button("🚀 CONFIRMAR Y COBRAR", type="primary", use_container_width=True):
                
                # Generamos un identificador único para agrupar esta venta
                folio_venta = f"TX-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                fecha_hoy = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Preparamos la bolsa de datos para enviar a Supabase
                registros_para_nube = []
                for item in st.session_state["carrito_pos"]:
                    registros_para_nube.append({
                        "folio": folio_venta,
                        "rut_empresa": str(tenant_id),
                        "fecha": fecha_hoy,
                        "detalle": f"{item['descripcion']} (Cant: {item['cantidad']})",
                        "monto": float(item["subtotal"]), # Aseguramos que sea formato numérico
                        "metodo_pago": metodo_pago,
                        "documento": tipo_doc
                    })

                try:
                    # 1. Insertamos y GUARDAMOS la respuesta de Supabase para validarla
                    respuesta_venta = supabase.table("ventas").insert(registros_para_nube).execute()

                    # Validamos explícitamente si Supabase devolvió datos confirmando el guardado
                    if not respuesta_venta.data:
                        st.error("❌ OJO: Supabase recibió la orden pero NO guardó los datos. Verifica que las columnas (folio, rut_empresa, fecha, detalle, monto, metodo_pago, documento) existan en tu tabla 'ventas' y estén bien escritas.")
                    else:
                        # 2. Descontamos el stock SOLO si la venta realmente se guardó
                        for item in st.session_state["carrito_pos"]:
                            nuevo_stock = item["stock_actual"] - item["cantidad"]
                            supabase.table("productos").update({"stock": float(nuevo_stock)}).eq("rut_empresa", str(tenant_id)).eq("codigo", item["codigo"]).execute()
                        
                        st.success(f"🎉 ¡Venta cobrada con éxito! (Folio: {folio_venta})")
                        st.info("📁 Los datos ya están seguros en Supabase.")
                        
                        # Limpiamos la pantalla para el siguiente cliente
                        st.session_state["carrito_pos"] = []
                        st.rerun()
                        
                except Exception as e:
                    # Si falla por tipo de datos o error de conexión, frenará aquí y mostrará el problema real
                    st.error(f"❌ Error devuelto por la base de datos: {e}")
    else:
        st.info("👉 El carrito está vacío. Ingresa un código de producto para comenzar a cobrar.")