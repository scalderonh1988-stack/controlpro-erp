import pandas as pd

print("🚀 Iniciando el proceso de automatización...")

# 1. CARGAR EL ARCHIVO: Python lee el Excel por nosotros
archivo_entrada = 'BASE DE DATOS.xlsx'
df = pd.read_excel(archivo_entrada)

print(f"✅ Archivo cargado con éxito. Total de productos: {len(df)}")

# 2. AUTOMATIZACIÓN: Convertir todas las descripciones a Mayúsculas
df['Descripción'] = df['Descripción'].str.upper()

# 3. FILTRAR: Buscar solo los productos de la categoría 'ABARROTES'
abarrotes_df = df[df['Categoría'] == 'ABARROTES']
print(f"📦 Se encontraron {len(abarrotes_df)} productos en la categoría ABARROTES.")

# 4. GUARDAR EL RESULTADO: Crear un nuevo Excel limpio
archivo_salida = 'Reporte_Automatizado_Abarrotes.xlsx'
abarrotes_df.to_excel(archivo_salida, index=False)

print(f"🎉 ¡Listo! Archivo generado y guardado como: {archivo_salida}")