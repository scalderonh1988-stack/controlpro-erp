import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, date
import streamlit.components.v1 as components
import sys
from data_manager import guardar_nuevo_cliente, cargar_maestro_clientes
from calendario_pagos import mostrar_modulo_calendario_pagos
from compras_cpp import mostrar_modulo_compras
from supabase import create_client, Client
from fpdf import FPDF
from PIL import Image

# --- RUTA SEGURA PARA DESARROLLO Y .EXE ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CLIENTES_DIR = os.path.join(BASE_DIR, "clientes")
PERMISOS_FILE = os.path.join(BASE_DIR, "permisos_negocios.json")

# Configuración inicial de la página web
st.set_page_config(
    page_title="ControlPRO ERP - Gestión Inteligente",
    page_icon="📦",
    layout="wide"
)

# Estilo visual limpio y centrado
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
    </style>
""", unsafe_allow_html=True)

# Inicializar estados de sesión unificados
if "es_admin" not in st.session_state:
    st.session_state["es_admin"] = False
if "cliente_logueado" not in st.session_state:
    st.session_state["cliente_logueado"] = None
if "negocio_seleccionado" not in st.session_state:
    st.session_state["negocio_seleccionado"] = None

# --- 🔌 CONEXIÓN PREVIA A SUPABASE PARA VALIDACIONES ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
    resultado = supabase.table("empresas").select("*").execute()
    empresas_data = resultado.data if resultado.data else []
except Exception as e:
    empresas_data = []

# --- 1. SI UN CLIENTE YA INICIÓ SESIÓN CORRECTAMENTE ---
if st.session_state["cliente_logueado"]:
    negocio_actual = st.session_state["cliente_logueado"]
    ruta_negocio_cliente = os.path.join(CLIENTES_DIR, negocio_actual)
    os.makedirs(ruta_negocio_cliente, exist_ok=True)
    
    st.sidebar.markdown(f"👤 **Cliente Conectado:** {negocio_actual}")
    if st.sidebar.button("🚪 Cerrar Sesión Cliente"):
        st.session_state["cliente_logueado"] = None
        st.session_state["negocio_seleccionado"] = None
        st.rerun()
        
    # --- AQUÍ CARGA EL HOME Y EL ENTORNO DE TRABAJO DEL CLIENTE ---
    st.markdown(f"<div class='main-title'>🏠 Bienvenido a tu ERP - {negocio_actual}</div>", unsafe_allow_html=True)
    st.divider()
    
    # Menú rápido o indicador de que el entorno está activo
    st.success("✅ Conexión establecida correctamente con tu espacio de trabajo.")
    
    # Puedes poner aquí las llamadas a los módulos de tu ERP pasando `ruta_negocio_cliente`:
    # Ejemplo: mostrar_modulo_cuentas_por_cobrar(ruta_negocio_cliente)
    
    st.stop() # Evita que se muestren las pantallas de login al estar conectado

# --- 2. SI ERES TÚ (ADMINISTRADOR) CON TU SESIÓN ACTIVA ---
if st.session_state["es_admin"]:
    with st.sidebar:
        st.markdown("### 🛠️ Control Maestro")
        if st.button("🔒 Cerrar Sesión Admin"):
            st.session_state["es_admin"] = False
            st.rerun()
           
        st.divider()
        st.markdown("#### ➕ Registrar Nuevo Cliente")
       
        with st.form("form_crear_cliente"):
            id_negocio = st.text_input("ID Carpeta (ej: negocio_2, sin espacios)")
            nombre_comercial = st.text_input("Nombre Comercial / Razón Social")
            password_cliente = st.text_input("Contraseña para el Cliente", type="password")
            fecha_exp = st.date_input("Fecha de Expiración", value=date(2026, 12, 31))
           
            m_home = st.checkbox("🏠 Home / Bienvenida", value=True)
            m_dash = st.checkbox("📊 Dashboard Ejecutivo", value=True)
            m_inv = st.checkbox("📦 Inventario y Productos", value=True)
            m_pos = st.checkbox("💰 Módulo de Ventas (POS)", value=True)
            m_comp = st.checkbox("🛒 Registrar Compra (CPP)", value=True)
            m_mermas = st.checkbox("📉 Mermas y Ajustes", value=True)
            m_inf = st.checkbox("📈 Informes y Movimientos [Extra]", value=False)
            m_ctrl = st.checkbox("⚠️ Control de Inventario [Extra]", value=False)
            m_fin = st.checkbox("📊 Módulo de Finanzas", value=True)
            m_conf = st.checkbox("⚙️ Configuración General", value=True)
            m_cuad = st.checkbox("📒 Cuadratura Diaria", value=True)
            m_cxp = st.checkbox("📑 Cuentas por Cobrar", value=True)
           
            guardar = st.form_submit_button("💾 Guardar y Crear Negocio")
            if guardar:
                if not id_negocio or not nombre_comercial:
                    st.warning("⚠️ Debes completar el ID y el Nombre.")
                else:
                    st.success(f"✨ ¡Negocio '{nombre_comercial}' creado con éxito!")
                    st.rerun()

    st.markdown("### 📊 Panel de Control Maestro (Lista de Empresas en Supabase)")
    st.dataframe(empresas_data, use_container_width=True)
    st.stop()

# --- 3. PESTAÑAS DE ACCESO (CLIENTES VS ADMIN) ---
st.markdown("<div class='main-title'>ControlPRO ERP - Portal de Acceso</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Selecciona tu tipo de acceso al sistema</div>", unsafe_allow_html=True)

tab_cliente, tab_admin = st.tabs(["👥 Acceso Clientes", "🛠️ Acceso Desarrollador (Admin)"])

# PESTAÑA CLIENTES: Validación directa contra Supabase y creación automática de su carpeta
with tab_cliente:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_login_cliente_directo"):
            st.markdown("#### Iniciar Sesión en tu Negocio")
            rut_cli = st.text_input("👤 Usuario / RUT de tu Negocio:")
            pass_cli = st.text_input("🔑 Contraseña:", type="password")
            entrar_cli = st.form_submit_button("🚀 Entrar a mi ERP", use_container_width=True)
            
            if entrar_cli:
                rut_limpio = rut_cli.strip()
                if not rut_limpio or not pass_cli.strip():
                    st.error("❌ Debes completar todos los campos.")
                else:
                    # Buscamos el RUT en la tabla empresas de Supabase
                    empresa_encontrada = next((emp for emp in empresas_data if emp.get("rut_empresa") == rut_limpio), None)
                    
                    if empresa_encontrada and empresa_encontrada.get("licencia_activa", True):
                        # Creamos su carpeta local de forma automática si no existe
                        os.path.join(CLIENTES_DIR, rut_limpio)
                        os.makedirs(os.path.join(CLIENTES_DIR, rut_limpio), exist_ok=True)
                        
                        st.session_state["cliente_logueado"] = rut_limpio
                        st.session_state["negocio_seleccionado"] = rut_limpio
                        st.success(f"✅ ¡Bienvenido! Ingresando al sistema...")
                        st.rerun()
                    else:
                        st.error("❌ RUT no registrado o licencia inactiva.")

# PESTAÑA ADMIN: Exclusiva para ti con credenciales maestras
with tab_admin:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_login_admin_maestro"):
            st.markdown("#### Panel de Control Maestro")
            user_adm = st.text_input("Usuario Administrador:")
            pass_adm = st.text_input("Contraseña Maestra:", type="password")
            entrar_adm = st.form_submit_button("🔐 Acceder como Desarrollador", use_container_width=True)
            
            if entrar_adm:
                if user_adm == "admin" and pass_adm == "SIMON1908":
                    st.session_state["es_admin"] = True
                    st.rerun()
                else:
                    st.error("❌ Credenciales de desarrollador inválidas.")

st.stop()

# --- FUNCIONES Y MÓDULOS DEL ERP (ABAJO DEL TODO) ---
def generar_guia_pdf(cliente_nombre, cliente_rut, carrito):
    pdf = FPDF(orientation='P', unit='mm', format='Letter')
    pdf.add_page()
  
    negocio_actual = str(st.session_state.get('negocio_seleccionado', '')).strip()
    tenant_dir = os.path.join(CLIENTES_DIR, negocio_actual) if negocio_actual else ""

    if tenant_dir:
        ruta_logo = os.path.join(tenant_dir, "logo_empresa.png")
        ruta_logo_fpdf = ruta_logo.replace('\\', '/')
        if os.path.exists(ruta_logo):
            try:
                pdf.image(ruta_logo_fpdf, x=10, y=8, w=25)
            except Exception as e:
                print(f"Error al cargar el logo en el PDF: {e}")

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
   
    return pdf.output(dest='S')

# Recuperamos los datos del negocio autenticado de forma segura
negocio_seleccionado = st.session_state.get("negocio_actual", None)

if negocio_seleccionado:
    ruta_negocio = os.path.join(CLIENTES_DIR, str(negocio_seleccionado))
    os.makedirs(ruta_negocio, exist_ok=True)
    # Buscamos de forma flexible cualquier archivo base que comience por BASE DE DATOS
    archivos_en_carpeta = os.listdir(ruta_negocio)
    archivo_base = next((os.path.join(ruta_negocio, f) for f in archivos_en_carpeta if f.startswith("BASE DE DATOS")), os.path.join(ruta_negocio, "BASE DE DATOS.xlsx"))
    archivo_compras = next((os.path.join(ruta_negocio, f) for f in archivos_en_carpeta if f.startswith("Libro_Compras")), os.path.join(ruta_negocio, "Libro_Compras.xlsx"))

# Botón de Cerrar Sesión en la Barra Lateral
st.sidebar.markdown(f"👤 Usuario: **{st.session_state.usuario_logueado}**")
st.sidebar.markdown(f"🏢 Negocio: *{st.session_state.nombre_empresa if 'nombre_empresa' in st.session_state else 'NINGUNO'}*")
if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state.autenticado = False
    st.session_state.negocio_actual = None
    st.session_state.usuario_logueado = None
    st.rerun()

st.sidebar.divider()

# ----------------- GESTIÓN DE LICENCIAS Y PERMISOS (PANEL DEV) -----------------
archivo_permisos = "permisos_negocios.json"

def cargar_permisos():
    if os.path.exists(archivo_permisos):
        with open(archivo_permisos, "r") as f:
            return json.load(f)
    return {}

def guardar_permisos(datos):
    with open(archivo_permisos, "w") as f:
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
    "⚙️ Configuración General"
]

# Panel de Desarrollador en la Barra Lateral
with st.sidebar.expander("🛠️ Panel de Desarrollador (Licencias)"):
    clave_dev = st.text_input("Clave Maestro Dev:", type="password", key="input_dev_key")
    if clave_dev == "SIMON1908":
        st.success("✔️ Modo Desarrollador Activo")
        negocio_a_modificar = st.selectbox("Selecciona Negocio a Configurar:", negocios_disponibles, key="sel_dev_negocio")
       
        db_permisos = cargar_permisos()
        if negocio_a_modificar not in db_permisos:
            db_permisos[negocio_a_modificar] = {mod: True for mod in modulos_totales}
       
        st.markdown(f"**Editando accesos para: {negocio_a_modificar}**")
        with st.form(f"form_licencia_{negocio_a_modificar}"):
            permisos_temporales = {}
            for mod in modulos_totales:
                estado_actual = db_permisos[negocio_a_modificar].get(mod, True)
                permisos_temporales[mod] = st.checkbox(mod, value=estado_actual, key=f"chk_{negocio_a_modificar}_{mod}")
           
            if st.form_submit_button("💾 Guardar Licencia"):
                db_permisos[negocio_a_modificar] = permisos_temporales
                guardar_permisos(db_permisos)
                st.success("✅ ¡Licencia actualizada!")
                st.rerun()

# ----------------- INICIALIZACIÓN DE LA MEMORIA DE SESIÓN -----------------
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
        "Efectivo",
        "Tarjeta de Débito",
        "Tarjeta de Crédito",
        "Transferencia Electrónica",
        "Cheque",
        "Cuenta Corriente / Crédito Directo"
    ]

if "config_ticket" not in st.session_state:
    st.session_state.config_ticket = {
        "nombre_empresa": f"CONTROLPRO - {str(negocio_seleccionado).upper() if negocio_seleccionado else 'GENERAL'}",
        "rut_empresa": "76.123.456-K",
        "direccion": "Av. Principal 123",
        "pie_pagina": "¡GRACIAS POR SU PREFERENCIA!",
        "formato_impresion": "80mm (Térmica Estándar)"
    }

query_params = st.query_params
param_caja = query_params.get("caja", None)

# Filtrado dinámico de módulos según el archivo de permisos del negocio
db_permisos_actual = cargar_permisos()
permisos_del_negocio = db_permisos_actual.get(negocio_seleccionado, {})

lista_modulos_permitidos = [
    mod for mod in modulos_totales if permisos_del_negocio.get(mod, True)
]

if not lista_modulos_permitidos:
    lista_modulos_permitidos = ["🏠 Home / Bienvenida"]

menu = st.sidebar.selectbox(
    "🧭 Selecciona un Módulo:",
    lista_modulos_permitidos,
    index=lista_modulos_permitidos.index(st.session_state.menu_seleccionado) if st.session_state.menu_seleccionado in lista_modulos_permitidos else 0
)

st.session_state.menu_seleccionado = menu

def cargar_datos(path_db):
    if os.path.exists(path_db):
        df = pd.read_excel(path_db, dtype={'Código': str})
        # Filtramos para mantener solo los productos activos en el POS
        if 'Activo' in df.columns:
            df = df[df['Activo'].astype(str).str.strip().str.capitalize() == 'Si']
        return df
    return None

df_base = cargar_datos(archivo_base) if ('archivo_base' in globals() and archivo_base) else None

def mostrar_encabezado_con_home(titulo_modulo):
    col_titulo, col_btn = st.columns([4, 1])
    with col_titulo:
        # 🏢 Usamos el nombre de la empresa de la sesión
        nombre_mostrar = st.session_state.get('nombre_empresa', negocio_seleccionado)
        st.subheader(f"{titulo_modulo} (Negocio: {nombre_mostrar})")
    with col_btn:
        st.write("")
        if st.button("🏠 Volver al Home", use_container_width=True):
            st.session_state.menu_seleccionado = "🏠 Home / Bienvenida"
            st.rerun()

if param_caja:
    menu = "💰 Módulo de Ventas (POS)"
    st.sidebar.info(f"🖥️ Modo Terminal Activo: **{param_caja}**")

# ----------------- SECCIÓN HOME FIJO -----------------
if menu == "🏠 Home / Bienvenida":
    st.markdown(f"<p class='main-title'>🪙 ControlPRO ERP: {st.session_state.nombre_empresa if 'nombre_empresa' in st.session_state else 'GENERAL'}</p>", unsafe_allow_html=True)
    st.markdown("<p class='sub-title'>Selecciona un módulo para comenzar:</p>", unsafe_allow_html=True)

    # 1. Definimos los módulos con una clave única de identificación y sus nombres reales en los permisos
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
        {"id": "conf", "nombre_ref": "Configuración General", "label": "⚙️ Configuración General"}
    ]

    # 2. Verificamos contra la lista permitida contemplando posibles variaciones con emojis
    botones_activos = []
    for mod in modulos_disponibles_home:
        # Comprobamos si el nombre de referencia o alguna variante con emoji está en los permisos permitidos
        permitido = any(mod["nombre_ref"].lower() in str(p).lower() for p in lista_modulos_permitidos)
        if permitido:
            botones_activos.append(mod)

    # 3. Dibujamos dinámicamente en filas de 2 columnas alineadas perfectamente
    if botones_activos:
        num_columnas = 2
       
        for i in range(0, len(botones_activos), num_columnas):
            fila_mods = botones_activos[i:i + num_columnas]
            cols = st.columns(num_columnas)
           
            for idx_col, mod in enumerate(fila_mods):
                with cols[idx_col]:
                    if st.button(mod["label"], use_container_width=True, key=f"btn_home_{mod['id']}"):
                        # Buscamos el nombre exacto correspondiente en los permisos para redirigir bien
                        nombre_destino = next((p for p in lista_modulos_permitidos if mod["nombre_ref"].lower() in str(p).lower()), mod["nombre_ref"])
                        st.session_state.menu_seleccionado = nombre_destino
                        st.rerun()
    else:
        st.info("ℹ️ Tu licencia actual no tiene módulos activos asignados. Revisa el panel de desarrollador o permisos.")

# ----------------- SECCIÓN DASHBOARD EJECUTIVO -----------------
elif menu == "📊 Dashboard Ejecutivo":
    mostrar_encabezado_con_home("⚡ Resumen Ejecutivo en Tiempo Real")
   
    archivos_v = [f for f in os.listdir(ruta_negocio) if f.startswith("Libro_Ventas_") and f.endswith(".xlsx")]
    total_ventas_historico = 0.0
    if archivos_v:
        for ar in archivos_v:
            path_v = os.path.join(ruta_negocio, ar)
            df_temp_v = pd.read_excel(path_v)
            if not df_temp_v.empty:
                col_tot = next((c for c in df_temp_v.columns if 'total' in str(c).lower()), None)
                if col_tot:
                    total_ventas_historico += df_temp_v.drop_duplicates(subset=["TransaccionID"])[col_tot].sum()

    retiro_diario = total_ventas_historico * 0.10

    # Cálculos financieros del inventario
    if df_base is not None and not df_base.empty:
        df_base['Costo'] = pd.to_numeric(df_base['Costo'], errors='coerce').fillna(0)
        df_base['Precio de Venta'] = pd.to_numeric(df_base['Precio de Venta'], errors='coerce').fillna(0)
        df_base['Stock'] = pd.to_numeric(df_base['Stock'], errors='coerce').fillna(0) # Ajusta 'Stock' si tu columna tiene otro nombre exacto

        inversion_total = (df_base['Costo'] * df_base['Stock']).sum()
        valor_venta_total = (df_base['Precio de Venta'] * df_base['Stock']).sum()
        ganancia_potencial = valor_venta_total - inversion_total
    else: inversion_total = valor_venta_total = ganancia_potencial = 0.0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="💰 Venta Total Acumulada", value=f"${total_ventas_historico:,.2f}")
    with col2:
        st.metric(label="💵 Retiro Diario Sugerido", value=f"${retiro_diario:,.2f}")
    with col3:
        total_productos = len(df_base) if df_base is not None else 0
        st.metric(label="📦 Total Productos", value=total_productos)
    with col4:
        st.metric(label="🚨 Alertas de Quiebre", value="0", delta="Estable")

# 📉 Resumen Financiero del Inventario
    col_inv1, col_inv2, col_inv3 = st.columns(3)
    with col_inv1:
        st.metric(label="📉 Inversión Total (Costo)", value=f"${inversion_total:,.2f}")
    with col_inv2:
        st.metric(label="📈 Valor Venta Potencial", value=f"${valor_venta_total:,.2f}")
    with col_inv3:
        st.metric(label="💰 Ganancia Potencial", value=f"${ganancia_potencial:,.2f}")

# ----------------- SECCIÓN INVENTARIO GENERAL -----------------
elif menu == "📦 Inventario y Productos":
    mostrar_encabezado_con_home("Gestión de Bases de Datos")
   
    # Creamos pestañas internas para separar cada base de datos limpiamente
    tab_prod, tab_cli, tab_prov = st.tabs(["📦 Productos / Inventario", "👥 Clientes", "🚚 Proveedores"])
   
    with tab_prod:
        st.markdown("### 📦 Administración de Productos")
        if df_base is not None:
            st.success(f"✅ Base de datos conectada con éxito. Total de productos registrados: {len(df_base)}")
           
            # Si prefieres mostrar los productos con el mismo diseño tabular detallado y botones de eliminar:
            st.markdown("#### 📂 Listado General de Inventario")
            if not df_base.empty:
                # Detectamos columnas de forma automática
                c_cod = next((c for c in df_base.columns if 'código' in str(c).lower() or 'codigo' in str(c).lower() or 'ean' in str(c).lower()), df_base.columns[0])
                c_desc = next((c for c in df_base.columns if 'descripción' in str(c).lower() or 'nombre' in str(c).lower() or 'producto' in str(c).lower()), df_base.columns[1])
                c_stock = next((c for c in df_base.columns if 'stock' in str(c).lower() or 'cantidad' in str(c).lower()), None)
                c_precio = next((c for c in df_base.columns if 'precio' in str(c).lower() or 'venta' in str(c).lower()), None)
                c_costo = next((c for c in df_base.columns if 'costo' in str(c).lower()), None)

                # Cabeceras visuales de la tabla
                h1, h2, h3, h4, h5, h6 = st.columns([2, 3, 1, 1, 1, 0.8])
                with h1: st.markdown("**Código**")
                with h2: st.markdown("**Descripción**")
                with h3: st.markdown("**Costo**")
                with h4: st.markdown("**Precio Venta**")
                with h5: st.markdown("**Stock**")
                with h6: st.markdown("**Acción**")
                st.markdown("---")

                for idx_p, row_p in df_base.iterrows():
                    val_cod = str(row_p.get(c_cod, ''))
                    val_desc = str(row_p.get(c_desc, ''))
                    val_costo = float(row_p.get(c_costo, 0)) if c_costo and pd.notna(row_p.get(c_costo, 0)) else 0.0
                    val_precio = float(row_p.get(c_precio, 0)) if c_precio and pd.notna(row_p.get(c_precio, 0)) else 0.0
                    val_stock = row_p.get(c_stock, 0) if c_stock else 0

                    c1, c2, c3, c4, c5, c6 = st.columns([2, 3, 1, 1, 1, 0.8])
                    with c1: st.write(val_cod)
                    with c2: st.write(val_desc)
                    with c3: st.write(f"${val_costo:,.0f}")
                    with c4: st.write(f"${val_precio:,.0f}")
                    with c5: st.write(str(val_stock))
                    with c6:
                        if st.button("🗑️", key=f"del_prod_inv_{idx_p}", help="Eliminar este producto"):
                            df_base_act = df_base.drop(idx_p).reset_index(drop=True)
                            df_base_act.to_excel(archivo_base, index=False)
                            st.success("✅ Producto eliminado correctamente.")
                            st.rerun()
            else:
                st.info("ℹ️ No hay productos cargados en la base de datos.")
        else:
            st.error(f"⚠️ No se encontró el archivo de base de datos en la carpeta del negocio '{negocio_seleccionado}'.")
       
    with tab_cli:
        st.markdown("### 👥 Administración de Clientes")
       
        # Formulario de Registro de Nuevo Cliente
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

        # Visualización de la Base de Datos de Clientes
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
       
        # Formulario de Registro de Nuevo Proveedor
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

        # Visualización de la Base de Datos de Proveedores
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

            # Método de búsqueda similar al de compras/ventas
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

            # Formulario de registro de merma
            with st.form("form_registrar_merma"):
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    cant_merma = st.number_input("Cantidad a dar de baja / Ajustar", min_value=1.0, step=1.0, value=1.0)
                with col_m2:
                    motivo_merma = st.selectbox("Motivo de la Baja", ["Merma / Rotura", "Vencimiento / Caducado", "Consumo Interno", "Ajuste por Diferencia de Inventario"])

                observacion_merma = st.text_input("Observación opcional (Ej: Rotura en pasillo, vencido del semáforo)")

                # Verificamos si el producto tiene lotes activos para ofrecer seleccionarlo
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
                        # Extraer código y descripción
                        desc_p_merma = prod_seleccionado_merma.split(" - ")[1]

                        # 1. Descontar del stock general de la base de datos de productos
                        match_prod_b = df_base[df_base[col_cod].astype(str) == str(codigo_p_merma)]
                        if not match_prod_b.empty:
                            idx_b = match_prod_b.index[0]
                            stock_actual_b = float(df_base.at[idx_b, col_stock]) if not pd.isna(df_base.at[idx_b, col_stock]) else 0.0
                           
                            nuevo_stock_b = max(0.0, stock_actual_b - cant_merma)
                            df_base.at[idx_b, col_stock] = nuevo_stock_b
                            df_base.to_excel(archivo_base, index=False)

                        # 2. Descontar del lote específico si aplica
                        lote_limpio = "N/A"
                        if lotes_disponibles_prod and lote_seleccionado_str:
                            # Extraer el nombre del lote del texto seleccionado (Ej: "Lote: LOTE-001 (Disponibles...")
                            import re
                            match_lote_ext = re.search(r'Lote:\s*(.*?)\s*\(Disponibles', lote_seleccionado_str)
                            if match_lote_ext:
                                lote_limpio = match_lote_ext.group(1).strip()
                               
                                df_lotes_up = pd.read_excel(archivo_lotes, dtype={'Código': str})
                                match_lote_row = df_lotes_up[(df_lotes_up['Código'].astype(str) == str(codigo_p_merma)) & (df_lotes_up['Lote'].astype(str) == str(lote_limpio))]
                               
                                if not match_lote_row.empty:
                                    idx_l = match_lote_row.index[0]
                                    cant_dispo_lote = float(df_lotes_up.at[idx_l, 'CantidadDisponible'])
                                    df_lotes_up.at[idx_l, 'CantidadDisponible'] = max(0.0, cant_dispo_lote - cant_merma)
                                    df_lotes_up.to_excel(archivo_lotes, index=False)

                        # 3. Guardar el registro en el historial de mermas (base_mermas.xlsx)
                        archivo_mermas = os.path.join(ruta_negocio, "base_mermas.xlsx") if 'ruta_negocio' in globals() else "base_mermas.xlsx"
                        nuevo_reg_merma = pd.DataFrame([{
                            "FechaHora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Código": codigo_p_merma,
                            "Descripción": desc_p_merma,
                            "Cantidad": cant_merma,
                            "Motivo": motivo_merma,
                            "Lote": lote_limpio,
                            "Observacion": observacion_merma if observacion_merma else "Sin observaciones"
                        }])

                        if os.path.exists(archivo_mermas):
                            df_hist_mermas = pd.read_excel(archivo_mermas, dtype={'Código': str})
                            pd.concat([df_hist_mermas, nuevo_reg_merma], ignore_index=True).to_excel(archivo_mermas, index=False)
                        else:
                            nuevo_reg_merma.to_excel(archivo_mermas, index=False)

                        st.success(f"✅ ¡Merma registrada con éxito! Se descontaron {cant_merma} unidades de '{desc_p_merma}'.")
                        st.rerun()

            # Mostrar historial reciente de mermas del negocio
            archivo_mermas_ver = os.path.join(ruta_negocio, "base_mermas.xlsx") if 'ruta_negocio' in globals() else "base_mermas.xlsx"
            if os.path.exists(archivo_mermas_ver):
                st.divider()
                st.markdown("### 📊 Historial de Mermas y Ajustes Registrados")
                df_ver_mermas = pd.read_excel(archivo_mermas_ver, dtype={'Código': str})
                if not df_ver_mermas.empty:
                    st.dataframe(df_ver_mermas.tail(15), use_container_width=True)
                else:
                    st.info("ℹ️ Aún no hay registros en el historial de mermas.")
        else:
            st.warning("⚠️ No se encontró la columna de stock en la base de datos de productos.")
    else:
        st.error(f"⚠️ No se encontró la base de datos para '{negocio_seleccionado}'.")

# ---------------- SECCIÓN FINANZAS ----------------
elif menu == "📊 Módulo de Finanzas":
    mostrar_encabezado_con_home("📊 Panel de Control Financiero y Gastos")
   
    # Creamos las 3 pestañas internas idénticas al estilo de inventario
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
        mostrar_modulo_registro_gastos(ruta_negocio)

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
  
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🚦 Semáforo de Vencimientos", "📦 Sugerencia de Reabastecimiento", "🛑 Control de Sobrestock"])

    with sub_tab1:
        st.markdown("### 🚦 Clasificación Automática de Vencimientos (Lotes Activos)")
      
        # Leemos la base de lotes independientes que creamos en compras
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
               
                # Ignoramos si no tiene lote o fecha válida
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
                       
                        # Filtramos los que están dentro del rango de los próximos 30 días o vencidos
                        if dias <= 7:
                            roja.append(item)
                        elif 8 <= dias <= 15:
                            amarilla.append(item)
                        elif 16 <= dias <= 30:
                            verde.append(item)
                    except Exception as e:
                        pass

            c1, c2, c3 = st.columns(3)
            with c1:
                st.error(f"🔴 Zona Roja <= 7 días ({len(roja)})")
                if roja:
                    st.dataframe(pd.DataFrame(roja), use_container_width=True)
                else:
                    st.caption("Sin productos en riesgo crítico.")
            with c2:
                st.warning(f"🟡 Zona Amarilla 8-15 días ({len(amarilla)})")
                if amarilla:
                    st.dataframe(pd.DataFrame(amarilla), use_container_width=True)
                else:
                    st.caption("Sin productos en alerta media.")
            with c3:
                st.success(f"🟢 Zona Verde 16-30 días ({len(verde)})")
                if verde:
                    st.dataframe(pd.DataFrame(verde), use_container_width=True)
                else:
                    st.caption("Sin productos próximos a vencer.")
        else:
            st.info("ℹ️ Aún no hay registros de lotes con fecha de vencimiento guardados para este negocio.")

    with sub_tab2:
        st.markdown("### 📦 Asistente de Reabastecimiento Automático (Lead Time 72 horas)")
        if df_base is not None:
            col_stock = next((c for c in df_base.columns if 'stock' in str(c).lower() or 'cantidad' in str(c).lower() or 'existencia' in str(c).lower()), None)
            col_desc = next((c for c in df_base.columns if 'descripción' in str(c).lower() or 'nombre' in str(c).lower()), 'Descripción')
            col_cod = next((c for c in df_base.columns if 'código' in str(c).lower() or 'codigo' in str(c).lower()), df_base.columns[0])

            if col_stock:
                sugerencias = []
                for idx, row in df_base.iterrows():
                    stock = float(row.get(col_stock, 0)) if pd.notna(row.get(col_stock)) else 0.0
                    demanda_semanal, consumo_72h = 10.0, (10.0 / 7.0) * 3.0
                    if stock <= consumo_72h:
                        sugerencias.append({'Código': str(row.get(col_cod, '')), 'Descripción': str(row.get(col_desc, '')), 'Stock Actual': stock, 'Sugerido a Comprar': round(demanda_semanal - stock + consumo_72h, 2)})
                if sugerencias:
                    st.warning(f"⚠️ {len(sugerencias)} productos en riesgo de quiebre.")
                    st.dataframe(pd.DataFrame(sugerencias), use_container_width=True)
                else:
                    st.success("✔️ Todo el inventario soporta holgadamente las 72 horas de entrega.")
            else:
                st.warning("⚠️ Falta la columna de stock.")
        else:
            st.error("⚠️ Falta la base de datos.")

    with sub_tab3:
        st.markdown("### 🛑 Control de Capital Inmovilizado y Exceso de Stock (> 4 semanas)")
        if df_base is not None:
            col_stock = next((c for c in df_base.columns if 'stock' in str(c).lower() or 'cantidad' in str(c).lower() or 'existencia' in str(c).lower()), None)
            col_desc = next((c for c in df_base.columns if 'descripción' in str(c).lower() or 'nombre' in str(c).lower()), 'Descripción')
            col_cod = next((c for c in df_base.columns if 'código' in str(c).lower() or 'codigo' in str(c).lower()), df_base.columns[0])

            if col_stock:
                excesos = []
                for idx, row in df_base.iterrows():
                    stock = float(row.get(col_stock, 0)) if pd.notna(row.get(col_stock)) else 0.0
                    if (stock / 10.0) > 4.0:
                        excesos.append({'Código': str(row.get(col_cod, '')), 'Descripción': str(row.get(col_desc, '')), 'Stock Actual': stock, 'Semanas': round(stock / 10.0, 1)})
                if excesos:
                    st.warning(f"💡 {len(excesos)} productos con sobrestock detectados.")
                    st.dataframe(pd.DataFrame(excesos), use_container_width=True)
                else:
                    st.success("✔️ Inventario optimizado. Sin capital inmovilizado.")
            else:
                st.warning("⚠️ Falta la columna de stock.")
        else:
            st.error("⚠️ Falta la base de datos.")

# ----------------- SECCIÓN COMPRAS -----------------
elif menu == "🛒 Registrar Compra (CPP)":
    mostrar_encabezado_con_home("🛒 Registrar Compra (CPP)")

    if df_base is not None:
        col_cod = next((c for c in df_base.columns if 'código' in str(c).lower() or 'codigo' in str(c).lower() or 'ean' in str(c).lower()), df_base.columns[0])
        col_desc = next((c for c in df_base.columns if 'descripción' in str(c).lower() or 'nombre' in str(c).lower() or 'producto' in str(c).lower()), df_base.columns[1])
        col_stock = next((c for c in df_base.columns if 'stock' in str(c).lower() or 'cantidad' in str(c).lower()), None)
        col_precio = next((c for c in df_base.columns if 'precio' in str(c).lower() or 'venta' in str(c).lower()), None)

        accion_producto = st.radio("Selecciona una opción:", ["📥 Registrar Compra (Factura con Lotes)", "➕ Crear Producto Nuevo", "✏️ Editar Producto Existente"], horizontal=True)
        st.divider()

        if accion_producto == "📥 Registrar Compra (Factura con Lotes)":
            st.markdown("### 📋 Cabecera de la Factura")

            # Cargamos los proveedores desde la base de datos o ruta de negocio de manera segura
            path_db = archivo_base if ('archivo_base' in globals() and archivo_base) else "base_datos.xlsx"
            try:
                df_prov_list = pd.read_excel(path_db, sheet_name="BD_Proveedores", dtype={'RUT': str})
                lista_proveedores = df_prov_list['Nombre'].tolist() if not df_prov_list.empty else ["Sin Proveedores Registrados"]
            except Exception:
                # Fallback si la hoja no existe en el archivo principal, revisamos archivo dedicado
                try:
                    archivo_prov_alt = os.path.join(ruta_negocio, "Maestro_Proveedores.xlsx") if 'ruta_negocio' in globals() else "Maestro_Proveedores.xlsx"
                    if os.path.exists(archivo_prov_alt):
                        df_prov_list = pd.read_excel(archivo_prov_alt)
                        lista_proveedores = df_prov_list['Nombre_Proveedor'].tolist() if 'Nombre_Proveedor' in df_prov_list.columns else ["Proveedor General"]
                    else:
                        lista_proveedores = ["Proveedor General"]
                except Exception:
                    lista_proveedores = ["Proveedor General"]

            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                proveedor_factura = st.selectbox("Nombre del Proveedor", options=lista_proveedores)
                num_factura = st.text_input("Número de Factura")
            with col_f2:
                fecha_compra = st.date_input("Fecha de Compra", value=date.today())
                condicion_pago = st.selectbox("Condición de Pago", ["Contado", "Crédito", "Cheque"])
            with col_f3:
                col_imp_esp = next((c for c in df_base.columns if 'impuesto' in str(c).lower() or 'específico' in str(c).lower() or ' ila ' in str(c).lower() or 'iaba' in str(c).lower()), None)
                st.write("")
                st.write(f"🔍 Columna de Impuestos: **{'Detectada' if col_imp_esp else 'No detectada'}**")

            # Campos dinámicos para Crédito o Cheque
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
            st.markdown("#### 🔍 Agregar Productos de la Factura")

            if 'carrito_factura_compras' not in st.session_state:
                st.session_state.carrito_factura_compras = []

            # 1. Búsqueda de producto fuera del formulario para que sea reactiva
            metodo_entrada_prod = st.radio("Método para buscar producto:", ["⌨️ Escáner / Pistola Láser (Código)", "🔎 Buscar por Nombre / Palabra Clave"], horizontal=True)
        
            prod_seleccionado_item = None
            opciones_productos = ["-- Selecciona un producto --"] + [f"{row[col_cod]} - {row[col_desc]}" for idx, row in df_base.iterrows()]

            if metodo_entrada_prod == "⌨️ Escáner / Pistola Láser (Código)":
                codigo_buscado = st.text_input("Pistola láser / Digitar Código EAN:", key="input_pistola_compra")
                if codigo_buscado:
                    match_p = df_base[df_base[col_cod].astype(str) == str(codigo_buscado)]
                    if not match_p.empty:
                        prod_seleccionado_item = f"{match_p.iloc[0][col_cod]} - {match_p.iloc[0][col_desc]}"
                        st.success(f"✔️ Producto encontrado: {prod_seleccionado_item}")
                    else:
                        st.warning("⚠️ No se encontró ningún producto con ese código.")
            else:
                prod_seleccionado_item = st.selectbox("Selecciona o busca por palabra clave:", options=opciones_productos, key="select_palabra_clave_compra")

            # 2. Controles fuera del form para que el despliegue de lote sea inmediato
            col_item1, col_item2, col_item3 = st.columns(3)
            with col_item1:
                cant_item = st.number_input("Cantidad", min_value=1.0, step=1.0, value=1.0)
            with col_item2:
                neto_unit_item = st.number_input("Valor Neto Unitario ($)", min_value=0.0, step=1.0, value=0.0)
            with col_item3:
                maneja_lote = st.selectbox("¿Maneja Lote y Vencimiento?", ["No", "Sí"])

            lote_item = "SIN-LOTE"
            venc_item = str(date.today())

            if maneja_lote == "Sí":
                st.markdown("📌 **Ingrese los datos reales del lote:**")
                col_l1, col_l2 = st.columns(2)
                with col_l1:
                    lote_item = st.text_input("N° Lote", value="LOTE-001")
                with col_l2:
                    venc_item_date = st.date_input("Fecha de Vencimiento Lote", value=date.today())
                    venc_item = str(venc_item_date)

            # Botón para añadir al listado temporal
            if st.button("➕ Agregar Línea a la Factura", type="primary"):
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
                    st.success(f"✅ ¡Línea agregada!")
                    st.rerun()

            # 3. Mostrar el listado acumulado y procesar factura completa
            if st.session_state.carrito_factura_compras:
                st.markdown("#### 📦 Productos Agregados en esta Factura")
            
                for idx_c, item in enumerate(st.session_state.carrito_factura_compras):
                    c_col1, c_col2 = st.columns([8, 1])
                    with c_col1:
                        st.info(f"**{item['Cantidad']}x** {item['Descripción']} | Neto: ${item['NetoUnitario']:,.0f} | **Costo Unit. c/Imp: ${item['CostoUnitarioFinal']:,.0f}** | Total c/Imp: ${item['CostoTotal']:,.0f} | Lote: {item['Lote']} ({item['FechaVencimiento']})")
                    with c_col2:
                        if st.button("❌", key=f"del_linea_{idx_c}", help="Eliminar esta línea"):
                            st.session_state.carrito_factura_compras.pop(idx_c)
                            st.rerun()

                monto_total_factura_general = sum(item["CostoTotal"] for item in st.session_state.carrito_factura_compras)
                st.markdown(f"### 💰 **Monto Total de la Factura (con Impuestos): ${monto_total_factura_general:,.2f}**")

                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("🗑️ Limpiar / Vaciar Listado", type="secondary"):
                        st.session_state.carrito_factura_compras = []
                        st.rerun()
                with col_b2:
                    if st.button("💾 Procesar Factura Completa y Actualizar Stock/Finanzas", type="primary"):
                        if not num_factura:
                            st.warning("⚠️ Ingresa el Número de Factura antes de procesar.")
                        else:
                            # Asegurar persistencia del proveedor en maestro de proveedores
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
                            for item in st.session_state.carrito_factura_compras:
                                nuevo_reg_compra = pd.DataFrame([{
                                    "FechaHora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "Proveedor": prov_final,
                                    "Factura": num_factura,
                                    "Código": item["Código"],
                                    "Descripción": item["Descripción"],
                                    "Cantidad": item["Cantidad"],
                                    "NetoUnitario": item["NetoUnitario"],
                                    "SubtotalNeto": item["SubtotalNeto"],
                                    "IVA": item["IVA"],
                                    "ImpuestoEspecifico": item["ImpuestoEspecifico"],
                                    "CostoTotal": item["CostoTotal"],
                                    "ManejaLote": item["ManejaLote"],
                                    "Lote": item["Lote"],
                                    "FechaVencimientoLote": item["FechaVencimiento"],
                                    "Condicion_Pago": condicion_pago,
                                    "FechaVencimientoPago": str(fecha_vencimiento_pago),
                                    "Banco": banco_cheque,
                                    "N_Serie": num_serie_cheque,
                                    "Estado": estado_inicial
                                }])

                                archivo_compras_path = os.path.join(ruta_negocio, "Registro_Compras.xlsx") if 'ruta_negocio' in globals() else "Registro_Compras.xlsx"
                                if os.path.exists(archivo_compras_path):
                                    df_ec = pd.read_excel(archivo_compras_path, dtype={'Código': str, 'Factura': str})
                                    pd.concat([df_ec, nuevo_reg_compra], ignore_index=True).to_excel(archivo_compras_path, index=False)
                                else:
                                    nuevo_reg_compra.to_excel(archivo_compras_path, index=False)

                                if item["ManejaLote"] == "Sí":
                                    archivo_lotes = os.path.join(ruta_negocio, "base_lotes.xlsx") if 'ruta_negocio' in globals() else "base_lotes.xlsx"
                                    nuevo_reg_lote = pd.DataFrame([{
                                        "Código": item["Código"],
                                        "Descripción": item["Descripción"],
                                        "Lote": item["Lote"],
                                        "CantidadDisponible": item["Cantidad"],
                                        "FechaVencimiento": item["FechaVencimiento"],
                                        "CostoUnitarioFinal": item["CostoUnitarioFinal"]
                                    }])

                                    if os.path.exists(archivo_lotes):
                                        df_lotes = pd.read_excel(archivo_lotes, dtype={'Código': str})
                                        match_l = df_lotes[(df_lotes['Código'].astype(str) == str(item["Código"])) & (df_lotes['Lote'].astype(str) == str(item["Lote"]))]
                                        if not match_l.empty:
                                            idx_l = match_l.index[0]
                                            cant_ant = float(df_lotes.at[idx_l, 'CantidadDisponible'])
                                            df_lotes.at[idx_l, 'CantidadDisponible'] = cant_ant + item["Cantidad"]
                                            df_lotes.at[idx_l, 'CostoUnitarioFinal'] = item["CostoUnitarioFinal"]
                                            df_lotes.at[idx_l, 'FechaVencimiento'] = item["FechaVencimiento"]
                                            df_lotes.to_excel(archivo_lotes, index=False)
                                        else:
                                            pd.concat([df_lotes, nuevo_reg_lote], ignore_index=True).to_excel(archivo_lotes, index=False)
                                    else:
                                        nuevo_reg_lote.to_excel(archivo_lotes, index=False)

                                match_prod_b = df_base[df_base[col_cod].astype(str) == str(item["Código"])]
                                if not match_prod_b.empty:
                                    idx_b = match_prod_b.index[0]
                                    stock_act = float(df_base.at[idx_b, col_stock]) if col_stock and not pd.isna(df_base.at[idx_b, col_stock]) else 0.0
                                    df_base.at[idx_b, col_stock] = stock_act + item["Cantidad"]
                                    df_base.to_excel(archivo_base, index=False)

                                procesados += 1

                            # AUTOMATIZACIÓN 1: REGISTRAR SIEMPRE EN REGISTRO DE GASTOS
                            archivo_gastos = os.path.join(ruta_negocio, "Registro_Gastos.xlsx") if 'ruta_negocio' in globals() else "Registro_Gastos.xlsx"
                            nuevo_gasto = pd.DataFrame([{
                                'Fecha_Hora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'Descripcion_Gasto': f"Compra Factura #{num_factura} - {prov_final}",
                                'Categoria': 'Mercadería',
                                'Metodo_Pago': condicion_pago,
                                'Documento': f"Factura {num_factura}",
                                'Monto': monto_total_factura_general
                            }])
                            if os.path.exists(archivo_gastos):
                                df_gastos_ant = pd.read_excel(archivo_gastos)
                                pd.concat([df_gastos_ant, nuevo_gasto], ignore_index=True).to_excel(archivo_gastos, index=False)
                            else:
                                nuevo_gasto.to_excel(archivo_gastos, index=False)

                            # AUTOMATIZACIÓN 2: SI ES CRÉDITO O CHEQUE, ENVIAR A CUENTAS POR PAGAR
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

                            st.session_state.carrito_factura_compras = []
                            st.success(f"✅ ¡Factura #{num_factura} procesada con éxito! Se actualizó el stock, se registró en gastos y {'se guardó en Cuentas por Pagar' if condicion_pago in ['Crédito', 'Cheque'] else 'quedó saldada al contado'}.")
                            st.rerun()

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

    # 🔄 Validar y recargar la configuración si cambia el negocio seleccionado
    if "ultimo_negocio_config" not in st.session_state or st.session_state.ultimo_negocio_config != negocio_seleccionado:
        st.session_state.ultimo_negocio_config = negocio_seleccionado
        if os.path.exists(ruta_config_json):
            try:
                with open(ruta_config_json, "r", encoding="utf-8") as f:
                    st.session_state.config_ticket = json.load(f)
            except Exception:
                st.session_state.config_ticket = {"nombre_empresa": negocio_seleccionado, "rut_empresa": "", "direccion": "", "pie_pagina": "", "formato_impresion": "80mm (Térmica Estándar)"}
        else:
            st.session_state.config_ticket = {"nombre_empresa": negocio_seleccionado, "rut_empresa": "", "direccion": "", "pie_pagina": "", "formato_impresion": "80mm (Térmica Estándar)"}

    tab1, tab2, tab3 = st.tabs(["👥 Usuarios y Cajas", "💳 Formas de Pago", "🖨️ Formato de Tickets e Impresión"])

    with tab1:
        st.markdown("### 👥 Administración de Accesos del Negocio")
        st.info(f"Actualmente configurando las cajas y usuarios para: **{negocio_seleccionado}**")
        with st.form("form_nuevo_usuario_config"):
            col_u1, col_u2, col_u3 = st.columns(3)
            with col_u1: nuevo_user = st.text_input("ID de Usuario (ej: cajero3)")
            with col_u2: nuevo_nombre = st.text_input("Nombre / Descripción (ej: Caja 03)")
            with col_u3: nueva_caja_id = st.text_input("Identificador de Caja (ej: Caja_03)")
            btn_crear_user = st.form_submit_button("💾 Registrar Terminal")
            if btn_crear_user and nuevo_user and nueva_caja_id:
                st.success(f"✅ ¡Terminal {nueva_caja_id} registrado para este negocio!")

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
            pie = st.text_input("Pie de Página", value=st.session_state.config_ticket.get("pie_pagina", ""))
           
            formatos_disponibles = ["80mm (Térmica Estándar)", "58mm (Térmica Pequeña)", "Carta / A4"]
            formato_actual = st.session_state.config_ticket.get("formato_impresion", "80mm (Térmica Estándar)")
            idx_formato = formatos_disponibles.index(formato_actual) if formato_actual in formatos_disponibles else 0
           
            formato = st.selectbox("Formato", formatos_disponibles, index=idx_formato)
            btn_guardar_config = st.form_submit_button("💾 Guardar")
           
            if btn_guardar_config:
                st.session_state.config_ticket = {
                    "nombre_empresa": empresa,
                    "rut_empresa": rut,
                    "direccion": direccion,
                    "pie_pagina": pie,
                    "formato_impresion": formato
                }
                try:
                    with open(ruta_config_json, "w", encoding="utf-8") as f:
                        json.dump(st.session_state.config_ticket, f, ensure_ascii=False, indent=4)
                    st.success("✅ Configuración guardada permanentemente.")
                except Exception as e:
                    st.error(f"❌ Error al guardar el archivo: {e}")

        st.markdown("---")
        st.markdown("### 🖼️ Logotipo de la Empresa")
        if os.path.exists(ruta_logo):
            st.image(ruta_logo, width=120, caption="Logotipo actual guardado")
    
        logo_cargado = st.file_uploader("Sube una imagen para tu logo (PNG o JPG)", type=["png", "jpg", "jpeg"], key="uploader_logo_empresa")
        if logo_cargado is not None:
            # 📂 Asegurar que la carpeta del negocio exista antes de guardar
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

# ----------------- SECCIÓN VENTAS / POS RÁPIDO -----------------
elif menu == "💰 Módulo de Ventas (POS)":
    caja_actual = param_caja if param_caja else "Caja Principal"
    mostrar_encabezado_con_home(f"Terminal de Ventas - {caja_actual}")

    tipo_documento = st.selectbox("Selecciona el documento:", ["Boleta Electrónica", "Factura Electrónica", "Guía de Despacho"])
    cliente_nombre, cliente_rut = "", ""

    # 1. Lógica de Selección de Clientes (Solo para Factura/Guía)
    if tipo_documento in ["Factura Electrónica", "Guía de Despacho"]:
        path_db = archivo_base if ('archivo_base' in globals() and archivo_base) else "base_datos.xlsx"
        try:
            df_clientes_pos = pd.read_excel(path_db, sheet_name="BD_Clientes", dtype={'RUT': str})
        except Exception:
            df_clientes_pos = pd.DataFrame(columns=["RUT", "Nombre", "Teléfono", "Correo", "Dirección"])

        if not df_clientes_pos.empty and "Nombre" in df_clientes_pos.columns:
            df_clientes_pos["etiqueta"] = df_clientes_pos["Nombre"] + " (" + df_clientes_pos["RUT"].astype(str) + ")"
            lista_clientes = df_clientes_pos["etiqueta"].tolist()
            cliente_elegido = st.selectbox("👤 Selecciona un cliente registrado:", lista_clientes)
          
            if cliente_elegido and " (" in cliente_elegido:
                cliente_nombre = cliente_elegido.split(" (")[0]
                cliente_rut = cliente_elegido.split(" (")[1].replace(")", "")
        else:
            st.warning("⚠️ No hay clientes registrados.")
            col_f1, col_f2 = st.columns(2)
            with col_f1: cliente_nombre = st.text_input("Razón Social / Nombre del Cliente")
            with col_f2: cliente_rut = st.text_input("RUT / Identificación Tributaria")

    # 2. Visualización de Resultado de Venta (Transacción Completada)
    if st.session_state.ultimo_recibo is not None:
        st.success("🎉 ¡Transacción completada!")
        st.markdown(f'<div class="ticket-box">{st.session_state.ultimo_recibo}</div>', unsafe_allow_html=True)
      
        # Guardar respaldo del carrito al completar la venta si no existe
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

    # 3. Flujo de Formas de Pago
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
                        st.warning("⚠️ Monto insuficiente.")
                    else:
                        fecha_hora_actual = datetime.now()
                        registros_nuevos, lineas_productos = [], ""
                        for item in st.session_state.carrito_ventas:
                            lineas_productos += f"- {item['Descripción']} (x{int(item['Cantidad'])}) ... ${item['Subtotal']:,.2f}\n"
                            registros_nuevos.append({
                                "TransaccionID": f"TX_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                                "FechaHora": fecha_hora_actual.strftime("%Y-%m-%d %H:%M:%S"),
                                "Caja": caja_actual, "Documento": tipo_documento,
                                "Cliente": cliente_nombre if cliente_nombre else "Cliente General",
                                "RUT": cliente_rut if cliente_rut else "Sin RUT",
                                "Código": item["Código"], "Descripción": item["Descripción"],
                                "Cantidad": item["Cantidad"], "PrecioUnitario": item["Precio Unitario"],
                                "Subtotal": item["Subtotal"], "FormaPago": forma_pago,
                                "TotalBoleta": total_venta
                            })
                   
                        archivo_mensual = os.path.join(ruta_negocio, f"Libro_Ventas_{fecha_hora_actual.strftime('%Y_%m')}.xlsx")
                        df_nuevo = pd.DataFrame(registros_nuevos)
                        if os.path.exists(archivo_mensual):
                            pd.concat([pd.read_excel(archivo_mensual), df_nuevo], ignore_index=True).to_excel(archivo_mensual, index=False)
                        else:
                            df_nuevo.to_excel(archivo_mensual, index=False)

                        # Registro en Cuentas por Cobrar si aplica
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

                        cfg = st.session_state.get('config_ticket', {'nombre_empresa': 'MI EMPRESA', 'rut_empresa': '00.000.000-0', 'direccion': 'Santiago', 'pie_pagina': 'Gracias por su preferencia'})
                       
                        st.session_state.items_recibo_actual = st.session_state.carrito_ventas.copy()
                        st.session_state.ultimo_recibo = f"""
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
                        st.session_state.estado_pago = False
                        st.rerun()

        else:
            st.warning("⚠️ Carrito vacío.")
            if st.button("Volver"):
                st.session_state.estado_pago = False
                st.rerun()

    # 4. Pantalla Principal del POS (Selección y Carrito)
    else:
        if df_base is not None:
            col_cod = next((c for c in df_base.columns if 'código' in str(c).lower() or 'codigo' in str(c).lower() or 'ean' in str(c).lower()), df_base.columns[0])
            col_desc = next((c for c in df_base.columns if 'descripción' in str(c).lower() or 'nombre' in str(c).lower() or 'producto' in str(c).lower()), df_base.columns[1])
            col_precio = "Precio de Venta" if "Precio de Venta" in df_base.columns else df_base.columns[5]

            metodo_lectura = st.radio("Método de entrada de código:", ["⌨️ Digitar / Lector Físico", "📷 Usar Cámara del Celular"], horizontal=True, key="radio_metodo_pos")

            codigo_escan_pos = ""

            if metodo_lectura == "📷 Usar Cámara del Celular":
                st.markdown("Apunta la cámara al código de barras y captura la foto:")
                foto_capturada = st.camera_input("Capturar código de barras", key="cam_pos")
                if foto_capturada is not None:
                    st.success("✔️ ¡Foto capturada con éxito!")
            else:
                codigo_escan_pos = st.text_input("📷 Digita el código o usa tu pistola láser:", key="input_escan_pos")

            opciones_productos = ["-- Selecciona o busca un producto --"] + [f"{row[col_cod]} - {row[col_desc]}" for idx, row in df_base.iterrows()]
            prod_sugerido_pos_idx = 0
       
            if codigo_escan_pos:
                match_pos = df_base[df_base[col_cod].astype(str) == str(codigo_escan_pos)]
                if not match_pos.empty:
                    match_str_pos = f"{match_pos.iloc[0][col_cod]} - {match_pos.iloc[0][col_desc]}"
                    if match_str_pos in opciones_productos:
                        prod_sugerido_pos_idx = opciones_productos.index(match_str_pos)
                        st.success(f"✔️ Producto detectado: {match_str_pos}")
                    
                        st.session_state.precio_actual_input = float(match_pos.iloc[0][col_precio])
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
                    match_row = df_base[df_base[col_cod].astype(str) == str(c_buscado)]
                    if not match_row.empty:
                        st.session_state.precio_actual_input = float(match_row.iloc[0][col_precio])
                else:
                    st.session_state.precio_actual_input = 0.0

            with st.form("form_agregar_item"):
                col_cant, col_precio_input = st.columns(2)
                with col_cant:
                    cantidad_vendida = st.number_input("Cantidad", min_value=0.01, step=0.1, value=1.0, format="%.2f")
                with col_precio_input:
                    precio_venta = st.number_input("Precio Unitario ($)", min_value=0.0, step=1.0, value=float(st.session_state.precio_actual_input))

                btn_agregar = st.form_submit_button("➕ Agregar al Carrito de Venta")

                if btn_agregar:
                    if producto_seleccionado == "-- Selecciona o busca un producto --":
                        st.warning("⚠️ Selecciona un producto válido.")
                    else:
                        st.session_state.carrito_ventas.append({
                            "Código": producto_seleccionado.split(" - ")[0],
                            "Descripción": producto_seleccionado.split(" - ")[1],
                            "Cantidad": float(cantidad_vendida),
                            "Precio Unitario": float(precio_venta),
                            "Subtotal": float(cantidad_vendida) * float(precio_venta)
                        })
                        st.rerun()

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



