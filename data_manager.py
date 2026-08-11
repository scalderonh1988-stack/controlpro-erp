import os
import pandas as pd
import streamlit as st
import json
from pathlib import Path

# Directorio raíz donde viven los datos de los tenants
BASE_TENANTS_DIR = "clientes"

def get_current_tenant() -> str:
    """
    Obtiene el identificador del negocio activo desde la sesión de Streamlit.
    Si no hay ninguno definido, por defecto usa 'negocio_demo'.
    """
    if "tenant_id" not in st.session_state:
        st.session_state.tenant_id = "negocio_demo"
    return st.session_state.tenant_id

def get_tenant_path(filename: str) -> str:
    """
    Construye la ruta completa al archivo del tenant actual.
    Ejemplo: tenants/negocio_demo/ventas.xlsx
    """
    tenant_id = get_current_tenant()
    tenant_dir = os.path.join(BASE_TENANTS_DIR, tenant_id)
    
    # Asegurar que la carpeta del negocio exista
    os.makedirs(tenant_dir, exist_ok=True)
    
    return os.path.join(tenant_dir, filename)

def load_excel_data(filename: str) -> pd.DataFrame:
    """
    Función centralizada para leer archivos Excel del negocio activo.
    """
    file_path = get_tenant_path(filename)
    if os.path.exists(file_path):
        return pd.read_excel(file_path)
    else:
        # Retorna un DataFrame vacío o maneja el archivo nuevo según convenga
        return pd.DataFrame()

def save_excel_data(df: pd.DataFrame, filename: str):
    """
    Función centralizada para guardar archivos Excel en el negocio activo.
    """
    file_path = get_tenant_path(filename)
    df.to_excel(file_path, index=False)
    import json
from pathlib import Path

ARCH_MAESTRO = "maestro_clientes.json"

def cargar_maestro_clientes():
    """Carga la lista de todos los clientes desde el archivo maestro."""
    if Path(ARCH_MAESTRO).exists():
        with open(ARCH_MAESTRO, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}
import shutil

def guardar_nuevo_cliente(id_negocio, datos_cliente):
    """Guarda un nuevo cliente en el maestro, crea su carpeta física y copia los archivos base."""
    maestro = cargar_maestro_clientes()
    maestro[id_negocio] = datos_cliente

    with open(ARCH_MAESTRO, "w", encoding="utf-8") as f:
        json.dump(maestro, f, indent=4, ensure_ascii=False)

    # Crear la carpeta física del cliente dentro de 'clientes'
    tenant_dir = Path("clientes") / id_negocio
    tenant_dir.mkdir(parents=True, exist_ok=True)

    # Copiar archivos base desde la plantilla si existe
    plantilla_dir = Path(__file__).resolve().parent / "plantilla_cliente"
    if plantilla_dir.exists():
        for archivo_plantilla in plantilla_dir.glob("*.xlsx"):
            destino = tenant_dir / archivo_plantilla.name
            shutil.copy(archivo_plantilla, destino)