import os
import pandas as pd
import streamlit as st
from pathlib import Path
import shutil
from supabase import create_client, Client

# --- CONFIGURACIÓN DE LA NUBE (SUPABASE) ---
SUPABASE_URL = "https://dmkjlcjrobszhwasrofc.supabase.co"
SUPABASE_KEY = "sb_publishable_uGVmMWz7T9aShxTMm_Vrgw_QFvRyTmH"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Directorio raíz donde viven los datos de los tenants
BASE_TENANTS_DIR = "clientes"

def get_current_tenant() -> str:
    """
    Obtiene el identificador del negocio activo desde la sesión de Streamlit 
    de forma compatible con cualquier variable de estado que uses.
    """
    if "tenant_id" in st.session_state:
        return st.session_state.tenant_id
    if "negocio_actual" in st.session_state:
        return st.session_state.negocio_actual
    if "negocio_seleccionado" in st.session_state:
        return st.session_state.negocio_seleccionado
        
    st.session_state.tenant_id = "negocio_demo"
    return st.session_state.tenant_id

def get_tenant_path(filename: str) -> str:
    """
    Construye la ruta completa al archivo del tenant actual.
    """
    tenant_id = get_current_tenant()
    tenant_dir = os.path.join(BASE_TENANTS_DIR, tenant_id)
    os.makedirs(tenant_dir, exist_ok=True)
    return os.path.join(tenant_dir, filename)

def load_excel_data(filename: str) -> pd.DataFrame:
    """
    Función centralizada para leer archivos Excel del negocio activo.
    """
    file_path = get_tenant_path(filename)
    if os.path.exists(file_path):
        return pd.read_excel(file_path)
    return pd.DataFrame()

def save_excel_data(df: pd.DataFrame, filename: str):
    """
    Función centralizada para guardar archivos Excel en el negocio activo.
    """
    file_path = get_tenant_path(filename)
    df.to_excel(file_path, index=False)

def cargar_maestro_clientes():
    """
    Carga la lista de clientes desde Supabase filtrando de forma estricta 
    por el negocio activo, probando las columnas más comunes para evitar fugas de datos.
    """
    try:
        tenant_id = get_current_tenant()
        maestro = {}
        respuesta = None
        
        # Probamos dinámicamente los nombres de columna más comunes en Supabase
        columnas_intento = ["id_negocio", "rut_empresa", "rut_negocio", "negocio_id"]
        
        for col in columnas_intento:
            try:
                res = supabase.table("clientes").select("*").eq(col, tenant_id).execute()
                if res.data is not None:
                    respuesta = res
                    break
            except Exception:
                continue
                
        # Si ninguna columna estándar dio resultados, traemos un respaldo vacío controlado
        if not respuesta or not respuesta.data:
            return {}
        
        # Transformamos la lista de la nube al formato de diccionario {rut: datos}
        for cliente in respuesta.data:
            rut = cliente.get("rut")
            if rut:
                maestro[rut] = cliente
                
        return maestro
    except Exception as e:
        print(f"❌ Error cargando maestro de clientes desde la nube: {e}")
        return {}

def guardar_nuevo_cliente(id_negocio, datos_cliente):
    """
    Guarda un nuevo cliente directamente en Supabase asegurando que la relación 
    con el negocio quede grabada correctamente en todas las columnas de control.
    """
    # 1. Guardado en la Nube (Supabase)
    try:
        # Inyectamos el ID en los nombres de columna estándar para prevenir desincronizaciones
        datos_cliente["id_negocio"] = id_negocio
        datos_cliente["rut_empresa"] = id_negocio
        
        supabase.table("clientes").upsert(
            datos_cliente, 
            on_conflict="rut"
        ).execute()
        print(f"✅ Cliente {id_negocio} guardado/actualizado en la nube con éxito.")
    except Exception as e:
        print(f"❌ Error guardando cliente en Supabase: {e}")

    # 2. Creación de carpeta local (Respaldos o módulos aún no migrados)
    tenant_dir = Path("clientes") / id_negocio
    tenant_dir.mkdir(parents=True, exist_ok=True)

    # Copiar archivos base desde la plantilla si existe
    plantilla_dir = Path(__file__).resolve().parent / "plantilla_cliente"
    if plantilla_dir.exists():
        for archivo_plantilla in plantilla_dir.glob("*.xlsx"):
            destino = tenant_dir / archivo_plantilla.name
            shutil.copy(archivo_plantilla, destino)