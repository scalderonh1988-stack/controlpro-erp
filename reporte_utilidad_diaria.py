import os
from datetime import datetime
import openpyxl
from supabase import create_client, Client

# --- CONFIGURACIÓN DE LA NUBE (SUPABASE) ---
SUPABASE_URL = "https://dmkjlcjrobszhwasrofc.supabase.co"
SUPABASE_KEY = "sb_publishable_uGVmMWz7T9aShxTMm_Vrgw_QFvRyTmH"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("📊 Generando el Reporte de Utilidad Diaria y Control de Retiros desde la Nube...")

# --- CONTROL DE SEGURIDAD ---
RUT_NEGOCIO = input("🔑 Ingresa el RUT de este local (ej: 12345678-9) para generar el reporte: ").strip()

if not RUT_NEGOCIO:
    print("❌ Error: Debes ingresar un RUT válido.")
    exit()

archivo_reporte = f"Reporte_Utilidad_Diaria_{RUT_NEGOCIO}.xlsx"

# 1. Obtenemos la fecha de hoy para filtrar
fecha_hoy = datetime.now().strftime('%Y-%m-%d')
print(f"⏳ Descargando ventas de hoy ({fecha_hoy})...")

try:
    # 2. Traemos las ventas del día desde Supabase
    res_ventas = supabase.table("ventas") \
        .select("*") \
        .eq("rut_empresa", RUT_NEGOCIO) \
        .like("fecha", f"{fecha_hoy}%") \
        .execute()
    ventas_hoy = res_ventas.data

    if not ventas_hoy:
        print("ℹ️ No se registraron ventas en la nube para el día de hoy.")
        exit()

    print(f"✅ Se encontraron {len(ventas_hoy)} transacciones hoy. Cruzando con costos del inventario...")

    # 3. Traemos el catálogo de productos para conocer los costos
    res_productos = supabase.table("productos") \
        .select("codigo, descripcion, costo, precio_venta") \
        .eq("rut_empresa", RUT_NEGOCIO) \
        .execute()
    
    # Armamos un "diccionario" en la memoria para buscar súper rápido por descripción
    catalogo = {p['descripcion']: p for p in res_productos.data if p['descripcion']}

    IVA = 0.19
    resumen_diario = []
    total_recaudado = 0.0
    total_utilidad_dia = 0.0

    # 4. Procesamos cada venta cruzándola con los costos
    for venta in ventas_hoy:
        detalle = venta.get('detalle', '')
        
        # Extraemos la descripción y la cantidad del texto que guardó la caja
        descripcion_venta = detalle
        cantidad = 1.0
        if "(Cant: " in detalle:
            partes = detalle.split(" (Cant: ")
            descripcion_venta = partes[0].strip()
            try:
                cantidad = float(partes[1].replace(")", "").strip())
            except ValueError:
                cantidad = 1.0

        # Buscamos los valores originales del producto en el catálogo
        producto = catalogo.get(descripcion_venta)
        
        if producto:
            cod = producto.get('codigo', 'Sin Código')
            c_bruto = float(producto.get('costo') or 0.0)
            p_bruto = float(producto.get('precio_venta') or 0.0)
            
            # Desglose neto (sin IVA 19%)
            p_neto = p_bruto / (1 + IVA)
            c_neto = c_bruto / (1 + IVA)

            # Totales diarios para esta línea de venta
            total_venta_bruta = p_bruto * cantidad
            total_costo_neto = c_neto * cantidad
            utilidad_neta_total = (p_neto - c_neto) * cantidad

            total_recaudado += total_venta_bruta
            total_utilidad_dia += utilidad_neta_total

            resumen_diario.append([
                venta.get('fecha'),
                cod,
                descripcion_venta,
                cantidad,
                round(total_venta_bruta, 2),
                round(total_costo_neto, 2),
                round(utilidad_neta_total, 2)
            ])
        else:
            # Si el producto se vendió pero luego fue borrado del catálogo
            resumen_diario.append([
                venta.get('fecha'),
                "N/A",
                descripcion_venta,
                cantidad,
                venta.get('monto'),
                0,
                0
            ])

    # 5. Generamos el archivo Excel (manteniendo tu formato original)
    if resumen_diario:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "UtilidadDiaria"

        headers = ['Fecha', 'Código', 'Descripción', 'Cantidad_Vendida', 'Venta_Total_Bruta', 'Costo_Neto_Total', 'Utilidad_Neta_Generada']
        ws.append(headers)

        for fila in resumen_diario:
            ws.append(fila)

        # Fila final con totales
        ws.append([])
        ws.append(["--- RESUMEN FINANCIERO DIARIO ---"])
        ws.append(["Total Caja Bruta Recaudada:", round(total_recaudado, 2)])
        ws.append(["Utilidad Neta Real del Día (Ganancia Pura):", round(total_utilidad_dia, 2)])

        # Blindamos la columna B con formato de texto '@' para los códigos de barras
        for row in ws.iter_rows(min_row=2):
            if row[1].value and not str(row[1].value).startswith('---'):
                row[1].number_format = '@'

        wb.save(archivo_reporte)
        print(f"\n✅ ¡Reporte de utilidad diaria generado con éxito desde la Nube!")
        print(f"📁 Archivo Excel guardado como: '{archivo_reporte}'.")
        print("---------------------------------------------------")
        print(f"💵 Venta Bruta Total en Caja: ${total_recaudado:,.2f}")
        print(f"💰 Utilidad Neta Real (Ganancia pura): ${total_utilidad_dia:,.2f}")
        print("---------------------------------------------------")

except Exception as e:
    print(f"❌ Ocurrió un error al conectar con Supabase o generar el reporte: {e}")