import json
import os
from openai import OpenAI
from dotenv import load_dotenv
import time

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

INPUT_FILE = "productos_optimizados.json"
OUTPUT_FILE = "productos_vectorizados.json"

def crear_embedding(texto):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texto
    )
    return response.data[0].embedding

def vectorizar_productos():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        productos = json.load(f)

    vectorizados = []
    for i, producto in enumerate(productos):
        categorias_texto = " ".join(
            cat.get("Categoría", "") + " " + cat.get("Subcategoría", "")
            for cat in producto.get("Categorías del producto", [])
        )

        contenido = producto.get("Content", "")
        contenido_corto = contenido[:500]  # Truncar para evitar error 400

        texto_para_embedding = " ".join([
            producto.get("Title", ""),
            contenido_corto,
            producto.get("Marcas", ""),
            categorias_texto
        ]).strip()

        embedding = crear_embedding(texto_para_embedding)

        producto_con_embedding = producto.copy()
        producto_con_embedding["embedding"] = embedding

        vectorizados.append(producto_con_embedding)

        if (i+1) % 50 == 0:
            print(f"Vectorizados {i+1} productos...")

        time.sleep(0.3)  # Ajusta si te da error rate limit

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f_out:
        json.dump(vectorizados, f_out, indent=2, ensure_ascii=False)

    print(f"Vectorización completa: {len(vectorizados)} productos guardados en {OUTPUT_FILE}")

if __name__ == "__main__":
    vectorizar_productos()
