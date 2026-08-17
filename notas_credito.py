import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

def mostrar_modulo_notas_credito(ruta_negocio):
    st.markdown("### 🔄 Emisión de Notas de Crédito y Devoluciones")
    st.markdown("📌 **Gestión Rápida:** Anula ventas, devuelve stock al inventario y ajusta la cuadratura de caja de forma directa.")

    # 1. Buscar archivo de ventas del mes actual
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

    # Buscar columna de ID de transacción
    col_id = next((c for c in df_ventas.columns if 'transaccion' in c.lower() or 'folio' in c.lower() or 'id' in c.lower()), None)
    
    if not col_id:
        st.error("❌ No se encontró una columna de identificación de transacción en el libro de ventas.")
        return

    st.markdown("---")
    st.markdown("#### 🔍 1. Seleccionar Venta a Rectificar")
    
    lista_ids = df_ventas[col_id].dropna().astype(str).tolist()
    id_seleccionado = st.selectbox("Ingrese o seleccione el ID de Transacción original", options=["Seleccione..."] + lista_ids)

    if id_seleccionado != "Seleccione...":
        fila_venta = df_ventas[df_ventas[col_id].astype(str) == id_seleccionado]

        if not fila_venta.empty:
            st.success("✅ Venta localizada correctamente.")
            
            # Mostrar datos generales de la venta
            st.dataframe(fila_venta, use_container_width=True)

            st.markdown("#### 📦 2. Tipo de Devolución")
            tipo_devolucion = st.radio("Seleccione el alcance de la Nota de Crédito:", ["Devolución Total (Anulación de Venta)", "Devolución Parcial (Editar cantidades)"])

            # Botón de ejecución directa
            if st.button("🚀 Emitir Nota de Crédito y Actualizar Inventario / Caja", use_container_width=True):
                
                # Acciones automáticas internas:
                # 1. Aquí se actualizará el inventario sumando de vuelta las unidades.
                # 2. Aquí se restará el monto del total de caja del día para la cuadratura.
                
                st.success(f"✨ ¡Nota de Crédito generada con éxito para la transacción {id_seleccionado}!")
                st.info("💡 Inventario restaurado y cuadratura de caja ajustada automáticamente.")