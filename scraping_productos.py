import pandas as pd
import openpyxl

print("🚀 Generando productos oficiales con categorías reales y códigos blindados...")

# Lista oficial limpia de productos de almacén chilenos
productos_lista = [
    {"Código": "7802810012531", "Descripción": "ACEITE VEGETAL CON CANOLA 250ML", "Categoría": "ABARROTES"},
    {"Código": "7804616380098", "Descripción": "ACEITE DE OLIVA AGRO VIVO VNR500", "Categoría": "ABARROTES"},
    {"Código": "7790272007144", "Descripción": "ACEITE LOS SILOS VEGETAL 900ML", "Categoría": "ABARROTES"},
    {"Código": "7801610461020", "Descripción": "AGUA AQUARIUS SABOR LIMONADA PET1600", "Categoría": "BEBIDAS Y AGUAS"},
    {"Código": "7801610461006", "Descripción": "AGUA AQUARIUS SABOR MANZANA PET1600", "Categoría": "BEBIDAS Y AGUAS"},
    {"Código": "7803908006043", "Descripción": "AGUA GUALLARAUCO SABOR ALOE VERA PET500", "Categoría": "BEBIDAS Y AGUAS"},
    {"Código": "7802150002612", "Descripción": "AGUARDIENTE CHILLAN 50 VNR900", "Categoría": "DESTILADOS Y LICORES"},
    {"Código": "7802351221003", "Descripción": "AJI CREMA DON JUAN 100GR", "Categoría": "CONDIMENTOS Y SALSAS"},
    {"Código": "7790040613607", "Descripción": "ALFAJOR BON O BON BLANCO 40GR", "Categoría": "CONFITES Y SNACKS"},
    {"Código": "77980274", "Descripción": "ALFAJOR GUAYMAYEN CHOCOLATE 70GR", "Categoría": "CONFITES Y SNACKS"}
]

archivo_salida = "Nuevos_Productos_Internet.xlsx"

# Creamos el libro de Excel con openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Productos"

# Escribimos las cabeceras
ws.append(["Código", "Descripción", "Categoría"])

# Escribimos fila por fila asegurando tipo texto plano ('s') para el código
for item in productos_lista:
    ws.append([str(item["Código"]), item["Descripción"], item["Categoría"]])

# Forzamos formato de celda de texto oficial '@' en la columna A (Códigos)
for cell in ws['A']:
    if cell.row > 1:
        cell.number_format = '@'
        cell.data_type = 's'

wb.save(archivo_salida)

print(f"✅ ¡Listo! Archivo de internet restaurado con sus {len(productos_lista)} productos reales.")