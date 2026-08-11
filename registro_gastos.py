import streamlit as st
import pandas as pd
import os
from datetime import datetime

def mostrar_modulo_registro_gastos(ruta_negocio):
    st.markdown("### 📋 Registro y Control de Gastos")

    archivo_gastos = os.path.join(ruta_negocio, "Registro_Gastos.xlsx")

    if not os.path.exists(archivo_gastos):
        df_ini = pd.DataFrame(columns=['Fecha_Hora', 'Descripcion_Gasto', 'Categoria', 'Metodo_Pago', 'Documento', 'Monto'])
        df_ini.to_excel(archivo_gastos, index=False)

    df_gastos = pd.read_excel(archivo_gastos)

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
                nuevo_registro = pd.DataFrame([{
                    'Fecha_Hora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'Descripcion_Gasto': desc_gasto,
                    'Categoria': cat_gasto,
                    'Metodo_Pago': metodo_pago,
                    'Documento': doc_gasto,
                    'Monto': monto_gasto
                }])
                df_actualizado = pd.concat([df_gastos, nuevo_registro], ignore_index=True)
                df_actualizado.to_excel(archivo_gastos, index=False)
                st.success("✅ ¡Gasto registrado con éxito!")
                st.rerun()

    st.divider()

    df_gastos = pd.read_excel(archivo_gastos)

    if df_gastos.empty:
        st.info("ℹ️ No hay gastos registrados todavía en este negocio.")
    else:
        total_egresos = df_gastos['Monto'].sum()

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
                st.info(f"📅 **{row.get('Fecha_Hora', '')}** | 📝 **{row.get('Descripcion_Gasto', '')}** | 🏷️ {row.get('Categoria', '')} | 💳 {row.get('Metodo_Pago', '')} | 📄 {row.get('Documento', 'Sin Doc')} | **Monto: ${float(row.get('Monto', 0)):,.2f}**")
            with c_btn:
                if st.button("🗑️", key=f"del_gasto_fila_{idx}", help="Eliminar este registro"):
                    df_gastos = df_gastos.drop(idx).reset_index(drop=True)
                    df_gastos.to_excel(archivo_gastos, index=False)
                    st.success("✅ Gasto eliminado correctamente.")
                    st.rerun()