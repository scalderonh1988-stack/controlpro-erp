import pandas as pd
import openpyxl
import os

print("🔍 Analizando inventario para detectar stock crítico...")

archivo_base = "BASE DE DATOS.xlsx"
archivo_reporte = "Reporte_Stock_Critico.xlsx"

if not os.path.exists(archivo_base):
    print(f"❌ Error crítico: No se encuentra el archivo maestro '{archivo_base}'.")
else:
    # 1. Leemos la base de datos asegurando formato de texto en los códigos
    df_base = pd.read_excel(archivo_base, dtype={'Código': str})

    # Buscamos de manera inteligente si existe alguna columna de stock o disponibilidad
    posibles_columnas = [col for col in df_base.columns if 'stock' in col.lower() or 'dispo' in col.lower() or 'cantidad' in col.lower()]

    if not posibles_columnas:
        print("⚠️ No se encontró columna de stock. Creando columna 'Stock' por defecto...")
        df_base['Stock'] = 10 # Valor base de prueba
        columna_stock = 'Stock'
    else:
        columna_stock = posibles_columnas[0]
        print(f"📊 Columna de inventario detectada: '{columna_stock}'")

    # Definimos nuestro límite de mínimo crítico (por ejemplo, 5 unidades o menos)
    LIMITE_CRITICO = 5

    # Limpiamos y convertimos a número de forma segura
    df_base[columna_stock] = pd.to_numeric(df_base[columna_stock], errors='coerce').fillna(0)

    # 2. Filtramos los productos en estado crítico
    df_critico = df_base[df_base[columna_stock] <= LIMITE_CRITICO].copy()

    print(f"📊 Total de productos analizados: {len(df_base)}")
    print(f"⚠️ Productos en estado crítico (Stock <= {LIMITE_CRITICO}): {len(df_critico)}")

    if len(df_critico) > 0:
        # 3. Guardamos el reporte prolijo usando openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "StockCritico"

        headers = list(df_critico.columns)
        ws.append(headers)

        for _, row in df_critico.iterrows():
            fila_valores = [str(row[col]) if col == 'Código' else row[col] for col in headers]
            ws.append(fila_valores)

        # Forzamos formato de texto oficial '@' en la columna A (Códigos)
        for cell in ws['A']:
            if cell.row > 1:
                cell.number_format = '@'
                cell.data_type = 's'

        wb.save(archivo_reporte)
        print(f"✅ ¡Reporte generado con éxito!")
        print(f"📁 Archivo guardado como: '{archivo_reporte}'.")
    else:
        print("🎉 ¡Excelente noticia! No hay productos en stock crítico.")