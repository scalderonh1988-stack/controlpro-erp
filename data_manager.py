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

BASE_TENANTS_DIR = "clientes"

def get_current_tenant() -> str:
    """Obtiene el identificador del negocio activo desde la sesión."""
    for key in ["tenant_id", "negocio_actual", "negocio_seleccionado"]:
        if key in st.session_state and st.session_state[key]:
            return str(st.session_state[key]).strip()
    return "negocio_demo"

def get_tenant_path(filename: str) -> str:
    tenant_id = get_current_tenant()
    tenant_dir = os.path.join(BASE_TENANTS_DIR, tenant_id)
    os.makedirs(tenant_dir, exist_ok=True)
    return os.path.join(tenant_dir, filename)

def load_excel_data(filename: str) -> pd.DataFrame:
    file_path = get_tenant_path(filename)
    if os.path.exists(file_path):
        return pd.read_excel(file_path)
    return pd.DataFrame()

def save_excel_data(df: pd.DataFrame, filename: str):
    file_path = get_tenant_path(filename)
    df.to_excel(file_path, index=False)

def cargar_maestro_clientes():
    """
    Carga los clientes de Supabase y aplica un FILTRADO ESTRICTO LOCAL 
    para garantizar que jamás se mezclen los datos entre empresas.
    """
    try:
        tenant_id = get_current_tenant()
        maestro = {}
        
        # Traemos los datos de la nube
        respuesta = supabase.table("clientes").select("*").execute()
        
        if not respuesta.data:
            return {}
        
        # FILTRO DE SEGURIDAD LOCAL: Revisamos cada cliente y solo guardamos 
        # los que coincidan exactamente con el tenant actual en CUALQUIER campo de control.
        # FILTRO DE SEGURIDAD LOCAL: Revisamos cada cliente y solo guardamos 
        # los que coincidan exactamente con el tenant actual en CUALQUIER campo de control.
        for cliente in respuesta.data:
            rut = cliente.get("rut")
            if not rut:
                continue
                
            # Identificamos a qué empresa pertenece este registro en la nube
            empresa_cliente = str(
                cliente.get("id_negocio") or 
                cliente.get("rut_empresa") or 
                cliente.get("rut_negocio") or 
                cliente.get("negocio_id") or ""
            ).strip()
            
            # Doble validación: Si la empresa coincide con la sesión actual, se agrega. 
            if empresa_cliente == tenant_id:
                maestro[rut] = cliente
                
        return maestro
    except Exception as e:
        print(f"❌ Error cargando maestro de clientes desde la nube: {e}")
        return {}

def guardar_nuevo_cliente(id_negocio, datos_cliente):
    try:
        # Inyectamos el ID de forma redundante para asegurar que quede grabado
        datos_cliente["id_negocio"] = id_negocio
        datos_cliente["rut_empresa"] = id_negocio
        
        supabase.table("clientes").upsert(
            datos_cliente, 
            on_conflict="rut"
        ).execute()
        print(f"✅ Cliente guardado/actualizado en la nube con éxito.")
    except Exception as e:
        print(f"❌ Error guardando cliente en Supabase: {e}")

    tenant_dir = Path("clientes") / id_negocio
    tenant_dir.mkdir(parents=True, exist_ok=True)

    plantilla_dir = Path(__file__).resolve().parent / "plantilla_cliente"
    if plantilla_dir.exists():
        for archivo_plantilla in plantilla_dir.glob("*.xlsx"):
            destino = tenant_dir / archivo_plantilla.name
            shutil.copy(archivo_plantilla, destino)