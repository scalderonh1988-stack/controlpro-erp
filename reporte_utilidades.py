import pandas as pd
import openpyxl
import os

print("📊 Calculando desgloses netos, IVA, Impuestos Específicos, Markup y Margen...")

archivo_base = "BASE DE DATOS.xlsx"
archivo_reporte = "Reporte_Utilidades.xlsx"

if not os.path.exists(archivo_base):
    print(f"❌ Error crítico: No se encuentra el archivo maestro '{archivo_base}'.")
else:
    # 1. Leemos la base asegurando códigos en texto
    df_base = pd.read_excel(archivo_base, dtype={'Código': str})

    # Identificamos columnas clave de forma flexible
    col_costo = next((col for col in df_base.columns if 'costo' in col.lower()), None)
    col_precio = next((col for col in df_base.columns if 'precio' in col.lower()), None)
    col_impuesto = next((col for col in df_base.columns if 'impuesto' in col.lower() or 'ila' in col.lower()), None)

    if not col_costo or not col_precio:
        print("⚠️ No se encontraron las columnas de Costo o Precio de Venta.")
    else:
        print(f"📈 Columnas utilizadas -> Costo: '{col_costo}' | Precio: '{col_precio}'")
        if col_impuesto:
            print(f"🍷 Impuesto específico detectado en columna: '{col_impuesto}'")

        # Limpiamos y convertimos a valores numéricos
        df_base[col_costo] = pd.to_numeric(df_base[col_costo], errors='coerce').fillna(0)
        df_base[col_precio] = pd.to_numeric(df_base[col_precio], errors='coerce').fillna(0)

        # 2. Desglose Tributario Chileno (Precios Netos sin IVA 19%)
        # El precio bruto se divide por 1.19 para obtener el valor neto real
        IVA = 0.19

        def calcular_valores(row):
            p_bruto = row[col_precio]
            c_bruto = row[col_costo]
            
            # Netos base sin IVA
            p_neto = p_bruto / (1 + IVA)
            c_neto = c_bruto / (1 + IVA)

            # Si hay impuesto específico (ej. ILA), extraemos o aplicamos el porcentaje correspondiente
            tasa_ila = 0.0
            if col_impuesto and pd.notna(row[col_impuesto]):
                val_imp = str(row[col_impuesto])
                # Buscamos números dentro del texto del impuesto (ej. "31.5" de "ILA 31.5")
                import re
                numeros = re.findall(r"[-+]?\d*\.\d+|\d+", val_imp)
                if numeros:
                    tasa_ila = float(numeros[0]) / 100.0

            # Aplicamos impuesto específico al neto si corresponde
            # (El ILA suele aplicarse sobre el precio neto en bebidas alcohólicas)
            p_neto_con_ila = p_neto * (1 + tasa_ila)

            # Utilidad neta
            utilidad_neta = p_neto_con_ila - c_neto

            # Markup = (Precio Neto - Costo Neto) / Costo Neto * 100
            markup = ((p_neto_con_ila - c_neto) / c_neto * 100) if c_neto > 0 else 0

            # Margen de beneficio sobre la venta = (Utilidad Neta / Precio Neto con ILA) * 100
            margen_venta = ((utilidad_neta / p_neto_con_ila) * 100) if p_neto_con_ila > 0 else 0

            return pd.Series({
                'Costo_Neto': round(c_neto, 2),
                'Precio_Neto': round(p_neto_con_ila, 2),
                'Utilidad_Neta': round(utilidad_neta, 2),
                'Markup_%': round(markup, 2),
                'Margen_Beneficio_%': round(margen_venta, 2)
            })

        # Aplicamos la función matemática fila por fila
        df_calculos = df_base.apply(calcular_valores, axis=1)
        
        # Unimos los nuevos cálculos al dataframe principal
        df_final = pd.concat([df_base, df_calculos], axis=1)

        # Ordenamos por mayor margen de beneficio
        df_final = df_final.sort_values(by='Margen_Beneficio_%', ascending=False)

        # 3. Guardamos el reporte prolijo con openpyxl blindando los códigos
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "UtilidadesNetas"

        headers = list(df_final.columns)
        ws.append(headers)

        for _, row in df_final.iterrows():
            fila_valores = [str(row[col]) if col == 'Código' else row[col] for col in headers]
            ws.append(fila_valores)

        # Forzamos formato de texto oficial '@' en la columna A
        for cell in ws['A']:
            if cell.row > 1:
                cell.number_format = '@'
                cell.data_type = 's'

        wb.save(archivo_reporte)
        print(f"✅ ¡Reporte financiero avanzado generado con éxito!")
        print(f"📁 Archivo guardado como: '{archivo_reporte}' con desgloses de IVA, ILA, Markup y Margen.")