import streamlit as st
import pandas as pd
from datetime import datetime

def mostrar_modulo_registro_gastos(supabase):
    st.markdown("### 📋 Registro y Control de Gastos")

    # Obtenemos el RUT del cliente que está usando el sistema ahora mismo
    rut_actual = st.session_state.get("negocio_seleccionado")

    with st.form("form_nuevo_gasto_manual"):
        st.markdown("#### ➕ Registrar Gasto Manual")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            desc_gasto = st.text_input("Descripción del Gasto", value="")
            cat_gasto = st.selectbox("Categoría", ["Mercadería", "Servicios Básicos", "Arriendo", "Remuneraciones", "Varios", "Otros"])
        with col_g2:
            metodo_pago = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Crédito", "Cheque"])
            monto_gasto = st.number_input("Monto Total del Gasto ($)", min_value=0.0, step=100.0, value=0.0)
           
        doc_gasto = st.text_input("Documento Asociado (ej. Factura 123, Boleta)", value="Sin Documento")

        submitted_gasto = st.form_submit_button("Guardar Gasto")

        if submitted_gasto:
            if not desc_gasto:
                st.warning("⚠️ Debes ingresar una descripción para el gasto.")
            elif monto_gasto <= 0:
                st.warning("⚠️ El monto del gasto debe ser mayor a 0.")
            else:
                # --- GUARDADO BLINDADO EN SUPABASE ---
                nuevo_gasto = {
                    "rut_empresa": rut_actual,
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "detalle": desc_gasto,
                    "categoria": cat_gasto,
                    "metodo_pago": metodo_pago,
                    "documento": doc_gasto,
                    "monto": monto_gasto
                }
                try:
                    supabase.table("gastos").insert(nuevo_gasto).execute()
                    st.success("✅ ¡Gasto registrado con éxito en la nube!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al guardar en la nube: {e}")

    st.divider()

    # --- LECTURA BLINDADA DESDE SUPABASE ---
    try:
        # Traemos solo los gastos del cliente actual, ordenados por fecha
        res = supabase.table("gastos").select("*").eq("rut_empresa", rut_actual).order("fecha", desc=True).execute()
        df_gastos = pd.DataFrame(res.data)
    except Exception as e:
        df_gastos = pd.DataFrame()
        st.error("Error al conectar con la base de datos.")

    if df_gastos.empty:
        st.info("ℹ️ No hay gastos registrados todavía en este negocio.")
    else:
        total_egresos = df_gastos['monto'].sum()

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric(label="💰 Total Egresos Acumulados", value=f"${total_egresos:,.2f}")
        with col_m2:
            st.metric(label="📊 Cantidad de Registros", value=len(df_gastos))

        st.divider()
        st.markdown("#### 📂 Historial de Gastos y Egresos")
        st.markdown("Revisa el detalle de cada gasto y utiliza el botón de la derecha para eliminar el registro en caso de error.")

        for idx, row in df_gastos.iterrows():
            c_info, c_btn = st.columns([10, 1])
            with c_info:
                st.info(f"📅 **{row.get('fecha', '')}** | 📝 **{row.get('detalle', '')}** | 🏷️ {row.get('categoria', '')} | 💳 {row.get('metodo_pago', '')} | 📄 {row.get('documento', 'Sin Doc')} | **Monto: ${float(row.get('monto', 0)):,.2f}**")
            with c_btn:
                # Ahora eliminamos usando el ID único e indestructible de Supabase
                if st.button("🗑️", key=f"del_gasto_{row.get('id')}", help="Eliminar este registro"):
                    try:
                        supabase.table("gastos").delete().eq("id", row.get('id')).execute()
                        st.success("✅ Gasto eliminado correctamente de la nube.")
                        st.rerun()
                    except Exception as e:
                        st.error("Error al eliminar el registro.")