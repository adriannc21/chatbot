import json

INPUT_FILE = "productos.json"   # archivo resultante de la vectorización
OUTPUT_FILE = "productos_stock.json"       # archivo filtrado

def filtrar_instock():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        productos = json.load(f)

    # Filtrar solo los que tengan Stock Status = instock
    instock = [p for p in productos if p.get("Stock Status") == "instock"]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f_out:
        json.dump(instock, f_out, indent=2, ensure_ascii=False)

    print(f"Productos filtrados: {len(instock)} guardados en {OUTPUT_FILE}")

if __name__ == "__main__":
    filtrar_instock()
