from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os, json, numpy as np, uuid, re
from openai import OpenAI
import uuid

load_dotenv()
app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
sessions = {}

# Cargar prompt base y catálogo
with open("prompt_base.txt", "r", encoding="utf-8") as f:
    PROMPT_BASE = f.read()

with open("productos_vectorizados.json", "r", encoding="utf-8") as f:
    catalog = json.load(f)

def vector_similaridad(vec1, vec2):
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

# === Detectar tipo de producto solicitado ===
def detectar_tipo_producto(query, historial):
    consulta_completa = query.lower()
    
    # Agregar contexto del historial
    if historial:
        for msg in historial[-4:]:
            if msg["role"] == "user":
                consulta_completa += " " + msg["content"].lower()
    
    # Detectar tecnología de impresora
    if any(word in consulta_completa for word in ["impresora", "impresor"]):
        if any(word in consulta_completa for word in ["resina", "sla", "lcd", "bisuteria", "bisutería", "detalle", "miniatura"]):
            return {"tipo": "impresora", "tecnologia": "resina"}
        elif any(word in consulta_completa for word in ["fdm", "filamento", "pla", "abs", "petg"]):
            return {"tipo": "impresora", "tecnologia": "fdm"}
        else:
            return {"tipo": "impresora", "tecnologia": None}
    
    # Detectar filamentos
    if any(word in consulta_completa for word in ["filamento", "pla", "abs", "petg", "tpu"]):
        return {"tipo": "filamento"}
    
    # Detectar resinas (material)
    if any(word in consulta_completa for word in ["resina"]) and not any(word in consulta_completa for word in ["impresora", "impresor"]):
        return {"tipo": "resina_material"}
    
    return {"tipo": "general"}

# === Filtrar catálogo por tipo de producto ===
def filtrar_por_tipo(catalog, deteccion):
    if deteccion["tipo"] == "impresora":
        # Filtrar solo impresoras
        productos_filtrados = []
        for p in catalog:
            categorias = p.get("Categorías del producto", [])
            es_impresora = any(
                cat.get("Categoría", "").lower() == "impresoras 3d" 
                for cat in categorias
            )
            if es_impresora:
                if deteccion.get("tecnologia") == "resina":
                    # Buscar específicamente resina/LCD
                    es_resina = any(
                        cat.get("Subcategoría", "").lower() in ["resina", "lcd", "sla"]
                        for cat in categorias
                    )
                    if es_resina:
                        productos_filtrados.append(p)
                elif deteccion.get("tecnologia") == "fdm":
                    # Buscar específicamente FDM (o que NO sea resina)
                    no_es_resina = not any(
                        cat.get("Subcategoría", "").lower() in ["resina", "lcd", "sla"]
                        for cat in categorias
                    )
                    if no_es_resina:
                        productos_filtrados.append(p)
                else:
                    # Sin filtro de tecnología específica
                    productos_filtrados.append(p)
        return productos_filtrados
    
    elif deteccion["tipo"] == "filamento":
        # Filtrar solo filamentos
        return [
            p for p in catalog
            if any(
                cat.get("Categoría", "").lower() == "filamentos"
                for cat in p.get("Categorías del producto", [])
            )
        ]
    
    elif deteccion["tipo"] == "resina_material":
        # Filtrar solo resinas (materiales)
        return [
            p for p in catalog
            if any(
                cat.get("Categoría", "").lower() == "resinas"
                for cat in p.get("Categorías del producto", [])
            )
        ]
    
    # Sin filtro específico, devolver todo
    return catalog

# === Buscar productos con contexto conversacional ===
def buscar_productos_contextuales(query, historial, catalog, top_k=2):
    # Detectar tipo de producto solicitado
    deteccion = detectar_tipo_producto(query, historial)
    
    # Construir consulta contextual
    consulta_completa = query
    if historial:
        mensajes_recientes = []
        for msg in historial[-6:]:
            if msg["role"] == "user":
                mensajes_recientes.append(msg["content"])
        
        if mensajes_recientes:
            consulta_completa = " ".join(mensajes_recientes[-2:]) + " " + query
    
    # Filtrar por stock Y por tipo de producto
    catalog_por_tipo = filtrar_por_tipo(catalog, deteccion)
    catalog_filtrado = [
        p for p in catalog_por_tipo
        if p.get("Stock Status", "").lower() == "instock" and "embedding" in p
    ]
    
    if not catalog_filtrado:
        return []
    
    print(f"Debug: Encontrados {len(catalog_filtrado)} productos del tipo {deteccion}")

    # Generar embedding de la consulta contextual
    embedding_query = client.embeddings.create(
        model="text-embedding-3-small",
        input=consulta_completa
    ).data[0].embedding

    # Calcular similitudes
    similitudes = [(vector_similaridad(embedding_query, p["embedding"]), p) for p in catalog_filtrado]
    similitudes.sort(key=lambda x: x[0], reverse=True)

    return [p for _, p in similitudes[:top_k]]

# === Determinar si debe mostrar productos ===
def debe_mostrar_productos(respuesta_ia):
    # Indicadores de que el IA decidió mostrar productos
    indicadores_productos = [
        "según tu consulta, se encontraron",
        "aquí tienes las opciones", 
        "estos son los productos",
        "recomiendo los siguientes",
        "[ver producto]",
        "s/"  # precio en soles
    ]
    
    respuesta_lower = respuesta_ia.lower()
    return any(indicador in respuesta_lower for indicador in indicadores_productos)

# === Limpiar respuesta del IA (quitar listas de productos) ===
def limpiar_respuesta_productos(respuesta):
    import re
    
    # Remover listas de productos con enlaces
    patron_lista = r'- \[.*?\] \(S/.*?\) \[Ver producto\].*?(?=\n|$)'
    respuesta = re.sub(patron_lista, '', respuesta, flags=re.MULTILINE | re.DOTALL)
    
    # Remover líneas que solo contengan guiones o estén vacías
    lineas = respuesta.split('\n')
    lineas_limpias = []
    
    for linea in lineas:
        linea = linea.strip()
        if linea and not linea.startswith('- [') and linea != '-':
            lineas_limpias.append(linea)
    
    respuesta_limpia = '\n'.join(lineas_limpias)
    
    # Limpiar múltiples saltos de línea
    respuesta_limpia = re.sub(r'\n\s*\n+', '\n\n', respuesta_limpia)
    
    return respuesta_limpia.strip()

# === Endpoint principal ===
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_msg = data.get("message","").strip()
    session_id = data.get("session_id")
    if not user_msg:
        return jsonify({"error": "Mensaje vacío"}), 400

    # Crear nueva sesión si no existe
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {"history":[]}
    session_data = sessions[session_id]

    # Buscar productos con contexto conversacional
    productos_relevantes = buscar_productos_contextuales(user_msg, session_data["history"], catalog, top_k=2)

    # Preparar contexto de productos para el IA
    if productos_relevantes:
        productos_texto = "\n".join([
            f"- {p.get('Title', '')} | Precio: S/ {p.get('Sale Price', 0)} | Link: {p.get('Permalink', '')}"
            for p in productos_relevantes
        ])
    else:
        productos_texto = "No se encontraron productos relevantes en stock."

    # Construir historial para el modelo
    mensajes = [{"role": "system", "content": PROMPT_BASE}] + session_data["history"]
    mensajes.append({
        "role": "user", 
        "content": f"{user_msg}\n\nProductos disponibles en catálogo:\n{productos_texto}"
    })

    # Llamar al modelo
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=mensajes,
        temperature=0.7
    )

    respuesta = completion.choices[0].message.content

    # Guardar en historial
    session_data["history"].append({"role": "user", "content": user_msg})
    session_data["history"].append({"role": "assistant", "content": respuesta})

    # Determinar si incluir productos en la respuesta
    incluir_productos = debe_mostrar_productos(respuesta) and productos_relevantes

    # Si va a mostrar productos, limpiar la respuesta de listas duplicadas
    respuesta_final = limpiar_respuesta_productos(respuesta) if incluir_productos else respuesta

    response_data = {
        "session_id": session_id,
        "respuesta": respuesta_final,
        "mostrar_productos": bool(productos_relevantes)
    }

    # Solo incluir productos si el IA decidió mostrarlos (datos mínimos)
    if incluir_productos:
        response_data["productos"] = [
            {
                "nombre": p.get("Title", ""),
                "precio": f"S/ {p.get('Sale Price', 0)}",
                "imagen": p.get("Image URL", ""),
                "enlace": p.get("Permalink", "")
            }
            for p in productos_relevantes
        ]

    return jsonify(response_data)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
