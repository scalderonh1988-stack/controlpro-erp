import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, date
import streamlit.components.v1 as components
import sys
import plotly.express as px
from data_manager import guardar_nuevo_cliente, cargar_maestro_clientes
from calendario_pagos import mostrar_modulo_calendario_pagos
from compras_cpp import mostrar_modulo_compras
from supabase import create_client, Client
from fpdf import FPDF
from PIL import Image

def cargar_maestro_proveedores(ruta_negocio):
    archivo_prov = os.path.join(ruta_negocio, "Maestro_Proveedores.xlsx")
    if not os.path.exists(archivo_prov):
        df_ini = pd.DataFrame(columns=['Nombre_Proveedor', 'Rut', 'Contacto', 'Telefono', 'Email'])
        df_ini.to_excel(archivo_prov, index=False)
    return pd.read_excel(archivo_prov)

def guardar_nuevo_proveedor(ruta_negocio, nombre, rut="", contacto="", telefono="", email=""):
    archivo_prov = os.path.join(ruta_negocio, "Maestro_Proveedores.xlsx")
    df_prov = cargar_maestro_proveedores(ruta_negocio)
    
    nombre_limpio = str(nombre).strip().upper()
    if not df_prov.empty and nombre_limpio in df_prov['Nombre_Proveedor'].str.upper().values:
        return 
        
    nuevo = pd.DataFrame([{
        'Nombre_Proveedor': nombre.strip(),
        'Rut': rut,
        'Contacto': contacto,
        'Telefono': telefono,
        'Email': email
    }])
    
    df_actualizado = pd.concat([df_prov, nuevo], ignore_index=True)
    df_actualizado.to_excel(archivo_prov, index=False)

# ⚙️ 1. CONFIGURACIÓN DE PÁGINA (SIEMPRE LO PRIMERO)
st.set_page_config(
    page_title="CREC-ERP - Gestión Inteligente",
    page_icon="📦",
    layout="wide"
)

# Estilo visual general
st.markdown("""
    <style>
    .main-title {
        font-size: 1.8rem;
        color: #1E3A8A;
        text-align: center;
        font-weight: bold;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 0.95rem;
        color: #4B5563;
        text-align: center;
        margin-bottom: 15px;
    }
    .ticket-box {
        background-color: #1F2937;
        padding: 20px;
        border-radius: 10px;
        border: 1px dashed #3B82F6;
        color: #F3F4F6;
        font-family: monospace;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. RUTAS Y CARPETAS GLOBALES ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CLIENTES_DIR = os.path.join(BASE_DIR, "clientes")
CARPETA_CLIENTES = CLIENTES_DIR
PERMISOS_FILE = os.path.join(BASE_DIR, "permisos_negocios.json")

if not os.path.exists(CLIENTES_DIR):
    os.makedirs(CLIENTES_DIR)

negocios_disponibles = [d for d in os.listdir(CLIENTES_DIR) if os.path.isdir(os.path.join(CLIENTES_DIR, d))]
if not negocios_disponibles:
    negocio_default = "negocio_1"
    os.makedirs(os.path.join(CLIENTES_DIR, negocio_default), exist_ok=True)
    negocios_disponibles = [negocio_default]

# 🔌 Conexión a Supabase usando st.secrets
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

try:
    resultado = supabase.table("empresas").select("*").execute()
    empresas_data = resultado.data
except:
    empresas_data = []

PROVEEDORES_FILE = os.path.join(CLIENTES_DIR, "maestro_proveedores.xlsx")


# --- 3. FUNCIONES DE MÓDULOS ---
def generar_guia_pdf(cliente_nombre, cliente_rut, carrito):
    pdf = FPDF(orientation='P', unit='mm', format='Letter')
    pdf.add_page()
  
    negocio_actual = str(st.session_state.get('negocio_seleccionado', '')).strip()
    tenant_dir = os.path.join(CARPETA_CLIENTES, negocio_actual) if negocio_actual else ""

    if tenant_dir:
        ruta_logo = os.path.join(tenant_dir, "logo_empresa.png")
        if os.path.exists(ruta_logo):
            try:
                pdf.image(ruta_logo, x=10, y=8, w=25)
            except Exception as e:
                pass

    cfg = {}
    if tenant_dir:
        ruta_config_json = os.path.join(tenant_dir, "config_ticket.json")
        if os.path.exists(ruta_config_json):
            try:
                with open(ruta_config_json, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}

    if not cfg:
        cfg = st.session_state.get('config_ticket', {})

    nombre_empresa = cfg.get('nombre_empresa') or negocio_actual or 'MI EMPRESA SPA'
    rut_empresa = cfg.get('rut_empresa') or 'Sin RUT'
    direccion_empresa = cfg.get('direccion') or 'Sin Dirección'
   
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 6, str(nombre_empresa), ln=True, align='C')
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 5, f"Dirección: {str(direccion_empresa)}", ln=True, align='C')
    pdf.cell(0, 5, f"RUT: {str(rut_empresa)}", ln=True, align='C')
    pdf.ln(5)
   
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "GUÍA DE DESPACHO ELECTRÓNICA", ln=True, align='C')
    pdf.ln(5)
   
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 6, "DATOS DEL CLIENTE", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(115, 6, f"Razón Social / Nombre: {cliente_nombre}", border=1)
    pdf.cell(60, 6, f"RUT: {cliente_rut}", border=1, ln=True)
    pdf.ln(5)
   
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(85, 8, "Descripción", border=1, align='C')
    pdf.cell(20, 8, "Cant.", border=1, align='C')
    pdf.cell(35, 8, "P. Unitario", border=1, align='C')
    pdf.cell(35, 8, "Total", border=1, align='C', ln=True)
   
    pdf.set_font("Arial", '', 9)
    total_general = 0
    for item in carrito:
        producto = str(item.get('Descripción') or item.get('Producto') or 'Ítem')
        cantidad = item.get('Cantidad', 0)
        precio_unitario = item.get('Precio Unitario') or item.get('Precio_Unitario') or 0
        subtotal = item.get('Subtotal', 0)
        total_general += float(subtotal)
       
        pdf.cell(85, 7, producto, border=1)
        pdf.cell(20, 7, str(cantidad), border=1, align='C')
        pdf.cell(35, 7, f"${float(precio_unitario):,.0f}", border=1, align='R')
        pdf.cell(35, 7, f"${float(subtotal):,.0f}", border=1, align='R', ln=True)
       
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 8, "TOTAL GENERAL:", border=1, align='R')
    pdf.cell(35, 8, f"${total_general:,.0f}", border=1, align='R', ln=True)
   
    return pdf.output(dest='S').encode('latin1')

def mostrar_modulo_cuentas_por_cobrar(ruta_negocio):
    if st.button("⬅️ Volver al Home", use_container_width=True):
        st.session_state.menu_seleccionado = "🏠 Home / Bienvenida"
        st.rerun()
        
    st.markdown("### 📑 Gestión de Cuentas por Cobrar")
    archivo_cxp = os.path.join(ruta_negocio, "Cuentas_por_Cobrar.xlsx")
  
    if not os.path.exists(archivo_cxp):
        st.info("ℹ️ No hay registros de cuentas por cobrar todavía.")
        return

    df_cxp = pd.read_excel(archivo_cxp)
    
    if not df_cxp.empty:
        col_venc = next((c for c in df_cxp.columns if 'vencimiento' in c.lower() or 'fecha' in c.lower() and c.lower() != 'fecha'), None)
        
        if col_venc:
            hoy = pd.to_datetime(date.today())
            fechas_venc = pd.to_datetime(df_cxp[col_venc], errors='coerce')
            dias_atraso = (hoy - fechas_venc).dt.days
            dias_atraso = dias_atraso.apply(lambda x: x if x > 0 else 0)
            df_cxp["DiasAtraso"] = dias_atraso
        else:
            df_cxp["DiasAtraso"] = 0

    cliente_filtro = st.text_input("🔍 Buscar por Cliente:")
  
    df_filtrado = df_cxp.copy()
    if cliente_filtro:
        df_filtrado = df_filtrado[df_filtrado["Cliente"].str.contains(cliente_filtro, case=False, na=False)]
  
    st.dataframe(df_filtrado, use_container_width=True)
    
    total_pendiente = df_filtrado['SaldoPendiente'].sum() if 'SaldoPendiente' in df_filtrado.columns else 0.0
    st.write(f"Total pendiente: **${total_pendiente:,.2f}**")
  
    st.divider()
    st.markdown("### 💳 Registrar Abono")
    
    clientes_deuda = []
    if "SaldoPendiente" in df_cxp.columns and "Cliente" in df_cxp.columns:
        clientes_deuda = df_cxp[df_cxp["SaldoPendiente"] > 0]["Cliente"].unique().tolist()
   
    if clientes_deuda:
        cliente_seleccionado = st.selectbox("Selecciona el cliente para abonar:", options=clientes_deuda)
        monto_abono = st.number_input("💵 Monto a abonar ($):", min_value=0.0, step=100.0)
       
        if st.button("✅ Registrar Abono", use_container_width=True):
            if monto_abono > 0:
                idx = df_cxp[df_cxp["Cliente"] == cliente_seleccionado].index[0]
                saldo_actual = df_cxp.loc[idx, "SaldoPendiente"]
              
                if monto_abono >= saldo_actual:
                    df_cxp = df_cxp.drop(idx)
                    st.success(f"🎉 Deuda saldada por completo para {cliente_seleccionado}.")
                else:
                    df_cxp.loc[idx, "SaldoPendiente"] -= monto_abono
                    if "Abono" in df_cxp.columns:
                        df_cxp.loc[idx, "Abono"] += monto_abono
                    st.success(f"🟢 Abono registrado con éxito. Nuevo saldo pendiente: ${df_cxp.loc[idx, 'SaldoPendiente']:,.2f}")
              
                if "DiasAtraso" in df_cxp.columns:
                    df_cxp = df_cxp.drop(columns=["DiasAtraso"])
                    
                df_cxp.to_excel(archivo_cxp, index=False)
                st.rerun()
            else:
                st.warning("⚠️ Ingresa un monto mayor a cero.")
    else:
        st.info("ℹ️ No hay clientes con deudas pendientes para registrar abonos.")

def mostrar_modulo_registro_gastos(supabase):
    st.markdown("### 📋 Registro y Control de Gastos")
    
    rut_actual = st.session_state.get("negocio_seleccionado")
    
    with st.form("form_nuevo_gasto"):
        st.markdown("#### ➕ Registrar Nuevo Gasto o Egreso")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fecha_gasto = st.date_input("Fecha del Gasto")
            proveedor_g = st.text_input("Proveedor / Establecimiento")
            factura_g = st.text_input("Número de Factura o Boleta (Opcional)")
            categoria_g = st.selectbox("Categoría", ["Mercadería", "Gastos Operativos", "Servicios Básicos", "Logística", "Otros"])
        with col_g2:
            monto_g = st.number_input("Monto Total ($)", min_value=0.0, step=100.0, value=0.0)
            tipo_pago_g = st.selectbox("Método de Pago", ["Efectivo", "Tarjeta de Débito", "Tarjeta de Crédito", "Transferencia", "Cheque"])
            descripcion_g = st.text_input("Descripción / Detalle (ej: Paltas, Tablillas)")
            
        btn_guardar_gasto = st.form_submit_button("💾 Guardar Gasto", type="primary")
        
        if btn_guardar_gasto:
            if monto_g <= 0:
                st.warning("⚠️ Debes ingresar un monto mayor a cero.")
            else:
                texto_detalle = f"{proveedor_g} - {descripcion_g}" if proveedor_g else descripcion_g
                
                nuevo_gasto = {
                    "rut_empresa": rut_actual,
                    "fecha": str(fecha_gasto),
                    "detalle": texto_detalle,
                    "categoria": categoria_g,
                    "metodo_pago": tipo_pago_g,
                    "documento": factura_g or "S/N",
                    "monto": monto_g
                }
                try:
                    supabase.table("gastos").insert(nuevo_gasto).execute()
                    st.success("✅ ¡Gasto registrado con éxito en la nube!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al guardar en la nube: {e}")

    st.divider()
    st.markdown("### 📂 Historial de Gastos Registrados")
    
    try:
        res = supabase.table("gastos").select("*").eq("rut_empresa", rut_actual).order("fecha", desc=True).execute()
        df_gastos = pd.DataFrame(res.data)
    except Exception as e:
        df_gastos = pd.DataFrame()
        st.error("Error al conectar con la base de datos.")

    if df_gastos.empty:
        st.info("ℹ️ No hay registros de gastos todavía.")
    else:
        total_gastos = df_gastos['monto'].sum()
        st.metric(label="💰 Total Histórico de Gastos", value=f"${total_gastos:,.2f}")
        
        st.divider()
        st.markdown("Revisa el detalle de cada gasto y utiliza el botón de la derecha para **eliminar** el registro en caso de error.")

        for idx, row in df_gastos.iterrows():
            c_info, c_btn = st.columns([10, 1])
            with c_info:
                st.info(f"📅 **{row.get('fecha', '')}** | 📝 **{row.get('detalle', '')}** | 🏷️ {row.get('categoria', '')} | 💳 {row.get('metodo_pago', '')} | 📄 Fac/Bol: {row.get('documento', 'S/N')} | **Monto: ${float(row.get('monto', 0)):,.2f}**")
            with c_btn:
                if st.button("🗑️", key=f"del_gasto_{row.get('id')}", help="Eliminar este registro"):
                    try:
                        supabase.table("gastos").delete().eq("id", row.get('id')).execute()
                        st.success("✅ Gasto eliminado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error("Error al eliminar el registro.")

def mostrar_modulo_cuentas_por_pagar(ruta_negocio):
    st.markdown("### 💳 Módulo de Cuentas por Pagar y Proveedores")
    archivo_cuentas = os.path.join(ruta_negocio, "Cuentas_Por_Pagar.xlsx")
   
    if not os.path.exists(archivo_cuentas):
        pd.DataFrame(columns=['Proveedor', 'Numero_Factura', 'Fecha_Emision', 'Fecha_Vencimiento', 'Monto_Total', 'Estado']).to_excel(archivo_cuentas, index=False)
   
    df_cuentas = pd.read_excel(archivo_cuentas)
   
    for col_f in ['Fecha_Emision', 'Fecha_Vencimiento']:
        if col_f in df_cuentas.columns:
            df_cuentas[col_f] = pd.to_datetime(df_cuentas[col_f], errors='coerce').dt.date
   
    st.dataframe(df_cuentas, use_container_width=True)
   
    st.divider()
    st.markdown("### ⚙️ Actualizar Estado de Documento")
   
    if not df_cuentas.empty:
        opciones_facturas = []
        for idx, row in df_cuentas.iterrows():
            opciones_facturas.append(f"Fila {idx} - Prov: {row.get('Proveedor')} | Factura #{row.get('Numero_Factura')} | Estado: {row.get('Estado')}")
       
        with st.form("form_actualizar_estado_cxp"):
            factura_seleccionada = st.selectbox("Selecciona la factura a modificar:", options=opciones_facturas)
            nuevo_estado = st.selectbox("Nuevo Estado:", options=["PAGADO", "PENDIENTE"])
           
            btn_actualizar_estado = st.form_submit_button("🔄 Actualizar Estado de Factura", type="primary")
           
            if btn_actualizar_estado and factura_seleccionada:
                idx_fila = int(factura_seleccionada.split(" - ")[0].replace("Fila ", ""))
                df_cuentas.loc[idx_fila, "Estado"] = nuevo_estado
                df_cuentas.to_excel(archivo_cuentas, index=False)
                st.success(f"✅ ¡El estado de la factura se ha actualizado a **{nuevo_estado}** con éxito!")
                st.rerun()
    else:
        st.info("ℹ️ No hay registros en Cuentas por Pagar para modificar.")        

def mostrar_modulo_cuadratura_diaria(ruta_negocio):
    st.markdown("### 📒 Cuadratura Diaria y Cuaderno de Caja")
    
    st.markdown("""
        <div style='background-color: #F3F4F6; padding: 12px; border-radius: 8px; margin-bottom: 15px;'>
            <strong>📌 Control de Caja Inteligente:</strong> Gestiona tus ingresos generales y activa el interruptor si necesitas separar productos con margen diferenciado (como cigarrillos).
        </div>
    """, unsafe_allow_html=True)

    archivo_cuadratura = os.path.join(ruta_negocio, "Cuadratura_Diaria.xlsx")
    if not os.path.exists(archivo_cuadratura):
        pd.DataFrame(columns=[
            'Fecha', 'Efectivo', 'Transferencia', 'Debito', 'Cigarros', 'Otros_Ingresos', 
            'VentaTotal', 'MarkupGeneral', 'MarkupCigarros', 'CostoReposicion', 'UtilidadRetirable', 'Observaciones'
        ]).to_excel(archivo_cuadratura, index=False)

    with st.form("form_cuadratura_diaria"):
        fecha_cuat = st.date_input("Fecha de Cuadratura", value=date.today())
        
        st.divider()
        st.markdown("#### 💰 Ingresos Generales de Caja")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            efectivo_c = st.number_input("💵 Efectivo ($)", min_value=0.0, step=100.0, value=0.0)
        with col_f2:
            transferencia_c = st.number_input("📱 Transferencias ($)", min_value=0.0, step=100.0, value=0.0)
        with col_f3:
            debito_c = st.number_input("💳 Débito / Tarjetas ($)", min_value=0.0, step=100.0, value=0.0)

        col_f4, col_f5 = st.columns(2)
        with col_f4:
            otros_ingresos_c = st.number_input("➕ Otros Ingresos ($)", min_value=0.0, step=100.0, value=0.0)
        with col_f5:
            markup_general = st.number_input("📈 Markup Productos Generales (%)", min_value=1.0, max_value=500.0, value=50.0, step=5.0)

        st.divider()
        
        aplicar_cigarros = st.toggle("🚬 ¿Aplicar control diferenciado para Cigarrillos / Exentos en este cierre?", value=True)
        
        cigarrillos_c = 0.0
        markup_cigarros = 0.0

        if aplicar_cigarros:
            st.markdown("#### 🚬 Control Específico de Cigarrillos")
            col_cig1, col_cig2 = st.columns(2)
            with col_cig1:
                cigarrillos_c = st.number_input("🚬 Venta de Cigarrillos ($)", min_value=0.0, step=100.0, value=0.0)
            with col_cig2:
                markup_cigarros = st.number_input("📉 Markup Específico Cigarrillos (%)", min_value=1.0, max_value=100.0, value=10.0, step=1.0)

        ventas_generales = efectivo_c + transferencia_c + debito_c + otros_ingresos_c
        venta_total_calculada = ventas_generales + cigarrillos_c

        costo_general = ventas_generales / (1.0 + (markup_general / 100.0))
        
        if aplicar_cigarros and cigarrillos_c > 0:
            costo_cigarros = cigarrillos_c / (1.0 + (markup_cigarros / 100.0))
        else:
            costo_cigarros = 0.0
        
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

        btn_guardar_cuat = st.form_submit_button("💾 Guardar Cuadratura y Retiro", type="primary")

        if btn_guardar_cuat:
            if venta_total_calculada <= 0:
                st.warning("⚠️ Debes ingresar al menos un monto en los ingresos de caja.")
            else:
                df_cuat_ant = pd.read_excel(archivo_cuadratura)
                nuevo_registro = pd.DataFrame([{
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

    st.divider()
    st.markdown("### 📂 Historial de Cuadraturas Registradas")
    if os.path.exists(archivo_cuadratura):
        df_cuadratura = pd.read_excel(archivo_cuadratura)
        if not df_cuadratura.empty:
            st.dataframe(df_cuadratura, use_container_width=True)
        else:
            st.info("ℹ️ No hay registros guardados todavía.")

def mostrar_modulo_conciliacion_retiros(ruta_negocio):
    if "mostrar_encabezado_con_home" in globals():
        mostrar_encabezado_con_home("🏦 Conciliación Bancaria y Retiros Protegidos por Markup")
    else:
        st.markdown("### 🏦 Conciliación Bancaria y Retiros Protegidos por Markup")
    
    st.markdown("""
        <div style='background-color: #EFF6FF; padding: 15px; border-radius: 8px; border-left: 4px solid #3B82F6; margin-bottom: 20px;'>
            <strong>💡 Control Financiero para Emprendedores:</strong> Este módulo te ayuda a calcular el 
            <strong>retiro seguro de utilidades</strong> basado en tu porcentaje de Markup (margen), evitando que 
            saques dinero destinado a la reposición de mercadería.
        </div>
    """, unsafe_allow_html=True)

    archivo_retiros = os.path.join(ruta_negocio, "Registro_Retiros_Seguros.xlsx")
    if not os.path.exists(archivo_retiros):
        pd.DataFrame(columns=['Fecha', 'VentaTotal', 'MarkupAplicado', 'CostoMercaderia', 'UtilidadRealRetirable', 'RetiroEfectuado', 'Observaciones']).to_excel(archivo_retiros, index=False)

    tab_cr1, tab_cr2, tab_cr3 = st.tabs(["💰 Cálculo de Retiro Seguro (Markup)", "🏦 Conciliación de Cartolas (POS / Banco)", "📂 Historial de Retiros"])

    with tab_cr1:
        st.markdown("### 🎯 Asistente de Retiro Diario sin Desfinanciar el Negocio")
        
        with st.form("form_calculo_retiro"):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                fecha_calculo = st.date_input("Fecha de la Cuadratura", value=date.today())
                venta_dia_input = st.number_input("💵 Venta Total del Día ($)", min_value=0.0, step=1000.0, value=150000.0)
            with col_c2:
                markup_porcentaje = st.number_input("📈 Markup / Margen Promedio (%)", min_value=1.0, max_value=500.0, value=50.0, step=5.0, help="Porcentaje de margen estimado sobre el costo aplicado a tus productos.")
                observacion_retiro = st.text_input("📝 Notas u Observaciones del Día", value="Cierre diario normal")

            markup_decimal = markup_porcentaje / 100.0
            costo_reposicion = venta_dia_input / (1.0 + markup_decimal)
            utilidad_neta_retirable = venta_dia_input - costo_reposicion

            st.divider()
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric(label="🛒 Venta Total Ingresada", value=f"${venta_dia_input:,.2f}")
            with col_m2:
                st.metric(label="🔒 Fondo Intocable (Reposición)", value=f"${costo_reposicion:,.2f}", delta="Guardar en Caja/Cuenta")
            with col_m3:
                st.metric(label="💵 Utilidad Real Retirable", value=f"${utilidad_neta_retirable:,.2f}", delta="Disponible para Retiro")

            btn_guardar_retiro = st.form_submit_button("💾 Guardar Registro de Retiro Seguro", type="primary")

            if btn_guardar_retiro:
                if venta_dia_input <= 0:
                    st.warning("⚠️ Ingresa una venta válida mayor a 0.")
                else:
                    df_ret_ant = pd.read_excel(archivo_retiros)
                    nuevo_reg_ret = pd.DataFrame([{
                        'Fecha': str(fecha_calculo),
                        'VentaTotal': venta_dia_input,
                        'MarkupAplicado': markup_porcentaje,
                        'CostoMercaderia': costo_reposicion,
                        'UtilidadRealRetirable': utilidad_neta_retirable,
                        'RetiroEfectuado': utilidad_neta_retirable,
                        'Observaciones': observacion_retiro
                    }])
                    pd.concat([df_ret_ant, nuevo_reg_ret], ignore_index=True).to_excel(archivo_retiros, index=False)
                    st.success("✅ ¡Registro guardado con éxito! Se protegió el fondo de reposición de mercadería.")
                    st.rerun()

    with tab_cr2:
        st.markdown("### 🏦 Conciliación de Transacciones (Transbank / Bancos / Transferencias)")
        
        archivo_conciliacion = os.path.join(ruta_negocio, "Conciliacion_Bancaria.xlsx")
        if not os.path.exists(archivo_conciliacion):
            pd.DataFrame(columns=['Fecha', 'Origen', 'MontoVentaPOS', 'MontoAbonadoBanco', 'Diferencia', 'Estado']).to_excel(archivo_conciliacion, index=False)

        df_conci = pd.read_excel(archivo_conciliacion)
        st.dataframe(df_conci, use_container_width=True)

        with st.form("form_nueva_conciliacion"):
            st.markdown("#### ➕ Registrar Validación de Cartola")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                f_conci = st.date_input("Fecha de Cartola", value=date.today(), key="f_con")
                origen_pago = st.selectbox("Origen del Abono", ["Transbank / Débito", "Transbank / Crédito", "Transferencia Bancaria Directa", "Efectivo Depositado"])
            with col_b2:
                monto_pos = st.number_input("Monto Registrado en POS ($)", min_value=0.0, step=100.0, value=0.0, key="m_pos")
                monto_banco = st.number_input("Monto Abonado en Banco ($)", min_value=0.0, step=100.0, value=0.0, key="m_ban")

            diferencia_banco = monto_banco - monto_pos
            if diferencia_banco == 0:
                estado_conci = "Conciliado OK"
            elif diferencia_banco < 0:
                estado_conci = "Diferencia en contra (Comisión o Faltante)"
            else:
                estado_conci = "Abono Mayor"

            if st.form_submit_button("💾 Guardar Validación Bancaria"):
                nuevo_c = pd.DataFrame([{
                    'Fecha': str(f_conci),
                    'Origen': origen_pago,
                    'MontoVentaPOS': monto_pos,
                    'MontoAbonadoBanco': monto_banco,
                    'Diferencia': diferencia_banco,
                    'Estado': estado_conci
                }])
                pd.concat([df_conci, nuevo_c], ignore_index=True).to_excel(archivo_conciliacion, index=False)
                st.success("✅ ¡Conciliación registrada correctamente!")
                st.rerun()

    with tab_cr3:
        st.markdown("### 📂 Historial de Retiros Seguros Realizados")
        if os.path.exists(archivo_retiros):
            df_hist_ret = pd.read_excel(archivo_retiros)
            if not df_hist_ret.empty:
                st.dataframe(df_hist_ret, use_container_width=True)
                total_retirado = df_hist_ret['UtilidadRealRetirable'].sum() if 'UtilidadRealRetirable' in df_hist_ret.columns else 0.0
                st.metric(label="💵 Utilidad Histórica Retirada de forma Segura", value=f"${total_retirado:,.2f}")
            else:
                st.info("ℹ️ No hay registros de retiros todavía.")

# --- CONEXIÓN DE REPORTES A SUPABASE ---
def mostrar_modulo_reportes_avanzados(ruta_negocio):
    if st.button("⬅️ Volver al Home", use_container_width=True):
        st.session_state.menu_seleccionado = "🏠 Home / Bienvenida"
        st.rerun()

    st.markdown("### 📊 Módulo de Reportes e Inteligencia de Negocio")
    st.info("📈 Analiza el rendimiento financiero en tiempo real conectado a Supabase.")

    rut_actual = st.session_state.get("negocio_seleccionado")
    fecha_hoy = date.today().strftime('%Y-%m-%d')
    
    # Lectura de Ventas y Gastos en la Nube
    try:
        res_ventas = supabase.table("ventas").select("monto").eq("rut_empresa", rut_actual).like("fecha", f"{fecha_hoy}%").execute()
        total_ingresos_dia = sum([float(v['monto'] or 0) for v in res_ventas.data])
    except:
        total_ingresos_dia = 0.0

    try:
        res_gastos = supabase.table("gastos").select("monto, categoria").eq("rut_empresa", rut_actual).execute()
        df_g = pd.DataFrame(res_gastos.data)
        
        # Filtramos solo los gastos de hoy para el balance
        res_gastos_hoy = supabase.table("gastos").select("monto").eq("rut_empresa", rut_actual).like("fecha", f"{fecha_hoy}%").execute()
        total_egresos_hoy = sum([float(g['monto'] or 0) for g in res_gastos_hoy.data])
    except:
        total_egresos_hoy = 0.0
        df_g = pd.DataFrame()

    archivo_cxp = os.path.join(ruta_negocio, "Cuentas_por_Cobrar.xlsx")
    archivo_cpp = os.path.join(ruta_negocio, "Cuentas_Por_Pagar.xlsx")

    tab_r1, tab_r2, tab_r3, tab_r4 = st.tabs(["💰 Balance de Hoy (Nube)", "📈 Análisis de Gastos (Nube)", "📑 Estado de Cartera", "📄 Exportar Informes PDF"])

    with tab_r1:
        st.markdown("#### 💵 Resumen General de Ingresos vs. Gastos (Día Actual)")
        utilidad_estimada = total_ingresos_dia - total_egresos_hoy

        col_rep1, col_rep2, col_rep3 = st.columns(3)
        with col_rep1:
            st.metric(label="🪙 Ingresos Totales de Hoy", value=f"${total_ingresos_dia:,.2f}")
        with col_rep2:
            st.metric(label="📉 Gastos Operativos Hoy", value=f"${total_egresos_hoy:,.2f}")
        with col_rep3:
            st.metric(label="💼 Margen Neto Operativo", value=f"${utilidad_estimada:,.2f}", delta="Estimado")

    with tab_r2:
        st.markdown("#### 📂 Desglose Histórico de Gastos por Categoría")
        if not df_g.empty and 'categoria' in df_g.columns and 'monto' in df_g.columns:
            df_g['monto'] = pd.to_numeric(df_g['monto'], errors='coerce')
            gasto_por_cat = df_g.groupby('categoria')['monto'].sum().reset_index()
            st.dataframe(gasto_por_cat, use_container_width=True)
            st.bar_chart(gasto_por_cat.set_index('categoria')['monto'])
        else:
            st.info("ℹ️ No hay registros suficientes de gastos en la nube.")

    with tab_r3:
        st.markdown("#### ⏳ Reporte de Cuentas por Cobrar y Atrasos (Excel temporal)")
        if os.path.exists(archivo_cxp):
            df_cobrar = pd.read_excel(archivo_cxp)
            if not df_cobrar.empty:
                st.dataframe(df_cobrar, use_container_width=True)
            else:
                st.info("ℹ️ No hay registros activos en Cuentas por Cobrar.")
        else:
            st.info("ℹ️ No existe archivo de Cuentas por Cobrar.")

        st.markdown("#### 💳 Estado de Cuentas por Pagar (Proveedores)")
        if os.path.exists(archivo_cpp):
            df_pagar = pd.read_excel(archivo_cpp)
            if not df_pagar.empty:
                st.dataframe(df_pagar, use_container_width=True)
            else:
                st.info("ℹ️ No hay registros en Cuentas por Pagar.")
        else:
            st.info("ℹ️ No existe archivo de Cuentas por Pagar.")

    with tab_r4:
        st.markdown("#### 📄 Generación y Descarga de Informe Ejecutivo en PDF")
        if st.button("🖨️ Generar Reporte Ejecutivo PDF", type="primary"):
            try:
                pdf = FPDF(orientation='P', unit='mm', format='Letter')
                pdf.add_page()
                
                nombre_empresa_act = st.session_state.get('nombre_empresa', 'MI EMPRESA')
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 8, str(nombre_empresa_act), ln=True, align='C')
                pdf.set_font("Arial", '', 10)
                pdf.cell(0, 6, "INFORME EJECUTIVO DE GESTIÓN Y FINANZAS", ln=True, align='C')
                pdf.cell(0, 6, f"Fecha de Emisión: {date.today().strftime('%d/%m/%Y')}", ln=True, align='C')
                pdf.ln(10)

                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 8, "RESUMEN FINANCIERO DEL DIA", ln=True)
                pdf.set_font("Arial", '', 10)
                
                pdf.cell(100, 7, "Ingresos Totales Registrados:", border=1)
                pdf.cell(90, 7, f"${total_ingresos_dia:,.2f}", border=1, ln=True, align='R')
                pdf.cell(100, 7, "Gastos Operativos Totales:", border=1)
                pdf.cell(90, 7, f"${total_egresos_hoy:,.2f}", border=1, ln=True, align='R')
                pdf.cell(100, 7, "Margen Neto Operativo Estimado:", border=1)
                pdf.cell(90, 7, f"${utilidad_estimada:,.2f}", border=1, ln=True, align='R')
                pdf.ln(10)

                pdf.set_font("Arial", 'I', 9)
                pdf.cell(0, 6, "Reporte generado automáticamente desde la Nube.", ln=True, align='C')

                pdf_output_bytes = pdf.output(dest='S').encode('latin1')

                st.success("✅ ¡Informe PDF generado con éxito!")
                st.download_button(
                    label="⬇️ Descargar Informe PDF",
                    data=bytes(pdf_output_bytes),
                    file_name=f"Informe_Financiero_{date.today()}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"❌ Error al generar el PDF: {e}")


# --- 4. SISTEMA DE AUTENTICACIÓN Y BLINDAJE DE SEGURIDAD ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "negocio_actual" not in st.session_state:
    st.session_state.negocio_actual = None
if "usuario_logueado" not in st.session_state:
    st.session_state.usuario_logueado = None
if "es_admin_dev" not in st.session_state:
    st.session_state.es_admin_dev = False
if "intentos_fallidos" not in st.session_state:
    st.session_state.intentos_fallidos = 0

if not st.session_state.autenticado:
    st.markdown('<p class="main-title">🔐 CREC-ERP - Acceso Blindado</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Sistema protegido de gestión empresarial</p>', unsafe_allow_html=True)
 
    if st.session_state.intentos_fallidos >= 3:
        st.error("🚨 **Demasiados intentos fallidos.** El acceso temporalmente restringido por seguridad.")
        st.stop()

    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        with st.form("form_login_blindado"):
            usuario_input = st.text_input("👤 Usuario / RUT / Operador:")
            password_input = st.text_input("🔑 Contraseña:", type="password")
            btn_ingresar = st.form_submit_button("🚀 Entrar al Sistema", use_container_width=True)
         
        if btn_ingresar:
            usuario_limpio = str(usuario_input).strip()
            password_limpio = str(password_input).strip()
          
            if not usuario_limpio or not password_limpio:
                st.error("❌ Debes ingresar tanto el usuario como la contraseña.")
            else:
                # 1. Validación Admin Master (Blindada)
                if usuario_limpio.lower() in ["admin", "desarrollador", "simon"] and password_limpio == "SIMON1908":
                    st.session_state.autenticado = True
                    st.session_state.es_admin_dev = True
                    st.session_state.usuario_logueado = "Administrador Master"
                    st.session_state.negocio_actual = "admin_general"
                    st.session_state.nombre_empresa = "CREC-ERP Master"
                    st.session_state.rol_usuario = "Administrador"
                    st.session_state.intentos_fallidos = 0
                    st.success("🛠️ ¡Acceso Maestro Autorizado!")
                    st.rerun()
                else:
                    # 2. Buscar empresa principal en Supabase con validación de licencia
                    empresa_encontrada = next((emp for emp in empresas_data if str(emp.get("rut_empresa")) == usuario_limpio), None)

                    if empresa_encontrada:
                        licencia_activa_db = empresa_encontrada.get("licencia_activa", True)
                        
                        if licencia_activa_db:
                            negocio_asignado = usuario_limpio
                            os.makedirs(os.path.join(CLIENTES_DIR, negocio_asignado), exist_ok=True)
                          
                            st.session_state.autenticado = True
                            st.session_state.es_admin_dev = False
                            st.session_state.negocio_actual = negocio_asignado
                            st.session_state.usuario_logueado = usuario_input
                            st.session_state.nombre_empresa = empresa_encontrada.get("empresa_nombre")
                            st.session_state.rol_usuario = "Administrador"
                            st.session_state.intentos_fallidos = 0
                            st.success(f"🏠 ¡Bienvenido! Ingresando al entorno de {str(st.session_state.nombre_empresa).upper()}...")
                            st.rerun()
                        else:
                            st.error("❌ La licencia de este negocio se encuentra expirada o inactiva.")
                    else:
                        # 3. Buscar operador secundario en la nube (tabla 'usuarios' Supabase)
                        acceso_exitoso = False
                        try:
                            # Intenta conectar a Supabase para buscar el usuario secundario
                            res_usr = supabase.table("usuarios").select("*").eq("usuario", usuario_limpio).execute()
                            if res_usr.data:
                                datos_usr = res_usr.data[0]
                                if str(datos_usr.get("password")) == password_limpio:
                                    rut_negocio = datos_usr.get("rut_empresa")
                                    st.session_state.autenticado = True
                                    st.session_state.es_admin_dev = False
                                    st.session_state.negocio_actual = rut_negocio
                                    st.session_state.usuario_logueado = datos_usr.get("nombre", usuario_limpio)
                                    st.session_state.rol_usuario = datos_usr.get("rol", "Cajero / Vendedor")
                                    st.session_state.intentos_fallidos = 0
                                    
                                    emp_info = next((emp for emp in empresas_data if str(emp.get("rut_empresa")) == rut_negocio), None)
                                    st.session_state.nombre_empresa = emp_info.get("empresa_nombre") if emp_info else rut_negocio
                                    
                                    st.success(f"🟢 ¡Bienvenido {st.session_state.usuario_logueado}!")
                                    acceso_exitoso = True
                                    st.rerun()
                        except Exception as e:
                            pass
                            
                        # Fallback local (Por si tienes cajeros que aún no has migrado a Supabase)
                        if not acceso_exitoso:
                            for neg_folder in os.listdir(CLIENTES_DIR):
                                folder_path = os.path.join(CLIENTES_DIR, neg_folder)
                                if os.path.isdir(folder_path):
                                    arch_usr = os.path.join(folder_path, "usuarios_negocio.json")
                                    if os.path.exists(arch_usr):
                                        with open(arch_usr, "r", encoding="utf-8") as f:
                                            diccionario_users = json.load(f)
                                            if usuario_limpio in diccionario_users:
                                                datos_usr = diccionario_users[usuario_limpio]
                                                if str(datos_usr.get("password")) == password_limpio:
                                                    st.session_state.autenticado = True
                                                    st.session_state.es_admin_dev = False
                                                    st.session_state.negocio_actual = neg_folder
                                                    st.session_state.usuario_logueado = datos_usr.get("nombre", usuario_limpio)
                                                    st.session_state.rol_usuario = datos_usr.get("rol", "Cajero / Vendedor")
                                                    st.session_state.intentos_fallidos = 0
                                                    
                                                    emp_info = next((emp for emp in empresas_data if str(emp.get("rut_empresa")) == neg_folder), None)
                                                    st.session_state.nombre_empresa = emp_info.get("empresa_nombre") if emp_info else neg_folder
                                                    
                                                    st.success(f"🟢 ¡Bienvenido {st.session_state.usuario_logueado}!")
                                                    acceso_exitoso = True
                                                    st.rerun()
                        
                        if not acceso_exitoso:
                            st.session_state.intentos_fallidos += 1
                            intentos_restantes = 3 - st.session_state.intentos_fallidos
                            st.error(f"❌ Credenciales inválidas. Te quedan {intentos_restantes} intento(s) antes del bloqueo temporal.")
    st.stop()


# --- 5. CONFIGURACIÓN DE RUTAS Y ARCHIVOS DEL NEGOCIO ACTIVO ---
negocio_seleccionado = st.session_state.get("negocio_actual", None)
if negocio_seleccionado and negocio_seleccionado != "admin_general":
    ruta_negocio = os.path.join(CLIENTES_DIR, str(negocio_seleccionado))
    os.makedirs(ruta_negocio, exist_ok=True)
    archivos_en_carpeta = os.listdir(ruta_negocio)
    archivo_base = next((os.path.join(ruta_negocio, f) for f in archivos_en_carpeta if f.startswith("BASE DE DATOS")), os.path.join(ruta_negocio, "BASE DE DATOS.xlsx"))
    archivo_compras = next((os.path.join(ruta_negocio, f) for f in archivos_en_carpeta if f.startswith("Libro_Compras")), os.path.join(ruta_negocio, "Libro_Compras.xlsx"))
else:
    ruta_negocio = CLIENTES_DIR
    archivo_base = None
    archivo_compras = None

st.session_state.negocio_seleccionado = negocio_seleccionado

# --- 6. BARRA LATERAL, PERMISOS Y MENÚ ÚNICO ---
st.sidebar.markdown(f"👤 Usuario: **{st.session_state.usuario_logueado}**")
st.sidebar.markdown(f"🏢 Negocio: *{st.session_state.nombre_empresa if 'nombre_empresa' in st.session_state else 'NINGUNO'}*")

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state.autenticado = False
    st.session_state.negocio_actual = None
    st.session_state.usuario_logueado = None
    st.session_state.es_admin_dev = False
    st.rerun()

if not st.session_state.get("es_admin_dev", False):
    st.sidebar.write("") 
    st.sidebar.link_button("💳 Renovar Licencia Mensual", "https://mpago.la/2aRRK8q", type="primary", use_container_width=True)

if not st.session_state.get("es_admin_dev", False):
    try:
        rut_actual = st.session_state.get("negocio_seleccionado") 
        res_licencia = supabase.table("empresas").select("fecha_expiracion").eq("rut_empresa", rut_actual).execute()
        
        if res_licencia and res_licencia.data:
            fecha_exp_str = res_licencia.data[0].get("fecha_expiracion")
            if fecha_exp_str and str(fecha_exp_str).strip() not in ["None", "NaT", "nan", ""]:
                hoy = date.today()
                fecha_exp_date = pd.to_datetime(str(fecha_exp_str)).date()
                dias_restantes = (fecha_exp_date - hoy).days
                
                if 0 < dias_restantes <= 5:
                    st.sidebar.warning(f"⚠️ **Atención:** Tu licencia expira en **{dias_restantes} días**.")
                elif dias_restantes == 0:
                    st.sidebar.error("🚨 **Último día:** Tu licencia expira **HOY**.")
                elif dias_restantes < 0:
                    st.sidebar.error(f"🚫 **Licencia Expirada** hace {abs(dias_restantes)} días. Tu acceso será suspendido a la brevedad.")
    except Exception as e:
        pass

st.sidebar.divider()

def cargar_permisos():
    if os.path.exists(PERMISOS_FILE):
        with open(PERMISOS_FILE, "r") as f:
            return json.load(f)
    return {}

def guardar_permisos(datos):
    with open(PERMISOS_FILE, "w") as f:
        json.dump(datos, f, indent=4)

modulos_totales = [
    "🏠 Home / Bienvenida",
    "📊 Dashboard Ejecutivo",
    "📦 Inventario y Productos",
    "💰 Módulo de Ventas (POS)",
    "🛒 Registrar Compra (CPP)",
    "📉 Mermas y Ajustes",
    "📈 Informes y Movimientos (Kardex)",
    "⚠️ Control y Gestión de Inventario",
    "📊 Módulo de Finanzas",
    "📒 Cuadratura Diaria",
    "📑 Cuentas por Cobrar",
    "📈 Reportes y Analítica",
    "🏦 Conciliación y Retiros Seguros",
    "⚙️ Configuración General"
]
if st.session_state.get("es_admin_dev", False):
    modulos_totales.append("🔑 Control Maestro de Licencias")

ROLES_PERMISOS = {
    "Administrador": modulos_totales,
    "Cajero / Vendedor": [
        "🏠 Home / Bienvenida",
        "💰 Módulo de Ventas (POS)",
        "📒 Cuadratura Diaria"
    ],
    "Bodeguero": [
        "🏠 Home / Bienvenida",
        "📦 Inventario y Productos",
        "🛒 Registrar Compra (CPP)",
        "⚠️ Control y Gestión de Inventario",
        "📉 Mermas y Ajustes"
    ]
}

def obtener_modulos_permitidos(negocio_id, rol_usuario, es_dev):
    if es_dev:
        return modulos_totales
    db_permisos = cargar_permisos()
    modulos_licencia_negocio = db_permisos.get(negocio_id, {mod: True for mod in modulos_totales})
    modulos_del_rol = ROLES_PERMISOS.get(rol_usuario, modulos_totales)
    modulos_finales = [m for m in modulos_totales if modulos_licencia_negocio.get(m, True) and m in modulos_del_rol]
    return modulos_finales

if st.session_state.es_admin_dev:
    with st.sidebar.expander("🛠️ Panel de Desarrollador (Licencias y Mantenimiento)"):
        st.success("✔️ Modo Desarrollador Activo")
        tab_lic, tab_crear, tab_mant = st.tabs(["⚙️ Licencias", "➕ Crear Negocio", "🧹 Mantenimiento"])
        
        with tab_lic:
            negocio_a_modificar = st.selectbox("Selecciona Negocio:", negocios_disponibles, key="sel_dev_negocio_nico")
            db_permisos = cargar_permisos()
            if negocio_a_modificar not in db_permisos:
                db_permisos[negocio_a_modificar] = {mod: True for mod in modulos_totales}
           
            with st.form(f"form_licencia_dev_{negocio_a_modificar}"):
                permisos_temporales = {}
                for mod in modulos_totales:
                    estado_actual = db_permisos[negocio_a_modificar].get(mod, True)
                    permisos_temporales[mod] = st.checkbox(mod, value=estado_actual, key=f"chk_dev_{negocio_a_modificar}_{mod}")
               
                if st.form_submit_button("💾 Guardar Licencia"):
                    db_permisos[negocio_a_modificar] = permisos_temporales
                    guardar_permisos(db_permisos)
                    st.success("✅ ¡Licencia actualizada!")
                    st.rerun()

        with tab_crear:
            with st.form("form_crear_cliente_dev_unico"):
                id_negocio = st.text_input("ID Carpeta / RUT (ej: 77297004-8)", key="input_id_neg")
                nombre_comercial = st.text_input("Nombre Comercial / Razón Social", key="input_nom_neg")
                password_cliente = st.text_input("Contraseña / RUT", type="password", key="input_pass_neg")
                fecha_exp = st.date_input("Fecha de Expiración Inicial", value=date(2026, 12, 31), key="input_fech_neg")
               
                guardar_nuevo = st.form_submit_button("💾 Crear y Guardar Negocio")
               
                if guardar_nuevo:
                    if not id_negocio or not nombre_comercial:
                        st.warning("⚠️ Debes completar el ID y el Nombre.")
                    else:
                        datos_nuevo = {
                            "nombre": nombre_comercial,
                            "password": password_cliente,
                            "fecha_expiracion": str(fecha_exp),
                            "activo": True,
                            "modulos": {mod: True for mod in modulos_totales}
                        }
                        guardar_nuevo_cliente(id_negocio, datos_nuevo)
                        
                        db_permisos = cargar_permisos()
                        db_permisos[id_negocio] = {mod: True for mod in modulos_totales}
                        guardar_permisos(db_permisos)
                        
                        try:
                            supabase.table("empresas").insert({
                                "rut_empresa": id_negocio,
                                "empresa_nombre": nombre_comercial,
                                "fecha_expiracion": str(fecha_exp),
                                "licencia_activa": True
                            }).execute()
                        except Exception as e:
                            pass 
                        
                        st.success(f"✨ ¡Negocio '{nombre_comercial}' creado y sincronizado con Supabase!")
                        st.rerun()

        with tab_mant:
            st.markdown("#### 🧹 Reseteo y Limpieza Remota")
            negocio_a_limpiar = st.selectbox("Selecciona Negocio a Gestionar:", negocios_disponibles, key="limpiar_negocio_sel_nico")
            dir_cliente_objetivo = os.path.join(CLIENTES_DIR, negocio_a_limpiar)
            st.warning("⚠️ **Zona de Peligro:** La opción de fábrica eliminará todos los registros locales.")
            confirmar_borrado = st.checkbox("Confirmo que deseo restablecer este negocio a versión de fábrica", key="chk_confirmar_fabrica")

            if st.button("🚨 Restablecer a Versión de Fábrica (Borrar Todo)", type="primary", key="btn_version_fabrica"):
                if not confirmar_borrado:
                    st.error("❌ Debes marcar la casilla de confirmación para autorizar el reseteo.")
                else:
                    try:
                        import shutil
                        for archivo in os.listdir(dir_cliente_objetivo):
                            ruta_archivo = os.path.join(dir_cliente_objetivo, archivo)
                            if os.path.isfile(ruta_archivo) and archivo != "logo_empresa.png":
                                os.remove(ruta_archivo)
                        for carpeta_sub in ["archivador_ventas", "archivador_compras"]:
                            dir_sub = os.path.join(dir_cliente_objetivo, carpeta_sub)
                            if os.path.exists(dir_sub):
                                shutil.rmtree(dir_sub)
                        st.success(f"✨ ¡Negocio '{negocio_a_limpiar}' restablecido a versión de fábrica con éxito!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Ocurrió un error al restablecer: {e}")

st.sidebar.markdown("---")
st.sidebar.markdown("© 2026 CREC-ERP")
st.sidebar.markdown("Desarrollado por **Sebastián Calderón**")

# --- 7. INICIALIZACIÓN DE ESTADOS DE SESIÓN ---
if "menu_seleccionado" not in st.session_state:
    st.session_state.menu_seleccionado = "🏠 Home / Bienvenida"
if "carrito_ventas" not in st.session_state:
    st.session_state.carrito_ventas = []
if "ejecutar_cobro" not in st.session_state:
    st.session_state.ejecutar_cobro = False
if "estado_pago" not in st.session_state:
    st.session_state.estado_pago = False
if "ultimo_recibo" not in st.session_state:
    st.session_state.ultimo_recibo = None
if "formas_pago_erp" not in st.session_state:
    st.session_state.formas_pago_erp = [
        "Efectivo", "Tarjeta de Débito", "Tarjeta de Crédito", 
        "Transferencia Electrónica", "Cheque", "Cuenta Corriente / Crédito Directo"
    ]

rol_actual = st.session_state.get('rol_usuario', 'Administrador')
lista_modulos_permitidos = obtener_modulos_permitidos(negocio_seleccionado, rol_actual, st.session_state.es_admin_dev)
if st.session_state.get("es_admin_dev", False) and "🔑 Control Maestro de Licencias" not in lista_modulos_permitidos:
    lista_modulos_permitidos.append("🔑 Control Maestro de Licencias")

if not lista_modulos_permitidos:
    lista_modulos_permitidos = ["🏠 Home / Bienvenida"]

menu = st.sidebar.selectbox(
    "🧭 Selecciona un Módulo:",
    lista_modulos_permitidos,
    index=lista_modulos_permitidos.index(st.session_state.menu_seleccionado) if st.session_state.menu_seleccionado in lista_modulos_permitidos else 0
)
st.session_state.menu_seleccionado = menu

query_params = st.query_params
param_caja = query_params.get("caja", None)

if param_caja:
    menu = "💰 Módulo de Ventas (POS)"
    st.sidebar.info(f"🖥️ Modo Terminal Activo: **{param_caja}**")

def cargar_datos(path_db):
    if os.path.exists(path_db):
        df = pd.read_excel(path_db, dtype={'Código': str})
        if 'Activo' in df.columns:
            df = df[df['Activo'].astype(str).str.strip().str.capitalize() == 'Si']
        return df
    return None

df_base = cargar_datos(archivo_base) if ('archivo_base' in globals() and archivo_base) else None

def mostrar_encabezado_con_home(titulo_modulo):
    col_titulo, col_btn = st.columns([4, 1])
    with col_titulo:
        nombre_mostrar = st.session_state.get('nombre_empresa', negocio_seleccionado)
        st.subheader(f"{titulo_modulo} (Negocio: {nombre_mostrar})")
    with col_btn:
        st.write("")
        if st.button("🏠 Volver al Home", use_container_width=True):
            st.session_state.menu_seleccionado = "🏠 Home / Bienvenida"
            st.rerun()

# --- 8. RENDERIZADO DEL HOME FIJO Y MÓDULOS ---
if menu == "🏠 Home / Bienvenida":
    st.markdown(f"<p class='main-title'>🪙 CREC-ERP: {st.session_state.nombre_empresa if 'nombre_empresa' in st.session_state else 'GENERAL'}</p>", unsafe_allow_html=True)
    st.markdown("<p class='sub-title'>Selecciona un módulo para comenzar:</p>", unsafe_allow_html=True)
   
    # 🚀 BOTÓN FORZADO EXCLUSIVO PARA EL DESARROLLADOR
    if st.session_state.get("es_admin_dev", False):
        st.error("🛠️ **PANEL DE CONTROL MAESTRO**")
        if st.button("🔑 ABRIR CONTROL DE LICENCIAS Y CLIENTES", type="primary", use_container_width=True):
            st.session_state.menu_seleccionado = "🔑 Control Maestro de Licencias"
            st.rerun()
        st.divider()

    modulos_disponibles_home = [
        {"id": "dash", "nombre_ref": "Dashboard Ejecutivo", "label": "📊 Dashboard Ejecutivo"},
        {"id": "inv", "nombre_ref": "Inventario y Productos", "label": "📦 Inventario y Productos"},
        {"id": "pos", "nombre_ref": "Módulo de Ventas (POS)", "label": "💰 Módulo de Ventas (POS)"},
        {"id": "comp", "nombre_ref": "Registrar Compra (CPP)", "label": "🛒 Registrar Compra (CPP)"},
        {"id": "mermas", "nombre_ref": "Mermas y Ajustes", "label": "📉 Mermas y Ajustes"},
        {"id": "inf", "nombre_ref": "Informes y Movimientos (Kardex)", "label": "📋 Informes y Movimientos"},
        {"id": "ctrl", "nombre_ref": "Control y Gestión de Inventario", "label": "⚠️ Control y Gestión de Inventario"},
        {"id": "fin", "nombre_ref": "Módulo de Finanzas", "label": "📊 Módulo de Finanzas"},
        {"id": "cuadratura", "nombre_ref": "Cuadratura Diaria", "label": "📒 Cuadratura Diaria"},
        {"id": "cobrar", "nombre_ref": "Cuentas por Cobrar", "label": "📑 Cuentas por Cobrar"},
        {"id": "conci", "nombre_ref": "Conciliación y Retiros Seguros", "label": "🏦 Conciliación y Retiros Seguros"},
        {"id": "report", "nombre_ref": "Reportes y Analítica", "label": "📈 Reportes y Analítica"},
        {"id": "conf", "nombre_ref": "Configuración General", "label": "⚙️ Configuración General"}
    ]

    botones_activos = []
    for mod in modulos_disponibles_home:
        permitido = any(mod["nombre_ref"].lower() in str(p).lower() for p in lista_modulos_permitidos)
        if permitido:
            botones_activos.append(mod)

    if botones_activos:
        num_columnas = 2
        for i in range(0, len(botones_activos), num_columnas):
            fila_mods = botones_activos[i:i + num_columnas]
            cols = st.columns(num_columnas)
            for idx_col, mod in enumerate(fila_mods):
                with cols[idx_col]:
                    if st.button(mod["label"], use_container_width=True, key=f"btn_home_{mod['id']}"):
                        nombre_destino = next((p for p in lista_modulos_permitidos if mod["nombre_ref"].lower() in str(p).lower()), mod["nombre_ref"])
                        st.session_state.menu_seleccionado = nombre_destino
                        st.rerun()
    else:
        st.info("ℹ️ Tu licencia actual no tiene módulos activos asignados.")

# --- 9. RENDERIZADO DE MÓDULOS DE INVENTARIO Y REGISTROS ---
elif menu == "📦 Inventario y Productos":
    mostrar_encabezado_con_home("📦 Administración de Inventario")
    
    tab_inv1, tab_inv2, tab_inv3 = st.tabs(["📦 Productos", "👥 Clientes", "🚚 Proveedores"])
    
    with tab_inv1:
        st.markdown("#### ➕ Registrar o Gestionar Productos")
        rut_actual = st.session_state.get("negocio_seleccionado")
        
        try:
            res_inv = supabase.table("productos").select("*").eq("rut_empresa", rut_actual).execute()
            df_inv = pd.DataFrame(res_inv.data)
            st.success(f"Base de datos conectada con éxito desde la Nube. ({len(df_inv)} productos)")
            if not df_inv.empty:
                st.dataframe(df_inv, use_container_width=True)
            
            with st.form("form_nuevo_producto", clear_on_submit=True):
                st.markdown("##### Nuevo Producto")
                c_cod = st.text_input("Código")
                c_desc = st.text_input("Descripción")
                c_costo = st.number_input("Costo ($)", min_value=0.0, step=100.0)
                c_pv = st.number_input("Precio de Venta ($)", min_value=0.0, step=100.0)
                c_stock = st.number_input("Stock Inicial", min_value=0, step=1)
                
                btn_g_prod = st.form_submit_button("💾 Guardar Producto")
                if btn_g_prod:
                    if not c_cod or not c_desc:
                        st.warning("⚠️ Ingresa el código y la descripción.")
                    else:
                        nuevo_p = {
                            "rut_empresa": rut_actual,
                            "codigo": str(c_cod),
                            "descripcion": c_desc,
                            "costo": c_costo,
                            "precio_venta": c_pv,
                            "stock": c_stock
                        }
                        supabase.table("productos").upsert(nuevo_p, on_conflict="rut_empresa, codigo").execute()
                        st.success("✅ ¡Producto registrado con éxito en la Nube!")
                        st.rerun()
        except Exception as e:
            st.error(f"⚠️ Error al conectar con Supabase: {e}")

    with tab_inv2:
            st.markdown("#### 👥 Maestro de Clientes")
            
            # 1. Cargar clientes directamente desde Supabase filtrando por la empresa actual
            df_clientes = pd.DataFrame()
            try:
                res_cli = supabase.table("clientes").select("*").eq("id_negocio", rut_actual).execute()
                if res_cli.data:
                    # Mapeamos los campos para que la tabla muestre los nombres correctos
                    df_clientes = pd.DataFrame(res_cli.data)
                    # Aseguramos nombres de columnas estandarizados si vienen con otro nombre de la nube
                    renames = {}
                    if "nombre" in df_clientes.columns and "Nombre_Cliente" not in df_clientes.columns:
                        renames["nombre"] = "Nombre_Cliente"
                    if "direccion" in df_clientes.columns and "Direccion" not in df_clientes.columns:
                        renames["direccion"] = "Direccion"
                    if renames:
                        df_clientes = df_clientes.rename(columns=renames)
            except Exception as e:
                st.error(f"⚠️ Error cargando clientes desde la nube: {e}")

            st.dataframe(df_clientes, use_container_width=True)
            
            with st.form("form_nuevo_cliente_local", clear_on_submit=True):
                st.markdown("##### Registrar Cliente Nuevo")
                cl_nom = st.text_input("Nombre / Razón Social")
                cl_rut = st.text_input("RUT / Identificación")
                cl_tel = st.text_input("Teléfono")
                cl_mail = st.text_input("Correo Electrónico")
                cl_dir = st.text_input("Dirección")
                
                btn_g_cliente = st.form_submit_button("💾 Guardar Cliente")
                if btn_g_cliente:
                    if not cl_nom or not cl_rut:
                        st.warning("⚠️ Debes ingresar al menos el nombre y el RUT del cliente.")
                    else:
                        # 2. Preparamos el diccionario para subirlo directo a Supabase
                        nuevo_cliente_nube = {
                        "rut": str(cl_rut).strip(),
                        "nombre": str(cl_nom).strip(),
                        "telefono": str(cl_tel).strip(),
                        "correo": str(cl_mail).strip(),  # <-- Cambiado de "email" a "correo"
                        "direccion": str(cl_dir).strip(),
                        "id_negocio": str(rut_actual).strip()
                    }
                        
                        try:
                            # 3. Guardado directo en la tabla 'clientes' de Supabase
                            supabase.table("clientes").upsert(nuevo_cliente_nube, on_conflict="rut").execute()
                            st.success("✅ ¡Cliente guardado con éxito en la nube!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al guardar en Supabase: {e}")

    with tab_inv3:
        st.markdown("#### 🚚 Directorio de Proveedores")
        
        # 1. Cargar proveedores directamente desde Supabase filtrando por el negocio activo
        df_proveedores = pd.DataFrame()
        try:
            res_prov = supabase.table("proveedores").select("*").eq("id_negocio", rut_actual).execute()
            if res_prov.data:
                df_proveedores = pd.DataFrame(res_prov.data)
                # Normalizamos las columnas para que la tabla se dibuje correctamente en la interfaz
                renames_prov = {}
                if "nombre" in df_proveedores.columns and "Nombre_Proveedor" not in df_proveedores.columns:
                    renames_prov["nombre"] = "Nombre_Proveedor"
                if "rut" in df_proveedores.columns and "Rut" not in df_proveedores.columns:
                    renames_prov["rut"] = "Rut"
                if "contacto" in df_proveedores.columns and "Contacto" not in df_proveedores.columns:
                    renames_prov["contacto"] = "Contacto"
                if "telefono" in df_proveedores.columns and "Telefono" not in df_proveedores.columns:
                    renames_prov["telefono"] = "Telefono"
                if "email" in df_proveedores.columns and "Email" not in df_proveedores.columns:
                    renames_prov["email"] = "Email"
                if renames_prov:
                    df_proveedores = df_proveedores.rename(columns=renames_prov)
        except Exception as e:
            st.error(f"⚠️ Error cargando proveedores desde la nube: {e}")

        st.dataframe(df_proveedores, use_container_width=True)
        
        with st.form("form_nuevo_proveedor_nube", clear_on_submit=True):
            st.markdown("##### Registrar Proveedor Nuevo")
            pr_nom = st.text_input("Nombre del Proveedor")
            pr_rut = st.text_input("RUT Proveedor")
            pr_cont = st.text_input("Persona de Contacto")
            pr_tel = st.text_input("Teléfono")
            pr_mail = st.text_input("Email")
            
            btn_g_prov = st.form_submit_button("💾 Guardar Proveedor")
            if btn_g_prov:
                if not pr_nom or not pr_rut:
                    st.warning("⚠️ Debes ingresar al menos el nombre y el RUT del proveedor.")
                else:
                    # 2. Preparamos el registro para subirlo directamente a Supabase
                    nuevo_proveedor_nube = {
                        "rut": str(pr_rut).strip(),
                        "nombre": str(pr_nom).strip(),
                        "contacto": str(pr_cont).strip(),
                        "telefono": str(pr_tel).strip(),
                        "correo": str(pr_mail).strip(),  # <-- Cambiado de "email" a "correo"
                        "id_negocio": str(rut_actual).strip()
                    }
                    
                    try:
                        # 3. Guardado directo en la tabla 'proveedores' de Supabase
                        supabase.table("proveedores").insert(nuevo_proveedor_nube).execute()
                        st.success("✅ ¡Proveedor guardado con éxito en la nube!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al guardar en Supabase: {e}")

                    

elif menu == "📊 Módulo de Finanzas":
    mostrar_encabezado_con_home("📊 Panel de Control Financiero")
    tab_fin1, tab_fin2, tab_fin3 = st.tabs(["💳 Cuentas por Pagar", "📅 Calendario de Pagos", "📋 Registro de Gastos"])
    with tab_fin1:
        mostrar_modulo_cuentas_por_pagar(ruta_negocio)
    with tab_fin2:
        mostrar_modulo_calendario_pagos(ruta_negocio)
    with tab_fin3:
        mostrar_modulo_registro_gastos(supabase)

elif menu == "📒 Cuadratura Diaria":
    mostrar_encabezado_con_home("📒 Cuadratura Diaria")
    mostrar_modulo_cuadratura_diaria(ruta_negocio)

elif menu == "📑 Cuentas por Cobrar":
    mostrar_modulo_cuentas_por_cobrar(ruta_negocio)

# ----------------- SECCIÓN DASHBOARD EJECUTIVO -----------------
elif menu == "📊 Dashboard Ejecutivo":
    mostrar_encabezado_con_home("⚡ Resumen Ejecutivo en Tiempo Real")
   
    # 🕒 Selector de Período Temporal en Tiempo Real
    st.markdown("### 🎛️ Filtro Temporal de Análisis")
    col_f1, col_f2 = st.columns([2, 2])
    with col_f1:
        periodo_seleccionado = st.selectbox(
            "Selecciona el período a visualizar:",
            options=["Diaria (Hoy)", "Semanal (Últimos 7 días)", "Quincenal (Últimos 15 días)", "Mensual (Últimos 30 días)", "Histórico Completo"],
            index=3
        )

    hoy_dt = pd.to_datetime(date.today())
    if periodo_seleccionado == "Diaria (Hoy)":
        fecha_limite = hoy_dt
    elif periodo_seleccionado == "Semanal (Últimos 7 días)":
        fecha_limite = hoy_dt - pd.Timedelta(days=7)
    elif periodo_seleccionado == "Quincenal (Últimos 15 días)":
        fecha_limite = hoy_dt - pd.Timedelta(days=15)
    elif periodo_seleccionado == "Mensual (Últimos 30 días)":
        fecha_limite = hoy_dt - pd.Timedelta(days=30)
    else:
        fecha_limite = None

    archivo_gastos = os.path.join(ruta_negocio, "Registro_Gastos.xlsx")
    archivo_cxp = os.path.join(ruta_negocio, "Cuentas_por_Cobrar.xlsx")
    archivo_cpp = os.path.join(ruta_negocio, "Cuentas_Por_Pagar.xlsx")
    archivo_cuadratura = os.path.join(ruta_negocio, "Cuadratura_Diaria.xlsx")

    # 1. Cálculo de Ventas Filtradas por Período
    archivos_v = [f for f in os.listdir(ruta_negocio) if f.startswith("Libro_Ventas_") and f.endswith(".xlsx")]
    total_ventas_periodo = 0.0
    if archivos_v:
        for ar in archivos_v:
            path_v = os.path.join(ruta_negocio, ar)
            df_temp_v = pd.read_excel(path_v)
            if not df_temp_v.empty:
                col_fecha = next((c for c in df_temp_v.columns if 'fecha' in str(c).lower() or 'timestamp' in str(c).lower()), None)
                if col_fecha and fecha_limite is not None:
                    df_temp_v['Fecha_Parsed'] = pd.to_datetime(df_temp_v[col_fecha], errors='coerce')
                    if periodo_seleccionado == "Diaria (Hoy)":
                        df_temp_v = df_temp_v[df_temp_v['Fecha_Parsed'].dt.date == hoy_dt.date()]
                    else:
                        df_temp_v = df_temp_v[df_temp_v['Fecha_Parsed'] >= fecha_limite]
                
                col_tot = next((c for c in df_temp_v.columns if 'total' in str(c).lower()), None)
                if col_tot and not df_temp_v.empty:
                    if "TransaccionID" in df_temp_v.columns:
                        total_ventas_periodo += df_temp_v.drop_duplicates(subset=["TransaccionID"])[col_tot].sum()
                    else:
                        total_ventas_periodo += df_temp_v[col_tot].sum()

    # 2. Cálculo de Gastos Filtrados por Período
    total_gastos_periodo = 0.0
    df_g_filtrado = pd.DataFrame()
    if os.path.exists(archivo_gastos):
        df_g = pd.read_excel(archivo_gastos)
        if not df_g.empty and 'Monto' in df_g.columns:
            if 'Fecha' in df_g.columns and fecha_limite is not None:
                df_g['Fecha_Parsed'] = pd.to_datetime(df_g['Fecha'], errors='coerce')
                if periodo_seleccionado == "Diaria (Hoy)":
                    df_g_filtrado = df_g[df_g['Fecha_Parsed'].dt.date == hoy_dt.date()]
                else:
                    df_g_filtrado = df_g[df_g['Fecha_Parsed'] >= fecha_limite]
            else:
                df_g_filtrado = df_g.copy()
            
            total_gastos_periodo = df_g_filtrado['Monto'].sum()

    # 3. Cálculo de Inventario y Ganancia Potencial desde la Nube
    try:
        res_prod = supabase.table("productos").select("costo, precio_venta, stock").eq("rut_empresa", st.session_state.negocio_seleccionado).limit(10000).execute()
        if res_prod.data:
            df_prod_nube = pd.DataFrame(res_prod.data)
            df_prod_nube['costo'] = pd.to_numeric(df_prod_nube['costo'], errors='coerce').fillna(0)
            df_prod_nube['precio_venta'] = pd.to_numeric(df_prod_nube['precio_venta'], errors='coerce').fillna(0)
            df_prod_nube['stock'] = pd.to_numeric(df_prod_nube['stock'], errors='coerce').fillna(0)

            inversion_total = (df_prod_nube['costo'] * df_prod_nube['stock']).sum()
            valor_venta_total = (df_prod_nube['precio_venta'] * df_prod_nube['stock']).sum()
            ganancia_potencial = valor_venta_total - inversion_total
            total_productos = len(df_prod_nube)
        else:
            inversion_total = valor_venta_total = ganancia_potencial = 0.0
            total_productos = 0
    except Exception as e:
        inversion_total = valor_venta_total = ganancia_potencial = 0.0
        total_productos = 0

    utilidad_neta_estimada = total_ventas_periodo - total_gastos_periodo

    st.divider()

    # --- BLOQUE DE KPIS SUPERIORES ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label=f"💰 Venta ({periodo_seleccionado.split()[0]})", value=f"${total_ventas_periodo:,.2f}")
    with col2:
        st.metric(label=f"📉 Gastos ({periodo_seleccionado.split()[0]})", value=f"${total_gastos_periodo:,.2f}", delta="Egresos", delta_color="inverse")
    with col3:
        st.metric(label=f"💼 Utilidad Est. ({periodo_seleccionado.split()[0]})", value=f"${utilidad_neta_estimada:,.2f}", delta="Margen")
    with col4:
        st.metric(label="📦 Total Productos", value=total_productos)

    st.divider()

    # --- BLOQUE DE INVENTARIO ---
    col_inv1, col_inv2, col_inv3 = st.columns(3)
    with col_inv1:
        st.metric(label="📉 Inversión Total (Costo)", value=f"${inversion_total:,.2f}")
    with col_inv2:
        st.metric(label="📈 Valor Venta Potencial", value=f"${valor_venta_total:,.2f}")
    with col_inv3:
        st.metric(label="💰 Ganancia Potencial", value=f"${ganancia_potencial:,.2f}")

    st.divider()

    # --- GRÁFICOS Y TENDENCIAS INTERACTIVAS ---
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("#### 📈 Evolución Diaria de Ingresos (Cuadratura)")
        if os.path.exists(archivo_cuadratura):
            df_cuat = pd.read_excel(archivo_cuadratura)
            if not df_cuat.empty and 'Fecha' in df_cuat.columns and 'VentaTotal' in df_cuat.columns:
                if fecha_limite is not None and periodo_seleccionado != "Histórico Completo":
                    df_cuat['Fecha_Parsed'] = pd.to_datetime(df_cuat['Fecha'], errors='coerce')
                    if periodo_seleccionado == "Diaria (Hoy)":
                        df_cuat = df_cuat[df_cuat['Fecha_Parsed'].dt.date == hoy_dt.date()]
                    else:
                        df_cuat = df_cuat[df_cuat['Fecha_Parsed'] >= fecha_limite]
                
                if not df_cuat.empty:
                    st.line_chart(df_cuat.set_index('Fecha')['VentaTotal'])
                else:
                    st.info("ℹ️ No hay registros de cuadratura en este período.")
            else:
                st.info("ℹ️ Sin datos de cuadratura diarios.")
        else:
            st.info("ℹ️ Archivo de cuadratura no encontrado.")

    with col_g2:
        st.markdown("#### 📊 Distribución de Gastos por Categoría")
        with st.expander("💡 ¿Qué significa este gráfico y por qué es importante?"):
            st.write("""
            **¿Qué mide exactamente?** 
            Te muestra de forma visual en qué se está yendo el dinero de tu negocio, calculando qué porcentaje del total de tus egresos corresponde a cada categoría.
            
            **¿Por qué es clave para tu éxito?**
            * **Detección de fugas:** Si la categoría *Gastos Operativos* (arriendo, luz, sueldos) domina la gráfica, significa que los costos fijos de mantener tu local están muy altos.
            * **Equilibrio sano:** Lo ideal en tu negocio es que la porción más grande de esta gráfica sea siempre la **Mercadería**, ya que esa es la inversión que te generará ventas y ganancias reales.
            """)
        if not df_g_filtrado.empty and 'Categoria' in df_g_filtrado.columns and 'Monto' in df_g_filtrado.columns:
            df_cat = df_g_filtrado.groupby('Categoria')['Monto'].sum().reset_index()
            
            fig_dona = px.pie(
                df_cat, 
                values='Monto', 
                names='Categoria', 
                hole=0.65,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            
            fig_dona.update_traces(
                textposition='inside', 
                textinfo='percent', 
                hovertemplate="<b>%{label}</b><br>Gasto: $%{value:,.0f}<br>Porcentaje: %{percent}<extra></extra>"
            )
            
            fig_dona.update_layout(
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
                margin=dict(t=10, b=10, l=0, r=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            
            st.plotly_chart(fig_dona, use_container_width=True)
        else:
            st.info("ℹ️ No hay registros de gastos para el período seleccionado.")

    st.divider()
    st.markdown("### 🔔 Alertas y Salud Financiera del Negocio")
    
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        if total_gastos_periodo > (total_ventas_periodo * 0.7) and total_ventas_periodo > 0:
            st.error("⚠️ **Alerta Financiera:** Los gastos operativos superan el 70% de las ventas en este período.")
        else:
            st.success("✅ **Salud Financiera Estable:** Niveles de gastos controlados para el período analizado.")
            
    with col_a2:
        if os.path.exists(archivo_cpp):
            df_prov_pend = pd.read_excel(archivo_cpp)
            pendientes = df_prov_pend[df_prov_pend.get('Estado', '') == 'PENDIENTE'] if 'Estado' in df_prov_pend.columns else pd.DataFrame()
            if not pendientes.empty:
                st.warning(f"⚠️ Tienes **{len(pendientes)} factura(s) pendiente(s)** de pago a proveedores.")
            else:
                st.info("ℹ️ No hay facturas de proveedores pendientes de pago.")
        else:
            st.info("ℹ️ Módulo de cuentas por pagar sin registros activos.")

# ----------------- SECCIÓN INVENTARIO GENERAL -----------------
elif menu == "📦 Inventario y Productos":
    mostrar_encabezado_con_home("Gestión de Bases de Datos")
   
    tab_prod, tab_cli, tab_prov = st.tabs(["📦 Productos / Inventario", "👥 Clientes", "🚚 Proveedores"])
   
    with tab_prod:
        st.markdown("### 📦 Administración de Productos (Nube)")
        rut_actual = st.session_state.get("negocio_seleccionado")
        try:
            res_inv2 = supabase.table("productos").select("*").eq("rut_empresa", rut_actual).limit(10000).execute()
            df_base_nube = pd.DataFrame(res_inv2.data)
            st.success(f"✅ Base de datos conectada con éxito. Total de productos registrados: {len(df_base_nube)}")
           
            st.markdown("#### 📂 Listado General de Inventario")
            if not df_base_nube.empty:
                h1, h2, h3, h4, h5, h6 = st.columns([2, 3, 1, 1, 1, 0.8])
                with h1: st.markdown("**Código**")
                with h2: st.markdown("**Descripción**")
                with h3: st.markdown("**Costo**")
                with h4: st.markdown("**Precio Venta**")
                with h5: st.markdown("**Stock**")
                with h6: st.markdown("**Acción**")
                st.markdown("---")

                for idx_p, row_p in df_base_nube.iterrows():
                    val_cod = str(row_p.get('codigo', ''))
                    val_desc = str(row_p.get('descripcion', ''))
                    val_costo = float(row_p.get('costo', 0))
                    val_precio = float(row_p.get('precio_venta', 0))
                    val_stock = float(row_p.get('stock', 0))

                    c1, c2, c3, c4, c5, c6 = st.columns([2, 3, 1, 1, 1, 0.8])
                    with c1: st.write(val_cod)
                    with c2: st.write(val_desc)
                    with c3: st.write(f"${val_costo:,.0f}")
                    with c4: st.write(f"${val_precio:,.0f}")
                    with c5: st.write(str(val_stock))
                    with c6:
                        if st.button("🗑️", key=f"del_prod_inv2_{val_cod}", help="Eliminar este producto"):
                            supabase.table("productos").delete().eq("rut_empresa", rut_actual).eq("codigo", val_cod).execute()
                            st.success("✅ Producto eliminado correctamente de la Nube.")
                            st.rerun()
            else:
                st.info("ℹ️ No hay productos cargados en la base de datos.")
        except Exception as e:
            st.error(f"⚠️ Error conectando con la base de datos: {e}")
       
    with tab_cli:
        st.markdown("### 👥 Administración de Clientes")
       
        with st.form("form_nuevo_cliente", clear_on_submit=True):
            st.markdown("#### Registrar Nuevo Cliente")
            col1, col2 = st.columns(2)
            with col1:
                rut_cliente = st.text_input("RUT / Identificación")
                nombre_cliente = st.text_input("Nombre / Razón Social")
                telefono_cliente = st.text_input("Teléfono")
            with col2:
                correo_cliente = st.text_input("Correo Electrónico")
                direccion_cliente = st.text_input("Dirección")
           
            submitted = st.form_submit_button("💾 Guardar Cliente")
           
            if submitted:
                if rut_cliente and nombre_cliente:
                    nuevo_registro = {
                        "RUT": rut_cliente,
                        "Nombre": nombre_cliente,
                        "Teléfono": telefono_cliente,
                        "Correo": correo_cliente,
                        "Dirección": direccion_cliente
                    }
                   
                    path_db = archivo_base if ('archivo_base' in globals() and archivo_base) else "base_datos.xlsx"
                   
                    try:
                        df_clientes = pd.read_excel(path_db, sheet_name="BD_Clientes", dtype={'RUT': str})
                    except Exception:
                        df_clientes = pd.DataFrame(columns=["RUT", "Nombre", "Teléfono", "Correo", "Dirección"])
                   
                    if not df_clientes.empty and rut_cliente in df_clientes['RUT'].values:
                        st.error("⚠️ Ya existe un cliente registrado con este RUT.")
                    else:
                        df_nuevo = pd.DataFrame([nuevo_registro])
                        df_clientes = pd.concat([df_clientes, df_nuevo], ignore_index=True)
                       
                        with pd.ExcelWriter(path_db, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                            df_clientes.to_excel(writer, sheet_name="BD_Clientes", index=False)
                       
                        st.success(f"✅ Cliente '{nombre_cliente}' guardado exitosamente.")
                        st.rerun()
                else:
                    st.warning("⚠️ Los campos RUT y Nombre/Razón Social son obligatorios.")

        st.markdown("#### 📋 Listado de Clientes Registrados")
        path_db = archivo_base if ('archivo_base' in globals() and archivo_base) else "base_datos.xlsx"
        try:
            df_ver_clientes = pd.read_excel(path_db, sheet_name="BD_Clientes", dtype={'RUT': str})
            if not df_ver_clientes.empty:
                st.dataframe(df_ver_clientes, use_container_width=True)
            else:
                st.info("No hay clientes registrados todavía.")
        except Exception:
            st.info("Aún no se ha creado la hoja 'BD_Clientes' en el archivo Excel.")
       
    with tab_prov:
        st.markdown("### 🚚 Administración de Proveedores")
       
        with st.form("form_nuevo_proveedor", clear_on_submit=True):
            st.markdown("#### Registrar Nuevo Proveedor")
            col1, col2 = st.columns(2)
            with col1:
                rut_proveedor = st.text_input("RUT / Identificación Proveedor")
                nombre_proveedor = st.text_input("Nombre / Razón Social Proveedor")
                telefono_proveedor = st.text_input("Teléfono Proveedor")
            with col2:
                correo_proveedor = st.text_input("Correo Electrónico Proveedor")
                nombre_vendedor = st.text_input("Nombre de Vendedor")
           
            submitted_prov = st.form_submit_button("💾 Guardar Proveedor")
           
            if submitted_prov:
                if rut_proveedor and nombre_proveedor:
                    nuevo_registro_prov = {
                        "RUT": rut_proveedor,
                        "Nombre": nombre_proveedor,
                        "Teléfono": telefono_proveedor,
                        "Correo": correo_proveedor,
                        "Vendedor": nombre_vendedor
                    }
                   
                    path_db = archivo_base if ('archivo_base' in globals() and archivo_base) else "base_datos.xlsx"
                   
                    try:
                        df_proveedores = pd.read_excel(path_db, sheet_name="BD_Proveedores", dtype={'RUT': str})
                    except Exception:
                        df_proveedores = pd.DataFrame(columns=["RUT", "Nombre", "Teléfono", "Correo", "Vendedor"])
                   
                    if not df_proveedores.empty and rut_proveedor in df_proveedores['RUT'].values:
                        st.error("⚠️ Ya existe un proveedor registrado con este RUT.")
                    else:
                        df_nuevo_p = pd.DataFrame([nuevo_registro_prov])
                        df_proveedores = pd.concat([df_proveedores, df_nuevo_p], ignore_index=True)
                       
                        with pd.ExcelWriter(path_db, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                            df_proveedores.to_excel(writer, sheet_name="BD_Proveedores", index=False)
                       
                        st.success(f"✅ Proveedor '{nombre_proveedor}' guardado exitosamente.")
                        st.rerun()
                else:
                    st.warning("⚠️ Los campos RUT y Nombre/Razón Social del proveedor son obligatorios.")

        st.markdown("#### 📋 Listado de Proveedores Registrados")
        path_db = archivo_base if ('archivo_base' in globals() and archivo_base) else "base_datos.xlsx"
        try:
            df_ver_proveedores = pd.read_excel(path_db, sheet_name="BD_Proveedores", dtype={'RUT': str})
            if not df_ver_proveedores.empty:
                st.dataframe(df_ver_proveedores, use_container_width=True)
            else:
                st.info("No hay proveedores registrados todavía.")
        except Exception:
            st.info("Aún no se ha creado la hoja 'BD_Proveedores' en el archivo Excel.")

# ----------------- SECCIÓN MERMAS Y AJUSTES DE INVENTARIO -----------------
elif menu == "📉 Mermas y Ajustes":
    mostrar_encabezado_con_home("📉 Módulo de Control de Mermas y Ajustes de Inventario")
    st.markdown("Registra salidas extraordinarias de mercadería (roturas, vencimientos, consumo interno o mermas) para mantener tu inventario y lotes cuadrados.")

    if df_base is not None:
        col_cod = next((c for c in df_base.columns if 'código' in str(c).lower() or 'codigo' in str(c).lower() or 'ean' in str(c).lower()), df_base.columns[0])
        col_desc = next((c for c in df_base.columns if 'descripción' in str(c).lower() or 'nombre' in str(c).lower() or 'producto' in str(c).lower()), df_base.columns[1])
        col_stock = next((c for c in df_base.columns if 'stock' in str(c).lower() or 'cantidad' in str(c).lower()), None)

        if col_stock:
            st.markdown("### 📋 Registro de Salida por Merma o Ajuste")

            metodo_busqueda_merma = st.radio("Método para buscar producto:", ["⌨️ Escáner / Pistola Láser (Código)", "🔎 Buscar por Nombre / Palabra Clave"], horizontal=True, key="radio_merma")
           
            prod_seleccionado_merma = None
            opciones_productos_merma = ["-- Selecciona un producto --"] + [f"{row[col_cod]} - {row[col_desc]}" for idx, row in df_base.iterrows()]

            if metodo_busqueda_merma == "⌨️ Escáner / Pistola Láser (Código)":
                codigo_buscado_m = st.text_input("Pistola láser / Digitar Código EAN:", key="input_pistola_merma")
                if codigo_buscado_m:
                    match_pm = df_base[df_base[col_cod].astype(str) == str(codigo_buscado_m)]
                    if not match_pm.empty:
                        prod_seleccionado_merma = f"{match_pm.iloc[0][col_cod]} - {match_pm.iloc[0][col_desc]}"
                        st.success(f"✔️ Producto encontrado: {prod_seleccionado_merma}")
                    else:
                        st.warning("⚠️ No se encontró ningún producto con ese código.")
            else:
                prod_seleccionado_merma = st.selectbox("Selecciona o busca por palabra clave:", options=opciones_productos_merma, key="select_palabra_merma")

            with st.form("form_registrar_merma"):
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    cant_merma = st.number_input("Cantidad a dar de baja / Ajustar", min_value=1.0, step=1.0, value=1.0)
                with col_m2:
                    motivo_merma = st.selectbox("Motivo de la Baja", ["Merma / Rotura", "Vencimiento / Caducado", "Consumo Interno", "Ajuste por Diferencia de Inventario"])

                observacion_merma = st.text_input("Observación opcional (Ej: Rotura en pasillo, vencido del semáforo)")

                lotes_disponibles_prod = []
                codigo_p_merma = prod_seleccionado_merma.split(" - ")[0] if prod_seleccionado_merma and prod_seleccionado_merma != "-- Selecciona un producto --" else ""
               
                archivo_lotes = os.path.join(ruta_negocio, "base_lotes.xlsx") if 'ruta_negocio' in globals() else "base_lotes.xlsx"
                if os.path.exists(archivo_lotes) and codigo_p_merma:
                    df_lotes_check = pd.read_excel(archivo_lotes, dtype={'Código': str})
                    df_lotes_prod = df_lotes_check[(df_lotes_check['Código'].astype(str) == str(codigo_p_merma)) & (df_lotes_check['CantidadDisponible'] > 0)]
                    if not df_lotes_prod.empty:
                        lotes_disponibles_prod = [f"Lote: {row['Lote']} (Disponibles: {row['CantidadDisponible']} - Vence: {row['FechaVencimiento']})" for idx, row in df_lotes_prod.iterrows()]

                lote_seleccionado_str = "N/A"
                if lotes_disponibles_prod:
                    st.markdown("📌 **Este producto tiene lotes activos. Selecciona a qué lote descontar:**")
                    lote_seleccionado_str = st.selectbox("Lote afectado", options=lotes_disponibles_prod)

                btn_ejecutar_merma = st.form_submit_button("📉 Registrar Merma y Descontar de Inventario", type="primary")

                if btn_ejecutar_merma:
                    if not prod_seleccionado_merma or prod_seleccionado_merma == "-- Selecciona un producto --":
                        st.warning("⚠️ Debes seleccionar un producto válido.")
                    elif cant_merma <= 0:
                        st.warning("⚠️ La cantidad debe ser mayor a 0.")
                    else:
                        codigo_p_merma = prod_seleccionado_merma.split(" - ")[0]
                        desc_p_merma = prod_seleccionado_merma.split(" - ")[1]

                        try:
                            # 1. Consultar el producto directamente en Supabase para obtener su stock actual real
                            res_prod = supabase.table("productos").select("*").eq("rut_empresa", rut_actual).eq("codigo", str(codigo_p_merma)).execute()
                            
                            if res_prod.data:
                                prod_data = res_prod.data[0]
                                stock_actual_nube = float(prod_data.get("stock", 0) or 0.0)
                                
                                # Validar que haya suficiente stock
                                if stock_actual_nube < cant_merma:
                                    st.warning(f"⚠️ Stock insuficiente. Stock actual en nube: {stock_actual_nube}")
                                else:
                                    nuevo_stock_nube = max(0.0, stock_actual_nube - float(cant_merma))
                                    
                                    # 2. Actualizar el stock disminuido en Supabase
                                    supabase.table("productos").update({"stock": nuevo_stock_nube}).eq("rut_empresa", rut_actual).eq("codigo", str(codigo_p_merma)).execute()

                                    # 3. Registrar el historial de la merma en Supabase
                                    lote_limpio = "N/A"
                                    if lotes_disponibles_prod and lote_seleccionado_str:
                                        import re
                                        match_lote_ext = re.search(r'Lote:\s*(.*?)\s*\(Disponibles', lote_seleccionado_str)
                                        if match_lote_ext:
                                            lote_limpio = match_lote_ext.group(1).strip()

                                    nuevo_reg_merma_nube = {
                                        "fecha_hora": datetime.now().isoformat(),
                                        "codigo": str(codigo_p_merma),
                                        "descripcion": str(desc_p_merma),
                                        "cantidad": float(cant_merma),
                                        "motivo": str(motivo_merma),
                                        "lote": str(lote_limpio),
                                        "observacion": str(observacion_merma) if observacion_merma else "Sin observaciones",
                                        "id_negocio": str(rut_actual).strip()
                                    }
                                    
                                    supabase.table("mermas").insert(nuevo_reg_merma_nube).execute()

                                    st.success(f"✅ ¡Merma registrada y stock descontado en la nube con éxito! (Nuevo stock: {nuevo_stock_nube})")
                                    st.rerun()
                            else:
                                st.error("❌ No se encontró el producto en la base de datos de la nube.")
                        except Exception as e:
                            st.error(f"❌ Error al procesar la merma en Supabase: {e}")
# ---------------- SECCIÓN FINANZAS ----------------
elif menu == "📊 Módulo de Finanzas":
    mostrar_encabezado_con_home("📊 Panel de Control Financiero y Gastos")
   
    tab_fin1, tab_fin2, tab_fin3 = st.tabs([
        "💳 Cuentas por Pagar",
        "📅 Calendario de Pagos",
        "💸 Registro de Gastos"
    ])
   
    with tab_fin1:
        mostrar_modulo_cuentas_por_pagar(ruta_negocio)
       
    with tab_fin2:
        mostrar_modulo_calendario_pagos(ruta_negocio)
       
    with tab_fin3:
        mostrar_modulo_registro_gastos(supabase)

# ----------------- SECCIÓN INFORMES Y MOVIMIENTOS -----------------
elif menu == "📈 Informes y Movimientos (Kardex)":
    mostrar_encabezado_con_home("📈 Módulo Unificado de Informes y Movimientos")
    st.markdown("Consulta y filtra el historial completo de entradas (compras), salidas (ventas) y movimientos de inventario:")

    tab_inf1, tab_inf2 = st.tabs(["📑 Libro de Ventas (Salidas)", "📋 Historial de Compras (Entradas)"])

    with tab_inf1:
        st.markdown("### 💰 Registro de Salidas y Ventas")
        archivos_excel = [f for f in os.listdir(ruta_negocio) if f.startswith("Libro_Ventas_") and f.endswith(".xlsx")]
        if not archivos_excel:
            st.info("ℹ️ Aún no hay registros de ventas para este negocio.")
        else:
            archivo_sel = st.selectbox("📅 Selecciona el Libro Mensual de Ventas:", sorted(archivos_excel, reverse=True), key="sel_ventas_kardex")
            path_sel_v = os.path.join(ruta_negocio, archivo_sel)
            df_v = pd.read_excel(path_sel_v)
            if not df_v.empty:
                if 'Total' in df_v.columns and 'TotalBoleta' not in df_v.columns:
                    df_v['TotalBoleta'] = df_v['Total']
                elif 'TotalBoleta' in df_v.columns and 'Total' in df_v.columns:
                    df_v['TotalBoleta'] = df_v['TotalBoleta'].fillna(df_v['Total'])

                df_v["FechaHora"] = pd.to_datetime(df_v["FechaHora"])
                df_v["Fecha"] = df_v["FechaHora"].dt.date
                st.dataframe(df_v, use_container_width=True)
               
                if "TransaccionID" in df_v.columns and "TotalBoleta" in df_v.columns:
                    tot_v = df_v.drop_duplicates(subset=["TransaccionID"])["TotalBoleta"].sum()
                else:
                    tot_v = df_v["Subtotal"].sum() if "Subtotal" in df_v.columns else 0.0
               
                st.metric(label="💰 Total Ingresos Netos Reales", value=f"${tot_v:,.2f}")
            else:
                st.warning("⚠️ El libro seleccionado está vacío.")

    with tab_inf2:
        st.markdown("### 🛒 Registro de Entradas y Compras")
        if not os.path.exists(archivo_compras):
            st.info("ℹ️ Aún no hay registros de compras guardados para este negocio.")
        else:
            df_c = pd.read_excel(archivo_compras)
            if not df_c.empty:
                st.dataframe(df_c, use_container_width=True)
                tot_c = df_c["Subtotal"].sum() if "Subtotal" in df_c.columns else 0.0
                st.metric(label="💵 Total Invertido en Compras", value=f"${tot_c:,.2f}")
            else:
                st.warning("⚠️ El registro de compras está vacío.")

# ----------------- SECCIÓN CONTROL Y GESTIÓN DE INVENTARIO -----------------
elif menu == "⚠️ Control y Gestión de Inventario":
    mostrar_encabezado_con_home("⚠️ Panel de Control Operativo y Alertas de Inventario")
  
    with st.expander("⚙️ Configurar Parámetros de Operación e Inventario", expanded=False):
        st.markdown("Ajusta los valores operativos según la logística y tiempos de tu negocio:")
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        
        with col_p1:
            lead_time_dias = st.number_input("🚚 Lead Time Proveedor (Días)", min_value=1, max_value=90, value=3, step=1, help="Tiempo que demora el proveedor en entregar mercadería.")
        with col_p2:
            consumo_diario_estimado = st.number_input("📈 Consumo Promedio Diario (Unid)", min_value=0.1, max_value=10000.0, value=1.5, step=0.1, help="Venta o consumo diario estimado por producto si no hay histórico detallado.")
        with col_p3:
            limite_sobrestock_semanas = st.number_input("🛑 Límite de Sobrestock (Semanas)", min_value=1, max_value=52, value=4, step=1, help="Semanas máximas de stock permitidas antes de marcar exceso de capital.")
        with col_p4:
            dias_alerta_roja = st.number_input("🔴 Alerta Crítica Vencimiento (Días)", min_value=1, max_value=30, value=7, step=1, help="Días restantes para considerar un lote en zona roja.")

    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🚦 Semáforo de Vencimientos", "📦 Sugerencia de Reabastecimiento", "🛑 Control de Sobrestock"])

    with sub_tab1:
        st.markdown(f"### 🚦 Clasificación Automática de Vencimientos (Lotes Activos)")
      
        archivo_lotes = os.path.join(ruta_negocio, "base_lotes.xlsx") if 'ruta_negocio' in globals() else "base_lotes.xlsx"
       
        if os.path.exists(archivo_lotes):
            df_lotes_venc = pd.read_excel(archivo_lotes, dtype={'Código': str})
        else:
            df_lotes_venc = pd.DataFrame()

        if not df_lotes_venc.empty and 'FechaVencimiento' in df_lotes_venc.columns:
            roja, amarilla, verde = [], [], []
            hoy = datetime.now().date()
          
            for idx, row in df_lotes_venc.iterrows():
                fecha_val = row.get('FechaVencimiento')
                lote_val = str(row.get('Lote', 'N/A'))
               
                if pd.notna(fecha_val) and lote_val != "N/A" and str(fecha_val) != "N/A":
                    try:
                        f_venc = pd.to_datetime(fecha_val).date()
                        dias = (f_venc - hoy).days
                       
                        item = {
                            "Código": str(row.get("Código", "")),
                            "Descripción": str(row.get("Descripción", "")),
                            "Lote": lote_val,
                            "Cantidad Disponible": float(row.get("CantidadDisponible", 0)),
                            "Fecha Vencimiento": str(f_venc),
                            "Días Restantes": dias
                        }
                       
                        if dias <= dias_alerta_roja:
                            roja.append(item)
                        elif dias_alerta_roja < dias <= (dias_alerta_roja + 8):
                            amarilla.append(item)
                        elif (dias_alerta_roja + 9) <= dias <= (dias_alerta_roja + 23):
                            verde.append(item)
                    except Exception:
                        pass

            c1, c2, c3 = st.columns(3)
            with c1:
                st.error(f"🔴 Zona Roja <= {dias_alerta_roja} días ({len(roja)})")
                if roja:
                    st.dataframe(pd.DataFrame(roja), use_container_width=True)
                else:
                    st.caption("Sin productos en riesgo crítico.")
            with c2:
                st.warning(f"🟡 Zona Amarilla ({len(amarilla)})")
                if amarilla:
                    st.dataframe(pd.DataFrame(amarilla), use_container_width=True)
                else:
                    st.caption("Sin productos en alerta media.")
            with c3:
                st.success(f"🟢 Zona Verde ({len(verde)})")
                if verde:
                    st.dataframe(pd.DataFrame(verde), use_container_width=True)
                else:
                    st.caption("Sin productos próximos a vencer.")
        else:
            st.info("ℹ️ Aún no hay registros de lotes con fecha de vencimiento guardados para este negocio.")

    with sub_tab2:
        st.markdown(f"### 📦 Asistente de Reabastecimiento Automático (Lead Time configurado: {lead_time_dias} días)")
        if df_base is not None:
            col_stock = next((c for c in df_base.columns if 'stock' in str(c).lower() or 'cantidad' in str(c).lower() or 'existencia' in str(c).lower()), None)
            col_desc = next((c for c in df_base.columns if 'descripción' in str(c).lower() or 'nombre' in str(c).lower()), 'Descripción')
            col_cod = next((c for c in df_base.columns if 'código' in str(c).lower() or 'codigo' in str(c).lower()), df_base.columns[0])

            if col_stock:
                sugerencias = []
                consumo_periodo_lt = consumo_diario_estimado * lead_time_dias
                demanda_semanal = consumo_diario_estimado * 7.0

                for idx, row in df_base.iterrows():
                    stock = float(row.get(col_stock, 0)) if pd.notna(row.get(col_stock)) else 0.0
                    if stock <= consumo_periodo_lt:
                        sugerencias.append({
                            'Código': str(row.get(col_cod, '')),
                            'Descripción': str(row.get(col_desc, '')),
                            'Stock Actual': stock,
                            'Sugerido a Comprar': round(demanda_semanal - stock + consumo_periodo_lt, 2)
                        })
                if sugerencias:
                    st.warning(f"⚠️ {len(sugerencias)} productos en riesgo de quiebre según el lead time actual.")
                    st.dataframe(pd.DataFrame(sugerencias), use_container_width=True)
                else:
                    st.success(f"✔️ Todo el inventario soporta holgadamente los {lead_time_dias} días de entrega.")
            else:
                st.warning("⚠️ Falta la columna de stock.")
        else:
            st.error("⚠️ Falta la base de datos.")

    with sub_tab3:
        st.markdown("### 🖨️ Datos del Comprobante e Impresión")

        st.markdown("---")
        st.markdown("### 🖼️ Logotipo de la Empresa")
        
        if negocio_seleccionado and negocio_seleccionado != "admin_general":
            tenant_dir_logo = os.path.join(CARPETA_CLIENTES, str(negocio_seleccionado))
            ruta_logo_final = os.path.join(tenant_dir_logo, "logo_empresa.png")
            
            if os.path.exists(ruta_logo_final):
                st.image(ruta_logo_final, width=120, caption="Logotipo actual guardado")
       
            logo_cargado = st.file_uploader("Sube una imagen para tu logo (PNG o JPG)", type=["png", "jpg", "jpeg"], key="uploader_logo_empresa")
            
            if logo_cargado is not None:
                try:
                    os.makedirs(tenant_dir_logo, exist_ok=True)
                    
                    img = Image.open(logo_cargado)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    img.save(ruta_logo_final, "PNG")
                    st.success("✅ ¡Logotipo procesado y actualizado con éxito!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ocurrió un error al guardar el logotipo: {e}")
        else:
            st.warning("⚠️ Selecciona un negocio específico desde el panel para poder cambiar su logotipo.")

# ----------------- SECCIÓN COMPRAS Y RECEPCIONES (GRC / GRI) -----------------
elif menu == "🛒 Registrar Compra (CPP)":
    mostrar_encabezado_con_home("🛒 Gestión de Compras y Recepciones (GRC / GRI)")

    # --- CARGA DE PRODUCTOS DIRECTO DESDE LA NUBE (SUPABASE) PARA GRC/GRI ---
    df_base = pd.DataFrame()
    try:
        res_prod_nube = supabase.table("productos").select("codigo, descripcion, stock, precio_venta").eq("rut_empresa", rut_actual).limit(10000).execute()
        if res_prod_nube.data:
            df_base = pd.DataFrame(res_prod_nube.data)
    except Exception as e:
        st.error(f"⚠️ Error conectando al inventario de la nube para compras: {e}")

    if not df_base.empty:
        # Definimos las columnas estándar que usarán los selectbox y campos de la GRC
        col_cod = 'codigo'
        col_desc = 'descripcion'
        col_stock = 'stock'
        col_precio = 'precio_venta'
        accion_producto = st.radio("Selecciona una opción:", ["📥 Registrar Compra / GRC (Factura con Lotes)", "🔄 Recepción Interna / GRI (Ajustes / Producción)", "➕ Crear Producto Nuevo", "✏️ Editar Producto Existente"], horizontal=True)
        st.divider()

        # --- 1. REGISTRO GRC (Guía de Recepción de Compra - Proveedor Externo) ---
        if accion_producto == "📥 Registrar Compra / GRC (Factura con Lotes)":
            st.markdown("### 📋 Cabecera de la Recepción de Compra (GRC)")

            # --- CARGA DE PROVEEDORES DIRECTO DESDE LA NUBE (SUPABASE) ---
            lista_proveedores = []
            try:
                res_prov_nube = supabase.table("proveedores").select("nombre").eq("id_negocio", rut_actual).execute()
                if res_prov_nube.data:
                    lista_proveedores = [p["nombre"] for p in res_prov_nube.data if p.get("nombre")]
            except Exception as e:
                print(f"Error cargando proveedores desde Supabase en GRC: {e}")

            if not lista_proveedores:
                lista_proveedores = ["Proveedor General"]

            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                proveedor_factura = st.selectbox("Nombre del Proveedor", options=lista_proveedores)
                num_factura = st.text_input("Número de Factura / Folio GRC")
            with col_f2:
                fecha_compra = st.date_input("Fecha de Recepción GRC", value=date.today())
                condicion_pago = st.selectbox("Condición de Pago", ["Contado", "Crédito", "Cheque"])
            with col_f3:
                col_imp_esp = next((c for c in df_base.columns if 'impuesto' in str(c).lower() or 'específico' in str(c).lower() or ' ila ' in str(c).lower() or 'iaba' in str(c).lower()), None)
                st.write("")
                st.write(f"🔍 Columna de Impuestos: **{'Detectada' if col_imp_esp else 'No detectada'}**")

            fecha_vencimiento_pago = fecha_compra
            num_serie_cheque = ""
            banco_cheque = ""
            estado_inicial = "Pagado" if condicion_pago == "Contado" else "Pendiente"

            if condicion_pago == "Crédito":
                fecha_vencimiento_pago = st.date_input("Fecha de Vencimiento del Crédito", value=date.today())
            elif condicion_pago == "Cheque":
                col_ch1, col_ch2 = st.columns(2)
                with col_ch1:
                    fecha_vencimiento_pago = st.date_input("Fecha de Cobro del Cheque", value=date.today())
                    num_serie_cheque = st.text_input("Número de Serie del Cheque")
                with col_ch2:
                    banco_cheque = st.text_input("Banco Emisor")

            st.divider()
            st.markdown("#### 🔍 Agregar Productos de la GRC")

            if 'carrito_factura_compras' not in st.session_state:
                st.session_state.carrito_factura_compras = []

            metodo_entrada_prod = st.radio("Método para buscar producto:", ["⌨️ Escáner / Pistola Láser (Código)", "🔎 Buscar por Nombre / Palabra Clave"], horizontal=True, key="metodo_busq_grc")
        
            prod_seleccionado_item = None
            opciones_productos = ["-- Selecciona un producto --"] + [f"{row[col_cod]} - {row[col_desc]}" for idx, row in df_base.iterrows()]

            if metodo_entrada_prod == "⌨️ Escáner / Pistola Láser (Código)":
                codigo_buscado = st.text_input("Pistola láser / Digitar Código EAN:", key="input_pistola_compra_grc")
                if codigo_buscado:
                    match_p = df_base[df_base[col_cod].astype(str) == str(codigo_buscado)]
                    if not match_p.empty:
                        prod_seleccionado_item = f"{match_p.iloc[0][col_cod]} - {match_p.iloc[0][col_desc]}"
                        st.success(f"✔️ Producto encontrado: {prod_seleccionado_item}")
                    else:
                        st.warning("⚠️ No se encontró ningún producto con ese código.")
            else:
                prod_seleccionado_item = st.selectbox("Selecciona o busca por palabra clave:", options=opciones_productos, key="select_palabra_clave_compra_grc")

            col_item1, col_item2, col_item3 = st.columns(3)
            with col_item1:
                cant_item = st.number_input("Cantidad", min_value=1.0, step=1.0, value=1.0, key="cant_grc")
            with col_item2:
                neto_unit_item = st.number_input("Valor Neto Unitario ($)", min_value=0.0, step=1.0, value=0.0, key="neto_grc")
            with col_item3:
                maneja_lote = st.selectbox("¿Maneja Lote y Vencimiento?", ["No", "Sí"], key="lote_grc")

            lote_item = "SIN-LOTE"
            venc_item = str(date.today())

            if maneja_lote == "Sí":
                st.markdown("📌 **Ingrese los datos reales del lote:**")
                col_l1, col_l2 = st.columns(2)
                with col_l1:
                    lote_item = st.text_input("N° Lote", value="LOTE-001", key="num_lote_grc")
                with col_l2:
                    venc_item_date = st.date_input("Fecha de Vencimiento Lote", value=date.today(), key="venc_lote_grc")
                    venc_item = str(venc_item_date)

            if st.button("➕ Agregar Línea a la GRC", type="primary", key="btn_add_grc"):
                if not prod_seleccionado_item or prod_seleccionado_item == "-- Selecciona un producto --":
                    st.warning("⚠️ Debes seleccionar o escanear un producto válido.")
                elif neto_unit_item <= 0:
                    st.warning("⚠️ El valor neto unitario debe ser mayor a 0.")
                elif maneja_lote == "Sí" and not lote_item:
                    st.warning("⚠️ Debes ingresar el número de lote.")
                else:
                    codigo_p = prod_seleccionado_item.split(" - ")[0]
                    match_m = df_base[df_base[col_cod].astype(str) == str(codigo_p)]
                    porcentaje_ila = 0.0
                
                    if col_imp_esp and not match_m.empty:
                        val_imp = str(match_m.iloc[0][col_imp_esp]).strip()
                        import re
                        numeros = re.findall(r'\d+[\,,\.]?\d*', val_imp.replace(',', '.'))
                        if numeros:
                            porcentaje_ila = float(numeros[0])

                    subtotal_neto = cant_item * neto_unit_item
                    monto_iva = subtotal_neto * 0.19
                    monto_ila = subtotal_neto * (porcentaje_ila / 100.0)
                    costo_total_linea = subtotal_neto + monto_iva + monto_ila
                    costo_unitario_final = costo_total_linea / cant_item

                    st.session_state.carrito_factura_compras.append({
                        "TipoDoc": "GRC",
                        "Código": codigo_p,
                        "Descripción": prod_seleccionado_item.split(" - ")[1],
                        "Cantidad": cant_item,
                        "NetoUnitario": neto_unit_item,
                        "SubtotalNeto": subtotal_neto,
                        "IVA": monto_iva,
                        "ImpuestoEspecifico": monto_ila,
                        "CostoTotal": costo_total_linea,
                        "CostoUnitarioFinal": costo_unitario_final,
                        "ManejaLote": maneja_lote,
                        "Lote": lote_item if maneja_lote == "Sí" else "N/A",
                        "FechaVencimiento": venc_item if maneja_lote == "Sí" else "N/A"
                    })
                    st.success(f"✅ ¡Línea agregada a la GRC!")
                    st.rerun()

            if st.session_state.carrito_factura_compras:
                st.markdown("#### 📦 Productos Agregados en esta GRC")
            
                for idx_c, item in enumerate(st.session_state.carrito_factura_compras):
                    if item.get("TipoDoc", "GRC") == "GRC":
                        c_col1, c_col2 = st.columns([8, 1])
                        with c_col1:
                            st.info(f"**{item['Cantidad']}x** {item['Descripción']} | Neto: ${item['NetoUnitario']:,.0f} | **Costo Unit. c/Imp: ${item['CostoUnitarioFinal']:,.0f}** | Total: ${item['CostoTotal']:,.0f} | Lote: {item['Lote']} ({item['FechaVencimiento']})")
                        with c_col2:
                            if st.button("❌", key=f"del_linea_grc_{idx_c}", help="Eliminar esta línea"):
                                st.session_state.carrito_factura_compras.pop(idx_c)
                                st.rerun()

                monto_total_factura_general = sum(item["CostoTotal"] for item in st.session_state.carrito_factura_compras if item.get("TipoDoc", "GRC") == "GRC")
                st.markdown(f"### 💰 **Monto Total GRC (con Impuestos): ${monto_total_factura_general:,.2f}**")

                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("🗑️ Limpiar / Vaciar GRC", type="secondary", key="btn_limpiar_grc"):
                        st.session_state.carrito_factura_compras = [i for i in st.session_state.carrito_factura_compras if i.get("TipoDoc") != "GRC"]
                        st.rerun()
                with col_b2:
                    if st.button("💾 Procesar GRC Completa y Actualizar Stock/Finanzas", type="primary", key="btn_procesar_grc"):
                        if not num_factura:
                            st.warning("⚠️ Ingresa el Número de Factura o Folio GRC antes de procesar.")
                        else:
                            prov_final = proveedor_factura if proveedor_factura else "Proveedor General"
                            try:
                                archivo_prov_reg = os.path.join(ruta_negocio, "Maestro_Proveedores.xlsx") if 'ruta_negocio' in globals() else "Maestro_Proveedores.xlsx"
                                if os.path.exists(archivo_prov_reg):
                                    df_pr_g = pd.read_excel(archivo_prov_reg)
                                    if prov_final not in df_pr_g['Nombre_Proveedor'].values:
                                        nuevo_p_df = pd.DataFrame([{'Nombre_Proveedor': prov_final, 'Rut': '', 'Contacto': '', 'Telefono': '', 'Email': ''}])
                                        pd.concat([df_pr_g, nuevo_p_df], ignore_index=True).to_excel(archivo_prov_reg, index=False)
                                else:
                                    pd.DataFrame([{'Nombre_Proveedor': prov_final, 'Rut': '', 'Contacto': '', 'Telefono': '', 'Email': ''}]).to_excel(archivo_prov_reg, index=False)
                            except Exception:
                                pass

                            procesados = 0
                        lineas_detalle_grc = ""
                        for item in st.session_state.carrito_factura_compras:
                            if item.get("TipoDoc", "GRC") == "GRC":
                                lineas_detalle_grc += f"- {item['Descripción']} (x{item['Cantidad']}) | Costo Unit: ${item['CostoUnitarioFinal']:,.2f} | Subtotal: ${item['CostoTotal']:,.2f} | Lote: {item['Lote']}\n"
                                
                                # 1. Registro directo en la tabla 'compras' de Supabase con aislamiento por negocio
                                nuevo_reg_compra_nube = {
                                    "fecha_hora": datetime.now().isoformat(),
                                    "tipo_recepcion": "GRC",
                                    "proveedor": str(prov_final),
                                    "factura": str(num_factura),
                                    "codigo": str(item["Código"]),
                                    "descripcion": str(item["Descripción"]),
                                    "cantidad": float(item["Cantidad"]),
                                    "neto_unitario": float(item["NetoUnitario"]),
                                    "costo_total": float(item["CostoTotal"]),
                                    "lote": str(item["Lote"]),
                                    "fecha_vencimiento_lote": str(item["FechaVencimiento"]),
                                    "condicion_pago": str(condicion_pago),
                                    "id_negocio": str(rut_actual).strip() # Candado vital por empresa
                                }
                                
                                try:
                                    supabase.table("compras").insert(nuevo_reg_compra_nube).execute()
                                except Exception as e:
                                    print(f"⚠️ Error guardando compra en Supabase: {e}")

                                # 2. Actualizar Stock del producto en Supabase en tiempo real
                                try:
                                    res_stk = supabase.table("productos").select("stock").eq("rut_empresa", rut_actual).eq("codigo", str(item["Código"])).execute()
                                    if res_stk.data:
                                        stk_actual = float(res_stk.data[0]["stock"] or 0.0)
                                        nuevo_stk = stk_actual + float(item["Cantidad"])
                                        supabase.table("productos").update({"stock": nuevo_stk}).eq("rut_empresa", rut_actual).eq("codigo", str(item["Código"])).execute()
                                except Exception as e:
                                    print(f"⚠️ Error actualizando stock en Supabase: {e}")

                                procesados += 1

                            archivo_gastos = os.path.join(ruta_negocio, "Registro_Gastos.xlsx") if 'ruta_negocio' in globals() else "Registro_Gastos.xlsx"
                            nuevo_gasto = pd.DataFrame([{
                                'Fecha_Hora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'Descripcion_Gasto': f"GRC Factura/Folio #{num_factura} - {prov_final}",
                                'Categoria': 'Mercadería',
                                'Metodo_Pago': condicion_pago,
                                'Documento': f"GRC {num_factura}",
                                'Monto': monto_total_factura_general
                            }])
                            if os.path.exists(archivo_gastos):
                                df_gastos_ant = pd.read_excel(archivo_gastos)
                                pd.concat([df_gastos_ant, nuevo_gasto], ignore_index=True).to_excel(archivo_gastos, index=False)
                            else:
                                nuevo_gasto.to_excel(archivo_gastos, index=False)

                            if condicion_pago in ["Crédito", "Cheque"]:
                                archivo_cuentas = os.path.join(ruta_negocio, "Cuentas_Por_Pagar.xlsx") if 'ruta_negocio' in globals() else "Cuentas_Por_Pagar.xlsx"
                                nueva_cuenta = pd.DataFrame([{
                                    'Proveedor': prov_final,
                                    'Numero_Factura': num_factura,
                                    'Fecha_Emision': str(fecha_compra),
                                    'Fecha_Vencimiento': str(fecha_vencimiento_pago),
                                    'Monto_Total': monto_total_factura_general,
                                    'Estado': 'PENDIENTE'
                                }])
                                if os.path.exists(archivo_cuentas):
                                    df_cuentas_ant = pd.read_excel(archivo_cuentas)
                                    pd.concat([df_cuentas_ant, nueva_cuenta], ignore_index=True).to_excel(archivo_cuentas, index=False)
                                else:
                                    nueva_cuenta.to_excel(archivo_cuentas, index=False)
                            # 🗂️ ARCHIVADOR AUTOMÁTICO GRC (Subdirectorio)
                            try:
                                dir_arch_grc = os.path.join(ruta_negocio, "archivador_compras", "grc")
                                os.makedirs(dir_arch_grc, exist_ok=True)
                                doc_grc_txt = f"""========================================
 GUÍA DE RECEPCIÓN DE COMPRA (GRC)
========================================
FOLIO / FACTURA: {num_factura}
PROVEEDOR: {prov_final}
FECHA: {fecha_compra}
CONDICIÓN PAGO: {condicion_pago}
----------------------------------------
DETALLE:
{lineas_detalle_grc}----------------------------------------
TOTAL GRC: ${monto_total_factura_general:,.2f}
========================================"""
                                ruta_doc_grc = os.path.join(dir_arch_grc, f"GRC_{num_factura}.txt")
                                with open(ruta_doc_grc, "w", encoding="utf-8") as f_grc:
                                    f_grc.write(doc_grc_txt)
                            except Exception as e:
                                print(f"Error archivando GRC: {e}")

                            st.session_state.carrito_factura_compras = [i for i in st.session_state.carrito_factura_compras if i.get("TipoDoc") != "GRC"]
                            st.success(f"✅ ¡GRC #{num_factura} procesada con éxito! Stock actualizado, documento archivado y finanzas sincronizadas.")
                            st.rerun()

        # --- 2. REGISTRO GRI (Guía de Recepción Interna - Ajustes / Producción / Hallazgos) ---
        elif accion_producto == "🔄 Recepción Interna / GRI (Ajustes / Producción)":
            st.markdown("### 🔄 Generar Guía de Recepción Interna (GRI)")
            st.info("ℹ️ Use este módulo para ingresos de inventario generados internamente (devoluciones, producción propia, hallazgos o ajustes positivos de bodega).")

            with st.form("form_gri_interno"):
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    folio_gri = st.text_input("N° Folio GRI interno (ej. GRI-2026-001)")
                    motivo_gri = st.selectbox("Motivo del Ingreso Interno", ["Producción Propia", "Hallazgo de Inventario / Conteo", "Devolución de Cliente", "Ajuste Positivo de Bodega", "Otro"])
                with col_g2:
                    fecha_gri = st.date_input("Fecha de Recepción Interna", value=date.today())
                    responsable_gri = st.text_input("Responsable / Autorizado por")

                st.markdown("#### 📦 Seleccionar Producto y Cantidad")
                opciones_prod_gri = ["-- Selecciona un producto --"] + [f"{row[col_cod]} - {row[col_desc]}" for idx, row in df_base.iterrows()]
                prod_gri_sel = st.selectbox("Producto a Ingresar Internamente", options=opciones_prod_gri)
                
                col_q1, col_q2 = st.columns(2)
                with col_q1:
                    cant_gri = st.number_input("Cantidad a Ingresar", min_value=1.0, step=1.0, value=1.0)
                with col_q2:
                    costo_estimado_gri = st.number_input("Costo Unitario de Referencia ($)", min_value=0.0, step=1.0, value=0.0)

                maneja_lote_gri = st.selectbox("¿Asignar Lote a este ingreso interno?", ["No", "Sí"])
                lote_gri = "GRI-LOTE"
                venc_gri = str(date.today())

                if maneja_lote_gri == "Sí":
                    col_lg1, col_lg2 = st.columns(2)
                    with col_lg1:
                        lote_gri = st.text_input("N° Lote Interno", value="LOTE-INT-01")
                    with col_lg2:
                        venc_gri_date = st.date_input("Fecha de Vencimiento Lote Interno", value=date.today())
                        venc_gri = str(venc_gri_date)

                btn_procesar_gri = st.form_submit_button("💾 Emitir GRI y Actualizar Inventario", type="primary")

                if btn_procesar_gri:
                    if not folio_gri:
                        st.warning("⚠️ Debes ingresar un número de folio para la GRI.")
                    elif prod_gri_sel == "-- Selecciona un producto --":
                        st.warning("⚠️ Selecciona un producto válido.")
                    elif cant_gri <= 0:
                        st.warning("⚠️ La cantidad debe ser mayor a 0.")
                    else:
                        codigo_gri = prod_gri_sel.split(" - ")[0]
                        desc_gri = prod_gri_sel.split(" - ")[1]
                        
                        # 1. Actualizar Stock en base principal
                        match_gri = df_base[df_base[col_cod].astype(str) == str(codigo_gri)]
                        if not match_gri.empty:
                            idx_g = match_gri.index[0]
                            stock_actual_g = float(df_base.at[idx_g, col_stock]) if col_stock and not pd.isna(df_base.at[idx_g, col_stock]) else 0.0
                            df_base.at[idx_g, col_stock] = stock_actual_g + cant_gri
                            df_base.to_excel(archivo_base, index=False)

                        # 2. Registrar en base de lotes si aplica
                        if maneja_lote_gri == "Sí":
                            archivo_lotes = os.path.join(ruta_negocio, "base_lotes.xlsx") if 'ruta_negocio' in globals() else "base_lotes.xlsx"
                            nuevo_reg_lote_gri = pd.DataFrame([{
                                "Código": codigo_gri,
                                "Descripción": desc_gri,
                                "Lote": lote_gri,
                                "CantidadDisponible": cant_gri,
                                "FechaVencimiento": venc_gri,
                                "CostoUnitarioFinal": costo_estimado_gri
                            }])
                            if os.path.exists(archivo_lotes):
                                df_lotes_g = pd.read_excel(archivo_lotes, dtype={'Código': str})
                                pd.concat([df_lotes_g, nuevo_reg_lote_gri], ignore_index=True).to_excel(archivo_lotes, index=False)
                            else:
                                nuevo_reg_lote_gri.to_excel(archivo_lotes, index=False)

                        # 3. Registrar en Registro de Compras/Recepciones como GRI
                        nuevo_reg_gri_hist = pd.DataFrame([{
                            "FechaHora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "TipoRecepcion": "GRI",
                            "Proveedor": f"INTERNO ({motivo_gri})",
                            "Factura": folio_gri,
                            "Código": codigo_gri,
                            "Descripción": desc_gri,
                            "Cantidad": cant_gri,
                            "NetoUnitario": costo_estimado_gri,
                            "SubtotalNeto": cant_gri * costo_estimado_gri,
                            "IVA": 0.0,
                            "ImpuestoEspecifico": 0.0,
                            "CostoTotal": cant_gri * costo_estimado_gri,
                            "ManejaLote": maneja_lote_gri,
                            "Lote": lote_gri,
                            "FechaVencimientoLote": venc_gri,
                            "Condicion_Pago": "Interno",
                            "FechaVencimientoPago": str(fecha_gri),
                            "Banco": "",
                            "N_Serie": responsable_gri,
                            "Estado": "Completado"
                        }])
                        archivo_compras_path = os.path.join(ruta_negocio, "Registro_Compras.xlsx") if 'ruta_negocio' in globals() else "Registro_Compras.xlsx"
                        if os.path.exists(archivo_compras_path):
                            df_ec_g = pd.read_excel(archivo_compras_path, dtype={'Código': str, 'Factura': str})
                            pd.concat([df_ec_g, nuevo_reg_gri_hist], ignore_index=True).to_excel(archivo_compras_path, index=False)
                        else:
                            nuevo_reg_gri_hist.to_excel(archivo_compras_path, index=False)

                        # 🗂️ 4. ARCHIVADOR AUTOMÁTICO GRI (Subdirectorio)
                        try:
                            dir_arch_gri = os.path.join(ruta_negocio, "archivador_compras", "gri")
                            os.makedirs(dir_arch_gri, exist_ok=True)
                            doc_gri_txt = f"""========================================
 GUÍA DE RECEPCIÓN INTERNA (GRI)
========================================
FOLIO: {folio_gri}
MOTIVO: {motivo_gri}
RESPONSABLE: {responsable_gri}
FECHA: {fecha_gri}
----------------------------------------
PRODUCTO INGRESADO:
- {desc_gri} (Código: {codigo_gri})
- Cantidad: {cant_gri}
- Costo Ref: ${costo_estimado_gri:,.2f}
- Lote: {lote_gri} (Venc: {venc_gri})
========================================"""
                            ruta_doc_gri = os.path.join(dir_arch_gri, f"GRI_{folio_gri}.txt")
                            with open(ruta_doc_gri, "w", encoding="utf-8") as f_gri:
                                f_gri.write(doc_gri_txt)
                        except Exception as e:
                            print(f"Error archivando GRI: {e}")

                        st.success(f"✅ ¡GRI #{folio_gri} procesada con éxito! Stock actualizado y documento archivado automáticamente.")
                        st.rerun()

        # --- 3. CREAR PRODUCTO NUEVO ---
        elif accion_producto == "➕ Crear Producto Nuevo":
            st.markdown("### 🆕 Ingresar Nuevo Producto a la Base de Datos")
            codigo_scanned_nuevo = st.text_input("📷 Digita o ingresa el código del producto nuevo:", key="scan_nuevo_prod")
        
            with st.form("form_crear_producto"):
                n_codigo = st.text_input("Código del Producto (EAN o Interno)", value=codigo_scanned_nuevo if codigo_scanned_nuevo else "")
                n_desc = st.text_input("Descripción / Nombre del Producto")
                n_stock = st.number_input("Stock Inicial", min_value=0.0, step=1.0, value=0.0)
                n_costo = st.number_input("Costo de Compra Neto ($)", min_value=0.0, step=1.0, value=0.0)
                n_precio = st.number_input("Precio de Venta ($)", min_value=0.0, step=1.0, value=0.0)
            
                btn_crear_prod = st.form_submit_button("💾 Agregar Producto a la Base de Datos")

                if btn_crear_prod:
                    if n_codigo and n_desc:
                        nuevo_prod_df = pd.DataFrame([{
                            col_cod: str(n_codigo),
                            col_desc: str(n_desc),
                            col_stock if col_stock else 'Stock': float(n_stock),
                            col_precio if col_precio else 'Precio': float(n_precio)
                        }])
                        df_actualizado = pd.concat([df_base, nuevo_prod_df], ignore_index=True)
                        df_actualizado.to_excel(archivo_base, index=False)
                        st.success(f"✅ ¡Producto '{n_desc}' creado con éxito!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Debes ingresar al menos el código y la descripción.")

        # --- 4. EDITAR PRODUCTO EXISTENTE ---
        elif accion_producto == "✏️ Editar Producto Existente":
            st.markdown("### ✏️ Modificar datos de un Producto Existente")
            opciones_editar = ["-- Selecciona producto a editar --"] + [f"{row[col_cod]} - {row[col_desc]}" for idx, row in df_base.iterrows()]
        
            with st.form("form_editar_producto"):
                prod_a_editar = st.selectbox("Selecciona Producto", options=opciones_editar)
                nuevo_nombre = st.text_input("Nueva Descripción / Nombre")
                nuevo_stock = st.number_input("Modificar Stock Actual", min_value=0.0, step=1.0, value=0.0)
                nuevo_precio = st.number_input("Modificar Precio de Venta ($)", min_value=0.0, step=1.0, value=0.0)
                btn_editar_prod = st.form_submit_button("💾 Guardar Cambios")

                if btn_editar_prod:
                    if prod_a_editar != "-- Selecciona producto a editar --":
                        cod_editar = prod_a_editar.split(" - ")[0]
                        match_edit = df_base[df_base[col_cod].astype(str) == str(cod_editar)]
                        if not match_edit.empty:
                            idx_e = match_edit.index[0]
                            if nuevo_nombre:
                                df_base.at[idx_e, col_desc] = nuevo_nombre
                            if col_stock:
                                df_base.at[idx_e, col_stock] = nuevo_stock
                            if col_precio:
                                df_base.at[idx_e, col_precio] = nuevo_precio
                            df_base.to_excel(archivo_base, index=False)
                            st.success("✅ ¡Producto actualizado correctamente!")
                            st.rerun()
                    else:
                        st.warning("⚠️ Selecciona un producto válido para editar.")

# ----------------- SECCIÓN CONFIGURACIÓN GENERAL -----------------
elif menu == "⚙️ Configuración General":
    mostrar_encabezado_con_home("⚙️ Panel de Configuración General del Sistema")
  
    # 📁 Definición de rutas y directorios específicos del negocio actual
    tenant_dir = os.path.join(CARPETA_CLIENTES, negocio_seleccionado)
    os.makedirs(tenant_dir, exist_ok=True)
    ruta_bd_actual = os.path.join(tenant_dir, "BASE DE DATOS.xlsx")
    ruta_plantilla_base = os.path.join("plantilla_cliente", "BASE DE DATOS.xlsx")
    ruta_logo = os.path.join(tenant_dir, "logo_empresa.png")
    ruta_config_json = os.path.join(tenant_dir, "config_ticket.json")
    ruta_usuarios_local = os.path.join(tenant_dir, "usuarios_negocio.json")

    def cargar_usuarios_local(path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def guardar_usuarios_local(path, datos):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)

    if "ultimo_negocio_config" not in st.session_state or st.session_state.ultimo_negocio_config != negocio_seleccionado:
        st.session_state.ultimo_negocio_config = negocio_seleccionado
        if os.path.exists(ruta_config_json):
            try:
                with open(ruta_config_json, "r", encoding="utf-8") as f:
                    st.session_state.config_ticket = json.load(f)
            except Exception:
                st.session_state.config_ticket = {"nombre_empresa": negocio_seleccionado, "rut_empresa": "", "direccion": "", "iva_tasa": 19.0, "pie_pagina": "", "formato_impresion": "80mm (Térmica Estándar)"}
        else:
            st.session_state.config_ticket = {"nombre_empresa": negocio_seleccionado, "rut_empresa": "", "direccion": "", "iva_tasa": 19.0, "pie_pagina": "", "formato_impresion": "80mm (Térmica Estándar)"}

    tab1, tab2, tab3 = st.tabs(["👥 Usuarios y Cajas", "💳 Formas de Pago", "🖨️ Formato de Tickets e Impresión"])

    with tab1:
        st.markdown("### 👥 Creación y Gestión de Operadores del Negocio")
        st.info("ℹ️ Registra nuevos operadores (cajeros, bodegueros, etc.) para que ingresen al sistema con su propia contraseña y rol asignado.")

        db_usuarios = cargar_usuarios_local(ruta_usuarios_local)

        with st.form("form_crear_operador"):
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                nuevo_user_id = st.text_input("ID de Usuario / RUT (ej: cajero1)")
                nuevo_nombre_usr = st.text_input("Nombre Completo o Descripción (ej: Juan Pérez - Caja 1)")
            with col_u2:
                nuevo_pass_usr = st.text_input("Contraseña de Acceso", type="password")
                nuevo_rol_usr = st.selectbox("Rol / Permisos", options=["Cajero / Vendedor", "Bodeguero", "Administrador"])

            btn_guardar_usr = st.form_submit_button("💾 Registrar Nuevo Operador", type="primary")

            if btn_guardar_usr:
                user_limpio = nuevo_user_id.strip()
                if not user_limpio or not nuevo_pass_usr:
                    st.warning("⚠️ Debes ingresar el ID de usuario y la contraseña.")
                else:
                    db_usuarios[user_limpio] = {
                        "nombre": nuevo_nombre_usr or user_limpio,
                        "password": nuevo_pass_usr.strip(),
                        "rol": nuevo_rol_usr
                    }
                    guardar_usuarios_local(ruta_usuarios_local, db_usuarios)
                    st.success(f"✨ ¡Usuario '{user_limpio}' creado con éxito bajo el rol de {nuevo_rol_usr}!")
                    st.rerun()

        st.divider()
        st.markdown("### 📋 Operadores Registrados")
        if db_usuarios:
            lista_tabla = []
            for uid, info in db_usuarios.items():
                lista_tabla.append({
                    "Usuario / RUT": uid,
                    "Nombre": info.get("nombre"),
                    "Rol Asignado": info.get("rol")
                })
            st.dataframe(pd.DataFrame(lista_tabla), use_container_width=True)
        else:
            st.info("ℹ️ No hay operadores secundarios registrados todavía. El acceso principal opera con las credenciales globales de la empresa.")

    with tab2:
        st.markdown("### 💳 Configuración de Formas de Pago Aceptadas")
        with st.form("form_nueva_forma_pago"):
            nueva_forma = st.text_input("Nueva Forma de Pago")
            btn_add_pago = st.form_submit_button("➕ Agregar Forma de Pago")
            if btn_add_pago and nueva_forma and nueva_forma not in st.session_state.formas_pago_erp:
                st.session_state.formas_pago_erp.append(nueva_forma)
                st.success(f"✅ Forma de pago '{nueva_forma}' agregada.")
        for fp in st.session_state.formas_pago_erp:
            st.markdown(f"- 💳 {fp}")

    with tab3:
        st.markdown("### 🖨️ Datos del Comprobante e Impresión")
        with st.form("form_config_ticket"):
            empresa = st.text_input("Nombre Empresa", value=st.session_state.config_ticket.get("nombre_empresa", ""))
            rut = st.text_input("RUT", value=st.session_state.config_ticket.get("rut_empresa", ""))
            direccion = st.text_input("Dirección", value=st.session_state.config_ticket.get("direccion", ""))
           
            iva_personalizado = st.number_input("Tasa de IVA Local (%)", min_value=0.0, max_value=100.0, value=float(st.session_state.config_ticket.get("iva_tasa", 19.0)), step=1.0)
           
            pie = st.text_input("Pie de Página", value=st.session_state.config_ticket.get("pie_pagina", ""))
          
            formatos_disponibles = ["80mm (Térmica Estándar)", "58mm (Térmica Pequeña)", "Carta / A4"]
            formato_actual = st.session_state.config_ticket.get("formato_impresion", "80mm (Térmica Estándar)")
            idx_formato = formatos_disponibles.index(formato_actual) if formato_actual in formatos_disponibles else 0
          
            formato = st.selectbox("Formato", formatos_disponibles, index=idx_formato)
            btn_guardar_config = st.form_submit_button("💾 Guardar Configuración")
          
            if btn_guardar_config:
                st.session_state.config_ticket = {
                    "nombre_empresa": empresa,
                    "rut_empresa": rut,
                    "direccion": direccion,
                    "iva_tasa": iva_personalizado,
                    "pie_pagina": pie,
                    "formato_impresion": formato
                }
                try:
                    with open(ruta_config_json, "w", encoding="utf-8") as f:
                        json.dump(st.session_state.config_ticket, f, ensure_ascii=False, indent=4)
                    st.success("✅ Configuración e IVA guardados permanentemente.")
                except Exception as e:
                    st.error(f"❌ Error al guardar el archivo: {e}")

        st.markdown("---")
        st.markdown("### 🖼️ Logotipo de la Empresa")
        if os.path.exists(ruta_logo):
            st.image(ruta_logo, width=120, caption="Logotipo actual guardado")
   
        logo_cargado = st.file_uploader("Sube una imagen para tu logo (PNG o JPG)", type=["png", "jpg", "jpeg"], key="uploader_logo_empresa")
        if logo_cargado is not None:
            os.makedirs(tenant_dir, exist_ok=True)
            img = Image.open(logo_cargado)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(ruta_logo, "PNG")
            st.success("✅ ¡Logotipo procesado y actualizado con éxito!")
            st.rerun()

    st.markdown("---")
    st.markdown("### 🗂️ Administración de archivos")
    st.write("Gestiona la base de datos de tu negocio: descarga plantillas en blanco, exporta tu información actual o importa cargas masivas.")

    accion = st.radio(
        "¿Qué acción deseas realizar?",
        ("Selecciona una opción...", "Descargar plantilla en blanco", "Exportar base de datos actual", "Importar base de datos"),
        index=0,
        key="radio_adm_archivos_config"
    )

    if accion == "Descargar plantilla en blanco":
        st.info("💡 Descarga esta plantilla para completar tus productos respetando los encabezados requeridos para la carga masiva.")
        if os.path.exists(ruta_plantilla_base):
            with open(ruta_plantilla_base, "rb") as f:
                st.download_button(
                    label="⬇️ Descargar Plantilla Base (Excel)",
                    data=f,
                    file_name="plantilla_base_datos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("⚠️ No se encontró la plantilla base en el sistema.")

    elif accion == "Exportar base de datos actual":
        st.info("📦 Obtén una copia de seguridad con todos los registros actuales de tu inventario o base de datos.")
        if os.path.exists(ruta_bd_actual):
            with open(ruta_bd_actual, "rb") as f:
                st.download_button(
                    label="⬇️ Descargar mi Base de Datos Actual (Excel)",
                    data=f,
                    file_name="BASE_DE_DATOS_actual.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("⚠️ Todavía no existe un archivo 'BASE DE DATOS.xlsx' registrado para este negocio.")

    elif accion == "Importar base de datos":
        st.warning("⚠️ *Atención:* Al importar una nueva base de datos, se sobrescribirán los datos actuales de tu negocio.")
      
        archivo_cargado = st.file_uploader("Selecciona tu archivo Excel desde tu equipo", type=["xlsx"], key="uploader_importar_bd")
      
        if archivo_cargado is not None:
            if st.button("🚀 Confirmar y Reemplazar Base de Datos"):
                try:
                    df_nuevo = pd.read_excel(archivo_cargado)
                    df_nuevo.to_excel(ruta_bd_actual, index=False)
                    st.success("✅ ¡Base de datos importada y actualizada con éxito!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ocurrió un error al procesar el archivo: {e}")

# ----------------- SECCIÓN VENTAS / POS RÁPIDO (CONECTADO A LA NUBE Y AISLADO) -----------------
elif menu == "💰 Módulo de Ventas (POS)":
    caja_actual = param_caja if param_caja else "Caja Principal"
    rut_actual = st.session_state.get("negocio_seleccionado")
    mostrar_encabezado_con_home(f"Terminal de Ventas - {caja_actual}")

    tipo_documento = st.selectbox("Selecciona el documento:", ["Boleta Electrónica", "Factura Electrónica", "Guía de Despacho"])
    
    modo_inventario = st.radio(
        "📦 Modo de trabajo del POS:",
        ["Control Estricto de Stock (Alerta si no hay inventario)", "Venta Libre / Solo Base de Datos"],
        horizontal=True,
        key="radio_modo_inventario"
    )
    controlar_stock = "Estricto" in modo_inventario

    cliente_nombre, cliente_rut = "", ""

    # 1. Lógica de Selección de Clientes (Solo para Factura/Guía) BLINDADA POR EMPRESA
    if tipo_documento in ["Factura Electrónica", "Guía de Despacho"]:
        try:
            # Candado de seguridad: Filtramos estrictamente por el RUT del negocio activo
            res_clientes = supabase.table("clientes").select("rut, nombre").eq("id_negocio", rut_actual).execute()
            df_clientes_pos = pd.DataFrame(res_clientes.data) if res_clientes.data else pd.DataFrame()
            
            # Doble validación por si la columna de empresa en Supabase se llama distinto
            if df_clientes_pos.empty:
                res_clientes_alt = supabase.table("clientes").select("rut, nombre").eq("id_negocio", rut_actual).execute()
                df_clientes_pos = pd.DataFrame(res_clientes_alt.data) if res_clientes_alt.data else pd.DataFrame()
        except Exception as e:
            st.error(f"⚠️ Error conectando a la base de clientes en la nube: {e}")
            df_clientes_pos = pd.DataFrame()

        if not df_clientes_pos.empty and "nombre" in df_clientes_pos.columns:
            # Concatenamos el nombre y el RUT
            df_clientes_pos["etiqueta"] = df_clientes_pos["nombre"].astype(str) + " (" + df_clientes_pos["rut"].astype(str) + ")"
            lista_clientes = df_clientes_pos["etiqueta"].tolist()
            
            # Agregamos una opción en blanco al inicio para que no seleccione al primero por defecto
            lista_clientes.insert(0, "-- Selecciona un cliente --")
            cliente_elegido = st.selectbox("👤 Selecciona un cliente registrado:", lista_clientes)
          
            if cliente_elegido and cliente_elegido != "-- Selecciona un cliente --" and " (" in cliente_elegido:
                cliente_nombre = cliente_elegido.split(" (")[0]
                cliente_rut = cliente_elegido.split(" (")[1].replace(")", "")
        else:
            st.warning("⚠️ No hay clientes registrados para este negocio en la nube. Agrégalos en el módulo correspondiente.")
            col_f1, col_f2 = st.columns(2)
            with col_f1: cliente_nombre = st.text_input("Razón Social / Nombre del Cliente")
            with col_f2: cliente_rut = st.text_input("RUT / Identificación Tributaria")

    if st.session_state.ultimo_recibo is not None:
        st.success("🎉 ¡Transacción completada y archivada con éxito!")
        st.markdown(f'<div class="ticket-box">{st.session_state.ultimo_recibo}</div>', unsafe_allow_html=True)
      
        if 'items_recibo_actual' not in st.session_state or st.session_state.items_recibo_actual is None:
            st.session_state.items_recibo_actual = st.session_state.carrito_ventas.copy()

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if tipo_documento == "Guía de Despacho":
                items_a_imprimir = st.session_state.get('items_recibo_actual', st.session_state.carrito_ventas)
                pdf_bytes = generar_guia_pdf(cliente_nombre, cliente_rut, items_a_imprimir)
                st.download_button("📥 Descargar Guía PDF", data=bytes(pdf_bytes), file_name="Guia_Despacho.pdf", mime="application/pdf", use_container_width=True)
            else:
                st.download_button("📥 Descargar Recibo", data=st.session_state.ultimo_recibo, file_name="Comprobante.txt", mime="text/plain", use_container_width=True)
      
        with col_r2:
            if st.button("➕ Nueva Venta", use_container_width=True, type="primary"):
                st.session_state.ultimo_recibo = None
                st.session_state.estado_pago = False
                st.session_state.items_recibo_actual = None
                st.session_state.carrito_ventas = []
                st.rerun()

    elif st.session_state.estado_pago:
        st.markdown("### 💳 2. Formas de Pago")
        if len(st.session_state.carrito_ventas) > 0:
            df_temp = pd.DataFrame(st.session_state.carrito_ventas)
            total_venta = df_temp["Subtotal"].sum()
            st.info(f"💰 **Total a Pagar: ${total_venta:,.2f}**")
            opciones_pago = list(st.session_state.get("formas_pago_erp", ["Efectivo"]))
            for extra in ["Consignación", "Fiado", "Crédito"]:
                if extra not in opciones_pago:
                    opciones_pago.append(extra)
            forma_pago = st.selectbox("Selecciona la Forma de Pago:", options=opciones_pago)
       
            efectivo_recibido, cambio = total_venta, 0.0
            if forma_pago == "Efectivo":
                efectivo_recibido = st.number_input("💵 Dinero Recibido ($):", min_value=0.0, value=float(total_venta), step=100.0)
                if efectivo_recibido >= total_venta:
                    cambio = efectivo_recibido - total_venta
                    st.success(f"🟢 **Vuelto: ${cambio:,.2f}**")
                else:
                    st.error("🔴 Monto insuficiente.")

            st.divider()
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                if st.button("⬅️ Volver al Carrito", use_container_width=True):
                    st.session_state.estado_pago = False
                    st.rerun()
            with col_p2:
                if st.button("✅ Confirmar Pago y Generar", use_container_width=True, type="primary"):
                    if forma_pago == "Efectivo" and efectivo_recibido < total_venta:
                        st.warning("⚠️ Monto insuficiente para procesar la venta.")
                    else:
                        fecha_hora_actual = datetime.now()
                        transaccion_id_actual = f"TX_{fecha_hora_actual.strftime('%Y%m%d%H%M%S')}"
                        registros_nuevos, lineas_productos = [], ""
                        
                        # --- ☁️ SINCRONIZACIÓN CON SUPABASE: DESCUENTO DE STOCK Y REGISTRO DE VENTA ---
                        for item in st.session_state.carrito_ventas:
                            lineas_productos += f"- {item['Descripción']} (x{int(item['Cantidad'])}) ... ${item['Subtotal']:,.2f}\n"
                            
                            # 1. Descontar Stock en Supabase
                            try:
                                res_stock = supabase.table("productos").select("stock").eq("rut_empresa", rut_actual).eq("codigo", str(item["Código"])).execute()
                                if res_stock.data:
                                    stock_actual = float(res_stock.data[0]["stock"] or 0.0)
                                    nuevo_stock = stock_actual - float(item["Cantidad"])
                                    supabase.table("productos").update({"stock": nuevo_stock}).eq("rut_empresa", rut_actual).eq("codigo", str(item["Código"])).execute()
                            except Exception as e:
                                print(f"⚠️ Error descontando stock en Nube para {item['Código']}: {e}")

                            # 2. Preparar línea de venta para Supabase y Excel local
                            registro_linea = {
                                "rut_empresa": rut_actual,
                                "transaccion_id": transaccion_id_actual,
                                "fecha_hora": fecha_hora_actual.isoformat(),
                                "caja": caja_actual, 
                                "documento": tipo_documento,
                                "cliente": cliente_nombre if cliente_nombre else "Cliente General",
                                "codigo_producto": str(item["Código"]), 
                                "descripcion": str(item["Descripción"]),
                                "cantidad": float(item["Cantidad"]), 
                                "precio_unitario": float(item["Precio Unitario"]),
                                "subtotal": float(item["Subtotal"]), 
                                "forma_pago": forma_pago,
                                "total_boleta": float(total_venta)
                            }
                            
                            try:
                                supabase.table("ventas").insert(registro_linea).execute()
                            except Exception as e:
                                print(f"⚠️ Error registrando venta en Nube para {item['Código']}: {e}")
                            
                            # Preparamos el array local para el Excel de respaldo
                            registros_nuevos.append({
                                "TransaccionID": transaccion_id_actual,
                                "FechaHora": fecha_hora_actual.strftime("%Y-%m-%d %H:%M:%S"),
                                "Caja": caja_actual, "Documento": tipo_documento,
                                "Cliente": cliente_nombre if cliente_nombre else "Cliente General",
                                "RUT": cliente_rut if cliente_rut else "Sin RUT",
                                "Código": item["Código"], "Descripción": item["Descripción"],
                                "Cantidad": item["Cantidad"], "PrecioUnitario": item["Precio Unitario"],
                                "Subtotal": item["Subtotal"], "FormaPago": forma_pago,
                                "TotalBoleta": total_venta
                            })
                   
                        # --- 💾 RESPALDO LOCAL: EXCEL ---
                        archivo_mensual = os.path.join(ruta_negocio, f"Libro_Ventas_{fecha_hora_actual.strftime('%Y_%m')}.xlsx")
                        df_nuevo = pd.DataFrame(registros_nuevos)
                        if os.path.exists(archivo_mensual):
                            pd.concat([pd.read_excel(archivo_mensual), df_nuevo], ignore_index=True).to_excel(archivo_mensual, index=False)
                        else:
                            df_nuevo.to_excel(archivo_mensual, index=False)

                        if any(p in forma_pago.lower() for p in ["fiado", "crédito", "credito", "consignación", "consignacion"]):
                            archivo_cxp = os.path.join(ruta_negocio, "Cuentas_por_Cobrar.xlsx")
                            registro_cxp = pd.DataFrame([{
                                "Fecha": fecha_hora_actual.strftime("%Y-%m-%d"),
                                "Cliente": cliente_nombre if cliente_nombre else "Cliente General",
                                "TotalDeuda": total_venta,
                                "Abono": 0.0,
                                "SaldoPendiente": total_venta,
                                "FormaPago": forma_pago,
                                "Estado": "Pendiente"
                            }])
                            if os.path.exists(archivo_cxp):
                                pd.concat([pd.read_excel(archivo_cxp), registro_cxp], ignore_index=True).to_excel(archivo_cxp, index=False)
                            else:
                                registro_cxp.to_excel(archivo_cxp, index=False)

                        # --- 🖨️ GENERACIÓN DEL COMPROBANTE ---
                        cfg = st.session_state.get('config_ticket', {'nombre_empresa': 'MI EMPRESA', 'rut_empresa': '00.000.000-0', 'direccion': 'Santiago', 'pie_pagina': 'Gracias por su preferencia'})
                       
                        st.session_state.items_recibo_actual = st.session_state.carrito_ventas.copy()
                        
                        texto_recibo = f"""
========================================
       {cfg.get('nombre_empresa', 'MI EMPRESA')}
       RUT: {cfg.get('rut_empresa', '00.000.000-0')}
       {cfg.get('direccion', 'Santiago')}
========================================
DOCUMENTO: {tipo_documento.upper()}
FECHA: {fecha_hora_actual.strftime('%d/%m/%Y %H:%M:%S')}
TERMINAL: {caja_actual}
----------------------------------------
{('CLIENTE: ' + cliente_nombre + ' | RUT: ' + cliente_rut + '\n----------------------------------------\n') if tipo_documento in ['Factura Electrónica', 'Guía de Despacho'] else ''}DETALLE:
{lineas_productos}----------------------------------------
TOTAL: ${total_venta:,.2f}
PAGO: {forma_pago.upper()}
{('RECIBIDO: $' + f'{efectivo_recibido:,.2f}' + '\nVUELTO: $' + f'{cambio:,.2f}') if forma_pago == 'Efectivo' else ''}
========================================
{cfg.get('pie_pagina', 'Gracias por su preferencia')}
========================================"""
                        
                        try:
                            carpeta_tipo = tipo_documento.lower().replace(" ", "_").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
                            dir_archivador = os.path.join(ruta_negocio, "archivador_ventas", carpeta_tipo)
                            os.makedirs(dir_archivador, exist_ok=True)
                            
                            ruta_completa_doc = os.path.join(dir_archivador, f"{transaccion_id_actual}.txt")
                            
                            with open(ruta_completa_doc, "w", encoding="utf-8") as f_doc:
                                f_doc.write(texto_recibo)
                        except Exception as e:
                            print(f"Error al guardar en el archivador: {e}")

                        st.session_state.ultimo_recibo = texto_recibo
                        st.session_state.estado_pago = False
                        st.rerun()

        else:
            st.warning("⚠️ Carrito vacío.")
            if st.button("Volver"):
                st.session_state.estado_pago = False
                st.rerun()

    else:
        # --- LÓGICA DE INVENTARIO CONECTADA A LA NUBE (POS) ---
        df_nube = pd.DataFrame()
        try:
            res_pos = supabase.table("productos").select("codigo, descripcion, precio_venta, stock").eq("rut_empresa", rut_actual).limit(10000).execute()
            if res_pos.data:
                df_nube = pd.DataFrame(res_pos.data)
        except Exception as e:
            st.error(f"⚠️ Error conectando al inventario en la nube: {e}")

        if not df_nube.empty:
            col_cod = 'codigo'
            col_desc = 'descripcion'
            col_precio = 'precio_venta'
            col_stock = 'stock'

            metodo_lectura = st.radio("Método de entrada de código:", ["⌨️ Digitar / Lector Físico", "📷 Usar Cámara del Celular"], horizontal=True, key="radio_metodo_pos")

            codigo_escan_pos = ""

            if metodo_lectura == "📷 Usar Cámara del Celular":
                st.markdown("Apunta la cámara al código de barras y captura la foto:")
                foto_capturada = st.camera_input("Capturar código de barras", key="cam_pos")
                if foto_capturada is not None:
                    st.success("✔️ ¡Foto capturada con éxito!")
            else:
                codigo_escan_pos = st.text_input("📷 Digita el código o usa tu pistola láser:", key="input_escan_pos")

            opciones_productos = ["-- Selecciona o busca un producto --"] + [f"{row[col_cod]} - {row[col_desc]}" for idx, row in df_nube.iterrows()]
            prod_sugerido_pos_idx = 0
       
            if codigo_escan_pos:
                match_pos = df_nube[df_nube[col_cod].astype(str) == str(codigo_escan_pos)]
                if not match_pos.empty:
                    match_str_pos = f"{match_pos.iloc[0][col_cod]} - {match_pos.iloc[0][col_desc]}"
                    if match_str_pos in opciones_productos:
                        prod_sugerido_pos_idx = opciones_productos.index(match_str_pos)
                        st.success(f"✔️ Producto detectado: {match_str_pos}")
                    
                        st.session_state.precio_actual_input = float(match_pos.iloc[0][col_precio] or 0.0)
                        st.session_state.ultimo_prod_sel = match_str_pos

            if "ultimo_prod_sel" not in st.session_state:
                st.session_state.ultimo_prod_sel = ""
            if "precio_actual_input" not in st.session_state:
                st.session_state.precio_actual_input = 0.0

            producto_seleccionado = st.selectbox(
                "O selecciona manualmente el producto:",
                options=opciones_productos,
                index=prod_sugerido_pos_idx,
                key="selectbox_producto_venta"
            )
        
            if producto_seleccionado != st.session_state.ultimo_prod_sel:
                st.session_state.ultimo_prod_sel = producto_seleccionado
                if producto_seleccionado != "-- Selecciona o busca un producto --":
                    c_buscado = producto_seleccionado.split(" - ")[0]
                    match_row = df_nube[df_nube[col_cod].astype(str) == str(c_buscado)]
                    if not match_row.empty:
                        st.session_state.precio_actual_input = float(match_row.iloc[0][col_precio] or 0.0)
                else:
                    st.session_state.precio_actual_input = 0.0

            with st.form("form_agregar_item"):
                col_cant, col_precio_input = st.columns(2)
                with col_cant:
                    cantidad_vendida = st.number_input("Cantidad", min_value=1.0, step=1.0, value=1.0, format="%.2f")
                with col_precio_input:
                    precio_venta = st.number_input("Precio Unitario ($)", min_value=0.0, step=1.0, value=float(st.session_state.precio_actual_input))

                btn_agregar = st.form_submit_button("➕ Agregar al Carrito de Venta")

                if btn_agregar:
                    if producto_seleccionado == "-- Selecciona o busca un producto --":
                        st.warning("⚠️ Selecciona un producto válido.")
                    else:
                        c_buscado = producto_seleccionado.split(" - ")[0]
                        match_row = df_nube[df_nube[col_cod].astype(str) == str(c_buscado)]
                        
                        stock_disponible = 0.0
                        if not match_row.empty:
                            stock_disponible = float(match_row.iloc[0][col_stock] or 0.0)

                        unidades_en_carrito = sum(item["Cantidad"] for item in st.session_state.carrito_ventas if item["Código"] == c_buscado)
                        total_intentado = unidades_en_carrito + float(cantidad_vendida)

                        if controlar_stock and total_intentado > stock_disponible:
                            st.error(f"🚨 **¡Inventario Insuficiente en la Nube!** Stock disponible: {stock_disponible:,.2f} | Intentas vender: {total_intentado:,.2f}")
                        else:
                            st.session_state.carrito_ventas.append({
                                "Código": c_buscado,
                                "Descripción": producto_seleccionado.split(" - ")[1],
                                "Cantidad": float(cantidad_vendida),
                                "Precio Unitario": float(precio_venta),
                                "Subtotal": float(cantidad_vendida) * float(precio_venta)
                            })
                            st.success("✅ Producto agregado con éxito.")
                            st.rerun()
        else:
            st.info("ℹ️ Aún no hay productos registrados en tu base de datos en la nube.")

        st.divider()
        st.markdown("### 🛒 Carrito de Venta Actual:")
        if len(st.session_state.carrito_ventas) > 0:
            total_general, indices_a_eliminar = 0.0, []
            col_h1, col_h2, col_h3, col_h4, col_h5, col_h6 = st.columns([1.2, 2.5, 1.2, 1.5, 1.5, 0.8])
            col_h1.markdown("**Código**"); col_h2.markdown("**Descripción**"); col_h3.markdown("**Cantidad**"); col_h4.markdown("**Precio Unitario**"); col_h5.markdown("**Subtotal**"); col_h6.markdown("**Acción**")
            st.divider()

            for i, item in enumerate(st.session_state.carrito_ventas):
                col_c1, col_c2, col_c3, col_c4, col_c5, col_c6 = st.columns([1.2, 2.5, 1.2, 1.5, 1.5, 0.8])
                with col_c1: st.text(item["Código"])
                with col_c2: st.text(item["Descripción"])
                with col_c3:
                    nc = st.number_input("Cant", min_value=0.01, step=0.1, value=float(item["Cantidad"]), format="%.2f", key=f"cant_{i}", label_visibility="collapsed")
                    st.session_state.carrito_ventas[i]["Cantidad"] = nc
                    st.session_state.carrito_ventas[i]["Subtotal"] = nc * st.session_state.carrito_ventas[i]["Precio Unitario"]
                with col_c4:
                    np = st.number_input("Prec", min_value=0.0, step=1.0, value=float(item["Precio Unitario"]), key=f"prec_{i}", label_visibility="collapsed")
                    st.session_state.carrito_ventas[i]["Precio Unitario"] = np
                    st.session_state.carrito_ventas[i]["Subtotal"] = st.session_state.carrito_ventas[i]["Cantidad"] * np
                with col_c5:
                    sub = st.session_state.carrito_ventas[i]["Subtotal"]
                    st.text(f"${sub:,.2f}")
                    total_general += sub
                with col_c6:
                    if st.button("🗑️", key=f"del_{i}"): indices_a_eliminar.append(i)

            if indices_a_eliminar:
                for idx in sorted(indices_a_eliminar, reverse=True): st.session_state.carrito_ventas.pop(idx)
                st.rerun()

            st.divider()
            st.markdown(f"### 💰 **Total a Pagar: ${total_general:,.2f}**")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("🗑️ Vaciar Carrito Completo", use_container_width=True):
                    st.session_state.carrito_ventas = []
                    st.rerun()
            with col_b2:
                if st.button("[F12] 💳 Cobrar", use_container_width=True, key="btn_cobrar_principal") or st.session_state.get('ejecutar_cobro', False):
                    st.session_state.ejecutar_cobro = False
                    st.session_state.estado_pago = True
                    st.rerun()
        else:
            st.info("ℹ️ Carrito vacío.")

        components.html("""
        <script>
        const doc = window.parent.document;
        doc.addEventListener('keydown', function(e) {
            if (e.key === 'F12') {
                e.preventDefault();
                doc.querySelectorAll('button').forEach(btn => { if (btn.innerText.includes('Cobrar')) btn.click(); });
            } else if (e.key === 'Enter') {
                const activeEl = doc.activeElement;
                if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.getAttribute('role') === 'combobox')) {
                    doc.querySelectorAll('button').forEach(btn => { if (btn.innerText.includes('Agregar al Carrito de Venta')) btn.click(); });
                }
            }
        });
        </script>
        """, height=0)

elif menu == "📑 Cuentas por Cobrar":
    mostrar_modulo_cuentas_por_cobrar(ruta_negocio)

elif menu == "📒 Cuadratura Diaria":
    mostrar_encabezado_con_home("📒 Cuaderno de Cuadratura y Caja Diaria")
    mostrar_modulo_cuadratura_diaria(ruta_negocio)

elif menu == "🏦 Conciliación y Retiros Seguros": 
    mostrar_modulo_conciliacion_retiros(ruta_negocio)

elif menu == "📈 Reportes y Analítica":
    mostrar_modulo_reportes_avanzados(negocio_seleccionado)

elif menu == "🔑 Control Maestro de Licencias":
    mostrar_encabezado_con_home("🔑 Control Maestro de Licencias y Ciclos Fijos")
    st.info("ℹ️ Panel de administración exclusivo para ver el estado de todos los clientes y modificar sus fechas de vigencia.")

    try:
        res_lic = supabase.table("empresas").select("*").execute()
        lista_empresas_db = res_lic.data if res_lic and res_lic.data else []
    except Exception as e:
        lista_empresas_db = []
        st.error(f"⚠️ Error al conectar con Supabase: {e}")

    if lista_empresas_db:
        hoy_actual = date.today()
        tabla_resumen = []

        for emp in lista_empresas_db:
            rut_cli = str(emp.get("rut_empresa", "N/A"))
            nombre_cli = str(emp.get("empresa_nombre", "Sin Nombre"))
            f_exp_str = str(emp.get("fecha_expiracion", "2026-12-31"))
            
            try:
                dias_restantes = (pd.to_datetime(f_exp_str).date() - hoy_actual).days
            except Exception:
                dias_restantes = 999

            if dias_restantes > 5:
                estado_txt = "🟢 Activa"
            elif 0 <= dias_restantes <= 5:
                estado_txt = "🟡 En Gracia"
            else:
                estado_txt = "🔴 Expirada / Suspendida"

            tabla_resumen.append({
                "RUT (Usuario)": rut_cli,
                "Empresa": nombre_cli,
                "Vencimiento": f_exp_str,
                "Días Restantes": dias_restantes,
                "Estado": estado_txt
            })

        st.dataframe(pd.DataFrame(tabla_resumen), use_container_width=True)

        st.divider()
        st.markdown("### ✏️ Modificar Fechas de Vigencia y Ciclo Fijo")
        
        nombres_clientes_dict = {emp.get("rut_empresa"): f"{emp.get('empresa_nombre')} (RUT: {emp.get('rut_empresa')})" for emp in lista_empresas_db}
        rut_a_modificar = st.selectbox("Selecciona la Empresa a Gestionar:", options=list(nombres_clientes_dict.keys()), format_func=lambda x: nombres_clientes_dict[x])
        
        cliente_sel_data = next((emp for emp in lista_empresas_db if emp.get("rut_empresa") == rut_a_modificar), None)
        
        if cliente_sel_data:
            f_actual_exp_str = cliente_sel_data.get("fecha_expiracion")
            
            try:
                if f_actual_exp_str and str(f_actual_exp_str).strip() not in ["None", "NaT", "nan", ""]:
                    f_default_date = pd.to_datetime(str(f_actual_exp_str)).date()
                else:
                    f_default_date = hoy_actual
            except Exception:
                f_default_date = hoy_actual

            with st.form(f"form_mod_fechas_principal_{rut_a_modificar}"):
                st.write(f"📌 **Editando a:** {cliente_sel_data.get('empresa_nombre')}")
                
                nueva_fecha_fin = st.date_input("Fecha de Finalización del Periodo", value=f_default_date)
                
                estado_licencia = cliente_sel_data.get("licencia_activa")
                estado_licencia = True if estado_licencia is None else bool(estado_licencia)
                
                activar_licencia_check = st.checkbox("Licencia Activa (Desmarcar para suspensión total)", value=estado_licencia)

                if st.form_submit_button("💾 Guardar Nueva Vigencia en Supabase", type="primary"):
                    try:
                        supabase.table("empresas").update({
                            "fecha_expiracion": str(nueva_fecha_fin),
                            "licencia_activa": activar_licencia_check
                        }).eq("rut_empresa", rut_a_modificar).execute()

                        st.success(f"✅ ¡Vigencia actualizada correctamente! Nuevo vencimiento: {nueva_fecha_fin}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al actualizar en Supabase: {e}")
    else:
        st.warning("⚠️ No se encontraron registros de empresas en Supabase.")