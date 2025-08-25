import json
import os
from openai import OpenAI
from dotenv import load_dotenv
import time

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

INPUT_FILE = "productos_stock.json"
OUTPUT_FILE = "productos_vectorizadosT1.json"

def crear_embedding(texto):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texto
    )
    return response.data[0].embedding

def parse_categorias(cat_string):
    categorias = []
    for item in cat_string.split("|"):
        if ">" in item:
            padre, sub = item.split(">", 1)
            categorias.append({"Categoría": padre.strip(), "Subcategoría": sub.strip()})
    return categorias

def vectorizar_productos():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        productos = json.load(f)

    vectorizados = []
    for i, producto in enumerate(productos):
        # Procesar categorías
        categorias_texto = " ".join(
            f"{c['Categoría']} {c['Subcategoría']}" 
            for c in parse_categorias(producto.get("Categorías del producto", ""))
        )

        # Tomar solo el primer enlace de Image URL
        imagen = producto.get("Image URL", "").split("|")[0]

        # Contenido y texto para embedding
        contenido = producto.get("Content", "")
        contenido_corto = contenido[:500]  # Truncar si es muy largo

        texto_para_embedding = " ".join([
            producto.get("Title", ""),
            contenido_corto,
            producto.get("Marcas", ""),
            categorias_texto
        ]).strip()

        embedding = crear_embedding(texto_para_embedding)

        producto_con_embedding = producto.copy()
        producto_con_embedding["embedding"] = embedding
        producto_con_embedding["Categorías del producto"] = parse_categorias(producto.get("Categorías del producto", ""))
        producto_con_embedding["Image URL"] = imagen

        vectorizados.append(producto_con_embedding)

        if (i + 1) % 50 == 0:
            print(f"Vectorizados {i+1} productos...")

        time.sleep(0.3)  # Evitar rate limit

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f_out:
        json.dump(vectorizados, f_out, indent=2, ensure_ascii=False)

    print(f"Vectorización completa: {len(vectorizados)} productos guardados en {OUTPUT_FILE}")


if __name__ == "__main__":
    vectorizar_productos()
