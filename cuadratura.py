import streamlit as st
import pandas as pd
from datetime import date
import os

def mostrar_modulo_cuadratura_diaria(ruta_negocio):
    st.markdown("### 📒 Cuadratura Diaria y Cuaderno de Caja")
    
    st.markdown("""
        <div style='background-color: #F3F4F6; padding: 12px; border-radius: 8px; margin-bottom: 15px;'>
            <strong>📌 Control de Caja Inteligente:</strong> Gestiona tus ingresos generales y controla tus cierres de forma limpia.
        </div>
    """, unsafe_allow_html=True)

    archivo_cuadratura = os.path.join(ruta_negocio, "Cuadratura_Diaria.xlsx")
    
    columnas_requeridas = [
        'ID', 'Fecha', 'Efectivo', 'Transferencia', 'Debito', 'Cigarros', 'Otros_Ingresos', 
        'VentaTotal', 'MarkupGeneral', 'MarkupCigarros', 'CostoReposicion', 'UtilidadRetirable', 'Observaciones'
    ]

    if not os.path.exists(archivo_cuadratura):
        pd.DataFrame(columns=columnas_requeridas).to_excel(archivo_cuadratura, index=False)

    fecha_cuat = st.date_input("Fecha de Cuadratura", value=date.today())
    
    st.markdown("#### 💰 Ingresos Generales de Caja")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        efectivo_c = float(st.number_input("💵 Efectivo ($)", min_value=0, step=1000, value=0, format="%d"))
    with col_f2:
        transferencia_c = float(st.number_input("📱 Transferencias ($)", min_value=0, step=1000, value=0, format="%d"))
    with col_f3:
        debito_c = float(st.number_input("💳 Débito / Tarjetas ($)", min_value=0, step=1000, value=0, format="%d"))

    col_f4, col_f5 = st.columns(2)
    with col_f4:
        otros_ingresos_c = float(st.number_input("➕ Otros Ingresos ($)", min_value=0, step=1000, value=0, format="%d"))
    with col_f5:
        markup_general = st.number_input("📈 Markup Productos Generales (%)", min_value=1.0, max_value=500.0, value=50.0, step=5.0)

    aplicar_cigarros = st.toggle("🚬 ¿Aplicar control diferenciado para Cigarrillos / Exentos en este cierre?", value=True)
    
    cigarrillos_c = 0.0
    markup_cigarros = 0.0

    if aplicar_cigarros:
        st.markdown("#### 🚬 Control Específico de Cigarrillos")
        col_cig1, col_cig2 = st.columns(2)
        with col_cig1:
            cigarrillos_c = float(st.number_input("🚬 Venta de Cigarrillos ($)", min_value=0, step=1000, value=0, format="%d"))
        with col_cig2:
            markup_cigarros = st.number_input("📉 Markup Específico Cigarrillos (%)", min_value=1.0, max_value=100.0, value=10.0, step=1.0)

    ventas_generales = efectivo_c + transferencia_c + debito_c + otros_ingresos_c
    venta_total_calculada = ventas_generales + cigarrillos_c

    costo_general = ventas_generales / (1.0 + (markup_general / 100.0))
    costo_cigarros = (cigarrillos_c / (1.0 + (markup_cigarros / 100.0))) if (aplicar_cigarros and cigarrillos_c > 0) else 0.0
    
    costo_reposicion_total = costo_general + costo_cigarros
    utilidad_neta_disponible = venta_total_calculada - costo_reposicion_total

    st.divider()
    col_res1, col_res2, col_res3, col_res4 = st.columns(4)
    with col_res1:
        st.metric(label="🪙 Venta Total Día", value=f"${venta_total_calculada:,.2f}")
    with col_res2:
        st.metric(label="🚬 Venta Cigarrillos", value=f"${cigarrillos_c:,.2f}")
    with col_res3:
        st.metric(label="🔒 Fondo Reposición Total", value=f"${costo_reposicion_total:,.2f}", delta="Intocable")
    with col_res4:
        st.metric(label="💵 Utilidad Retirable Segura", value=f"${utilidad_neta_disponible:,.2f}", delta="Disponible")

    observaciones_c = st.text_input("📝 Observaciones del Cierre de Caja", value="Cierre normal")

    if st.button("💾 Guardar Cuadratura y Retiro", type="primary"):
        if venta_total_calculada <= 0:
            st.warning("⚠️ Debes ingresar al menos un monto en los ingresos de caja.")
        else:
            df_cuat_ant = pd.read_excel(archivo_cuadratura)
            nuevo_id = str(pd.Timestamp.now().timestamp())
            
            nuevo_registro = pd.DataFrame([{
                'ID': nuevo_id,
                'Fecha': str(fecha_cuat),
                'Efectivo': efectivo_c,
                'Transferencia': transferencia_c,
                'Debito': debito_c,
                'Cigarros': cigarrillos_c if aplicar_cigarros else 0.0,
                'Otros_Ingresos': otros_ingresos_c,
                'VentaTotal': venta_total_calculada,
                'MarkupGeneral': markup_general,
                'MarkupCigarros': markup_cigarros if aplicar_cigarros else 0.0,
                'CostoReposicion': costo_reposicion_total,
                'UtilidadRetirable': utilidad_neta_disponible,
                'Observaciones': observaciones_c
            }])
            pd.concat([df_cuat_ant, nuevo_registro], ignore_index=True).to_excel(archivo_cuadratura, index=False)
            st.success("✅ ¡Cuadratura guardada con éxito!")
            st.rerun()