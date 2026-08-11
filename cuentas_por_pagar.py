import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

def mostrar_modulo_cuentas_por_pagar(ruta_negocio):
    st.markdown("### 💳 Módulo de Cuentas por Pagar y Proveedores")
    st.markdown("Administra y registra las facturas pendientes de tus proveedores. Cambia el estado a 'Pagado' cuando saldes la deuda.")
    st.error("🚨 ESTOY LEYENDO EL ARCHIVO NUEVO")

    archivo_cuentas = os.path.join(ruta_negocio, "Cuentas_Por_Pagar.xlsx")

    if not os.path.exists(archivo_cuentas):
        df_ini = pd.DataFrame(columns=['Proveedor', 'Numero_Factura', 'Fecha_Emision', 'Fecha_Vencimiento', 'Monto_Total', 'Estado'])
        df_ini.to_excel(archivo_cuentas, index=False)

    df_cuentas = pd.read_excel(archivo_cuentas)

    with st.expander("➕ Registrar Nueva Factura de Proveedor Manualmente"):
        with st.form("form_nueva_cuenta_manual"):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                prov_m = st.text_input("Nombre del Proveedor")
                num_fac_m = st.text_input("Número de Factura")
                monto_m = st.number_input("Monto Total ($)", min_value=0.0, step=100.0, value=0.0)
            with col_c2:
                f_emision = st.date_input("Fecha de Emisión", value=date.today())
                f_venc = st.date_input("Fecha de Vencimiento", value=date.today())
           
            btn_guardar_cuenta = st.form_submit_button("💾 Guardar Factura Pendiente")
            if btn_guardar_cuenta:
                if not prov_m or not num_fac_m or monto_m <= 0:
                    st.warning("⚠️ Completa todos los campos obligatorios y un monto mayor a 0.")
                else:
                    nueva_fila = pd.DataFrame([{
                        'Proveedor': prov_m,
                        'Numero_Factura': num_fac_m,
                        'Fecha_Emision': str(f_emision),
                        'Fecha_Vencimiento': str(f_venc),
                        'Monto_Total': monto_m,
                        'Estado': 'PENDIENTE'
                    }])
                    df_actualizado = pd.concat([df_cuentas, nueva_fila], ignore_index=True)
                    df_actualizado.to_excel(archivo_cuentas, index=False)
                    st.success("✅ ¡Factura registrada correctamente en Cuentas por Pagar!")
                    st.rerun()

    st.divider()

    df_cuentas = pd.read_excel(archivo_cuentas)

    if df_cuentas.empty:
        st.info("ℹ️ No hay cuentas por pagar registradas.")
    else:
        df_pendientes = df_cuentas[df_cuentas['Estado'].astype(str).str.upper() == 'PENDIENTE']
        deuda_total_pendiente = df_pendientes['Monto_Total'].sum() if not df_pendientes.empty else 0.0

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric(label="🔥 Deuda Total Pendiente", value=f"${deuda_total_pendiente:,.2f}")
        with col_m2:
            st.metric(label="📄 Total Documentos Registrados", value=len(df_cuentas))

        st.divider()
        st.markdown("#### 📂 Listado General de Cuentas")
        st.markdown("Utiliza el botón **'✅ Marcar Pagado'** al lado de cada documento para actualizar su estado de inmediato.")

        for idx, row in df_cuentas.iterrows():
            estado_actual = str(row.get('Estado', 'PENDIENTE')).upper()
            es_pendiente = estado_actual == 'PENDIENTE'

            c_info, c_action = st.columns([8, 2])
            with c_info:
                st.info(f"🏢 **{row.get('Proveedor', '')}** | Fac: **{row.get('Numero_Factura', '')}** | Emisión: {row.get('Fecha_Emision', '')} | Vence: **{row.get('Fecha_Vencimiento', '')}** | Monto: **${float(row.get('Monto_Total', 0)):,.2f}** | Estado: **{estado_actual}**")
           
            with c_action:
                if es_pendiente:
                    if st.button("✅ Marcar Pagado", key=f"pagar_cta_{idx}", type="primary"):
                        df_cuentas.at[idx, 'Estado'] = 'PAGADO'
                        df_cuentas.to_excel(archivo_cuentas, index=False)
                        st.success(f"🎉 ¡Factura {row.get('Numero_Factura', '')} marcada como Pagada!")
                        st.rerun()
                else:
                    st.success("✔ Pagado")