import pandas as pd
import openpyxl
import os
from datetime import datetime

print("📊 Generando el Reporte de Utilidad Diaria y Control de Retiros...")

archivo_base = "BASE DE DATOS.xlsx"
archivo_ventas_dia = "Ventas_Diarias.xlsx"
archivo_reporte = "Reporte_Utilidad_Diaria.xlsx"

if not os.path.exists(archivo_base):
    print(f"❌ Error crítico: No se encuentra el archivo maestro '{archivo_base}'.")
else:
    # Si aún no existe un archivo de ventas diarias de prueba, lo creamos automáticamente
    if not os.path.exists(archivo_ventas_dia):
        print(f"⚠️ No se encontró '{archivo_ventas_dia}'. Creando plantilla de ventas diarias de ejemplo...")
        df_ejemplo = pd.DataFrame({
            'Fecha': [datetime.now().strftime('%Y-%m-%d')],
            'Código': ['7802810012531'],
            'Cantidad_Vendida': [5]
        })
        df_ejemplo.to_excel(archivo_ventas_dia, index=False)
        print(f"📁 Plantilla creada: {archivo_ventas_dia}. Puedes registrar tus ventas diarias aquí.")

    # 1. Leemos la base de datos maestra y las ventas del día
    df_base = pd.read_excel(archivo_base, dtype={'Código': str})
    df_ventas = pd.read_excel(archivo_ventas_dia, dtype={'Código': str})

    # Identificamos columnas clave
    col_costo = next((col for col in df_base.columns if 'costo' in col.lower()), None)
    col_precio = next((col for col in df_base.columns if 'precio' in col.lower() or 'venta' in col.lower()), None)

    if not col_costo or not col_precio:
        print("⚠️ Faltan columnas de Costo o Precio de Venta en la base maestra.")
    else:
        # Limpiamos y convertimos a valores numéricos
        df_base[col_costo] = pd.to_numeric(df_base[col_costo], errors='coerce').fillna(0)
        df_base[col_precio] = pd.to_numeric(df_base[col_precio], errors='coerce').fillna(0)

        IVA = 0.19
        resumen_diario = []

        # 2. Procesamos las ventas cruzándolas con los costos y precios netos
        for _, row_v in df_ventas.iterrows():
            cod = str(row_v['Código']).strip()
            cantidad = float(row_v['Cantidad_Vendida']) if pd.notna(row_v.get('Cantidad_Vendida')) else 0
            fecha_venta = row_v['Fecha'] if 'Fecha' in df_ventas.columns else datetime.now().strftime('%Y-%m-%d')

            match = df_base[df_base['Código'].astype(str).str.strip() == cod]

            if not match.empty:
                desc = match['Descripción'].values[0] if 'Descripción' in match.columns else "Sin descripción"
                p_bruto = match[col_precio].values[0]
                c_bruto = match[col_costo].values[0]

                # Desglose neto (sin IVA 19%)
                p_neto = p_bruto / (1 + IVA)
                c_neto = c_bruto / (1 + IVA)

                # Totales diarios para esta línea de venta
                total_venta_bruta = p_bruto * cantidad
                total_costo_neto = c_neto * cantidad
                total_venta_neta = p_neto * cantidad
                
                # Utilidad bruta y neta del día por producto
                utilidad_neta_total = (p_neto - c_neto) * cantidad

                resumen_diario.append({
                    'Fecha': fecha_venta,
                    'Código': cod,
                    'Descripción': desc,
                    'Cantidad_Vendida': cantidad,
                    'Venta_Total_Bruta': round(total_venta_bruta, 2),
                    'Costo_Neto_Total': round(total_costo_neto, 2),
                    'Utilidad_Neta_Generada': round(utilidad_neta_total, 2)
                })

        if resumen_diario:
            df_resumen = pd.DataFrame(resumen_diario)

            # Totales generales del día
            total_recaudado = df_resumen['Venta_Total_Bruta'].sum()
            total_utilidad_dia = df_resumen['Utilidad_Neta_Generada'].sum()

            # 3. Guardamos el reporte prolijo usando openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "UtilidadDiaria"

            headers = list(df_resumen.columns)
            ws.append(headers)

            for _, row in df_resumen.iterrows():
                fila_valores = [str(row[col]) if col == 'Código' else row[col] for col in headers]
                ws.append(fila_valores)

            # Agregamos una fila final con los totales clave para el negocio
            ws.append([])
            ws.append(["--- RESUMEN FINANCIERO DIARIO ---"])
            ws.append(["Total Caja Bruta Recaudada:", total_recaudado])
            ws.append(["Utilidad Neta Real del Día (Ganancia Pura):", total_utilidad_dia])

            # Blindamos la columna A con formato de texto '@'
            for cell in ws['A']:
                if cell.row > 1 and cell.value and not cell.value.startswith('---') and not cell.value.startswith('Total'):
                    cell.number_format = '@'
                    cell.data_type = 's'

            wb.save(archivo_reporte)
            print(f"✅ ¡Reporte de utilidad diaria generado con éxito!")
            print(f"📁 Archivo guardado como: '{archivo_reporte}'.")
            print("\n---------------------------------------------------")
            print(f"💵 Venta Bruta Total en Caja: ${total_recaudado:,.2f}")
            print(f"💰 Utilidad Neta Real (Ganancia para retiro seguro): ${total_utilidad_dia:,.2f}")
            print("---------------------------------------------------")
        else:
            print("ℹ️ No se encontraron coincidencias de productos vendidos.")