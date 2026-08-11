import pandas as pd
import openpyxl
import os
from datetime import datetime

print("📊 Iniciando Módulo de Sugerencias de Reabastecimiento (Lead Time: 72 horas)...")

archivo_base = "BASE DE DATOS.xlsx"

if not os.path.exists(archivo_base):
    print(f"❌ Error crítico: No se encuentra el archivo maestro '{archivo_base}'.")
else:
    df_base = pd.read_excel(archivo_base, dtype={'Código': str})
    
    # Identificamos columnas clave
    col_stock = next((col for col in df_base.columns if 'stock' in str(col).lower() or 'cantidad' in str(col).lower() or 'existencia' in str(col).lower()), None)
    col_desc = next((col for col in df_base.columns if 'descripción' in str(col).lower() or 'nombre' in str(col).lower()), 'Descripción')

    if not col_stock:
        print("⚠️ No se encontró la columna de Stock en la base maestra.")
    else:
        # Lead time estandarizado a 72 horas (3 días)
        dias_entrega = 3.0

        print("\n=========================================================")
        print("🛒 ASISTENTE DE SUGERENCIA DE REABASTECIMIENTO")
        print(f"⏱️ Plazo de entrega estandarizado: 72 horas ({dias_entrega} días)")
        print("=========================================================")
        print(f"{'Código':<15} | {'Descripción':<25} | {'Stock':<8} | {'Dem./Semana':<12} | {'Sugerido a Comprar':<18}")
        print("-" * 75)

        sugerencias_compra = []

        for idx, row in df_base.iterrows():
            codigo = str(row.get('Código', 'N/D'))
            desc = str(row.get(col_desc, 'Sin descripción'))[:25]
            
            try:
                stock_actual = float(row.get(col_stock, 0)) if pd.notna(row.get(col_stock)) else 0.0
            except (ValueError, TypeError):
                stock_actual = 0.0

            # Demanda semanal estimada (ejemplo base de 10 unidades semanales para prueba)
            demanda_semanal = 10.0 
            
            # Cálculo del consumo durante las 72 horas de espera del proveedor
            consumo_durante_entrega = (demanda_semanal / 7.0) * dias_entrega

            # Punto de pedido: si el stock actual no alcanza para cubrir el tiempo de entrega
            if stock_actual <= consumo_durante_entrega:
                cantidad_sugerida = round(demanda_semanal - stock_actual + consumo_durante_entrega, 2)
                if cantidad_sugerida < 0:
                    cantidad_sugerida = demanda_semanal

                print(f"{codigo:<15} | {desc:<25} | {stock_actual:<8} | {demanda_semanal:<12} | 📦 Pedir: {cantidad_sugerida}")
                
                sugerencias_compra.append({
                    'Codigo': codigo,
                    'Descripcion': desc,
                    'Stock_Actual': stock_actual,
                    'Cantidad_Sugerida': cantidad_sugerida
                })

        print("-" * 75)
        if not sugerencias_compra:
            print("✔️ Todo tu inventario soporta holgadamente las 72 horas de entrega. ¡Sin alertas de quiebre!")
        else:
            print(f"💡 Se detectaron {len(sugerencias_compra)} productos en riesgo que requieren pedido inmediato.")
        print("=========================================================")