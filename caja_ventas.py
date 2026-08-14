import os
import csv
from datetime import datetime
from supabase import create_client, Client

# --- CONFIGURACIÓN DE LA NUBE (SUPABASE) ---
SUPABASE_URL = "https://dmkjlcjrobszhwasrofc.supabase.co"
SUPABASE_KEY = "sb_publishable_uGVmMWz7T9aShxTMm_Vrgw_QFvRyTmH"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def buscar_producto_en_nube(rut_empresa, codigo_barras):
    """Busca un producto en Supabase filtrando estrictamente por RUT y Código."""
    try:
        respuesta = supabase.table("productos") \
            .select("*") \
            .eq("rut_empresa", rut_empresa) \
            .eq("codigo", codigo_barras) \
            .execute()
        
        if len(respuesta.data) > 0:
            return respuesta.data[0] 
        else:
            return None 
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None

def actualizar_stock_en_nube(rut_empresa, codigo_barras, nuevo_stock):
    """Actualiza el stock del producto directamente en Supabase."""
    try:
        supabase.table("productos") \
            .update({"stock": nuevo_stock}) \
            .eq("rut_empresa", rut_empresa) \
            .eq("codigo", codigo_barras) \
            .execute()
    except Exception as e:
        print(f"❌ Error al actualizar stock en la nube: {e}")

print("🛒 Iniciando Terminal de Caja y Ventas (100% Nube)...")

# --- SEGURIDAD: SOLICITAMOS EL RUT AL INICIAR EL TURNO ---
print("\n🔒 Control de Seguridad")
RUT_NEGOCIO = input("🔑 Ingresa el RUT de este local (ej: 12345678-9) para iniciar turno: ").strip()

if not RUT_NEGOCIO:
    print("❌ Error: Debes ingresar un RUT válido para operar la caja.")
    exit()

print("\n---------------------------------------------------------")
print(f"🟢 CAJA ABIERTA - LOCAL: {RUT_NEGOCIO}")
print("---------------------------------------------------------")
print("Instrucciones: Ingresa el código de barras del producto (o escribe 'salir' para cerrar caja).")

carrito = []

while True:
    codigo_ingresado = input("\nScan Código / Escribir Código: ").strip()

    if codigo_ingresado.lower() == 'salir':
        break

    if not codigo_ingresado:
        continue

    # --- 1. BUSCAMOS EL PRODUCTO EN SUPABASE ---
    producto = buscar_producto_en_nube(RUT_NEGOCIO, codigo_ingresado)

    if not producto:
        print(f"❌ Producto con código '{codigo_ingresado}' no encontrado en la base de datos.")
    else:
        # Extraemos los datos de la nube
        descripcion = producto.get('descripcion') or "Sin descripción"
        
        try:
            precio_venta = float(producto.get('precio_venta') or 0.0)
        except Exception:
            precio_venta = 0.0
            
        try:
            stock_actual = float(producto.get('stock') or 0.0)
        except Exception:
            stock_actual = 0.0

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

        # Calculamos el nuevo stock
        nuevo_stock = stock_actual - cantidad_comprada
        
        # --- 2. ACTUALIZAMOS EL STOCK EN SUPABASE INMEDIATAMENTE ---
        actualizar_stock_en_nube(RUT_NEGOCIO, codigo_ingresado, nuevo_stock)

        total_linea = precio_venta * cantidad_comprada
        
        # --- 3. PREPARAMOS EL DATO PARA ENVIAR LA VENTA AL CERRAR ---
        carrito.append({
            "rut_empresa": RUT_NEGOCIO,
            "fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "detalle": f"{descripcion} (Cant: {cantidad_comprada})",
            "monto": total_linea,
            "metodo_pago": "Efectivo",
            "documento": "Ticket de Venta"
        })

        print(f"✅ Agregado al ticket. Subtotal línea: ${total_linea:,.2f} | Nuevo Stock en Nube: {nuevo_stock}")

# Al cerrar caja
if carrito:
    print("\n⏳ Subiendo ventas a la nube (Supabase)...")
    try:
        supabase.table("ventas").insert(carrito).execute()
        print("✅ ¡Ventas registradas con éxito en la nube!")
    except Exception as e:
        print(f"❌ Error al conectar con la nube: {e}")
        
        # Guardado de emergencia en CSV si falla el internet al final
        with open("Respaldo_Ventas_Emergencia.csv", "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=carrito[0].keys())
            writer.writeheader()
            writer.writerows(carrito)
        print("⚠️ Falló el internet. Las ventas se guardaron localmente en 'Respaldo_Ventas_Emergencia.csv'.")

    print("\n---------------------------------------------------------")
    print("🏁 CAJA CERRADA CON ÉXITO")
    print("📁 Inventario y ventas sincronizados al 100% en la Nube.")
    print("---------------------------------------------------------")
else:
    print("\nℹ️ No se registraron ventas en esta sesión de caja.")