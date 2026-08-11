import pandas as pd
import openpyxl
import os
from datetime import datetime

print("🛒 Iniciando Terminal de Caja y Ventas con Escáner...")

archivo_base = "BASE DE DATOS.xlsx"
archivo_ventas_diarias = "Ventas_Diarias.xlsx"

if not os.path.exists(archivo_base):
    print(f"❌ Error crítico: No se encuentra el archivo maestro '{archivo_base}'.")
else:
    # 1. Cargamos el libro maestro con openpyxl para proteger formato y códigos
    wb = openpyxl.load_workbook(archivo_base)
    ws = wb.active

    # 2. Leemos la base con pandas para buscar productos velozmente
    df_base = pd.read_excel(archivo_base, dtype={'Código': str})
    headers = [cell.value for cell in ws[1]]

    # Identificamos columnas clave
    col_stock = next((col for col in df_base.columns if 'stock' in col.lower() or 'dispo' in col.lower() or 'cantidad' in col.lower()), None)
    col_precio = next((col for col in df_base.columns if 'precio' in col.lower() or 'venta' in col.lower()), None)

    if not col_stock or not col_precio:
        print("⚠️ No se encontró la columna de Stock o Precio en la base maestra.")
    else:
        idx_stock_ws = headers.index(col_stock) + 1
        
        print("\n---------------------------------------------------------")
        print("🟢 CAJA ABIERTA Y LISTA PARA ESCANEAR PRODUCTOS")
        print("---------------------------------------------------------")
        print("Instrucciones: Ingresa el código de barras del producto (o escribe 'salir' para cerrar caja).")

        carrito = []

        while True:
            codigo_ingresado = input("\nScan Código / Escribir Código: ").strip()

            if codigo_ingresado.lower() == 'salir':
                break

            if not codigo_ingresado:
                continue

            # Buscamos el producto en el DataFrame
            match = df_base[df_base['Código'].astype(str).str.strip() == codigo_ingresado]

            if match.empty:
                print(f"❌ Producto con código '{codigo_ingresado}' no encontrado en la base de datos.")
            else:
                row_index_df = match.index[0]
                descripcion = match['Descripción'].values[0] if 'Descripción' in match.columns else "Sin descripción"
                precio_venta = float(match[col_precio].values[0]) if pd.notna(match[col_precio].values[0]) else 0
                stock_actual = float(match[col_stock].values[0]) if pd.notna(match[col_stock].values[0]) else 0

                print(f"📦 Producto: {descripcion}")
                print(f"💵 Precio Unitario: ${precio_venta:,.2f} | Stock Disponible: {stock_actual}")

                if stock_actual <= 0:
                    print("⚠️ ¡ALERTA! Producto sin stock disponible para la venta.")
                    continuar = input("¿Desea vender de todas formas? (s/n): ").strip().lower()
                    if continuar != 's':
                        continue

                try:
                    cantidad_comprada = float(input("Cantidad a vender (por defecto 1): ") or "1")
                except ValueError:
                    cantidad_comprada = 1

                # Actualizamos el stock en la memoria de pandas y en la hoja openpyxl
                nuevo_stock = stock_actual - cantidad_comprada
                df_base.loc[row_index_df, col_stock] = nuevo_stock

                # Buscamos la fila exacta en la hoja de Excel para actualizarla visualmente
                row_ws_idx = row_index_df + 2 # +2 por el encabezado y base 1 de Excel
                ws.cell(row=row_ws_idx, column=idx_stock_ws, value=nuevo_stock)

                total_linea = precio_venta * cantidad_comprada
                carrito.append({
                    'Fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'Código': codigo_ingresado,
                    'Cantidad_Vendida': cantidad_comprada,
                    'Total_Venta': total_linea
                })

                print(f"✅ Agregado al ticket. Subtotal línea: ${total_linea:,.2f} | Nuevo Stock: {nuevo_stock}")

        # Al cerrar caja, guardamos los cambios en el maestro y registramos las ventas del día
        if carrito:
            # Blindamos estrictamente la columna A (Códigos) con formato de texto '@'
            for cell in ws['A']:
                if cell.row > 1:
                    cell.number_format = '@'
                    cell.data_type = 's'

            wb.save(archivo_base)

            # Guardamos o acumulamos en el archivo de ventas diarias
            df_nuevas_ventas = pd.DataFrame(carrito)
            if os.path.exists(archivo_ventas_diarias):
                df_ventas_antiguas = pd.read_excel(archivo_ventas_diarias, dtype={'Código': str})
                df_ventas_final = pd.concat([df_ventas_antiguas, df_nuevas_ventas], ignore_index=True)
            else:
                df_ventas_final = df_nuevas_ventas

            df_ventas_final.to_excel(archivo_ventas_diarias, index=False)

            print("\n---------------------------------------------------------")
            print("🏁 CAJA CERRADA CON ÉXITO")
            print(f"📁 Stock actualizado en '{archivo_base}' y ventas registradas en '{archivo_ventas_diarias}'.")
            print("---------------------------------------------------------")
        else:
            print("\nℹ️ No se registraron ventas en esta sesión de caja.")