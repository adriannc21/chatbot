from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os, json, numpy as np, uuid, re
from openai import OpenAI

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

def buscar_productos(query, historial, catalog, top_k=2):
    """
    Python solo filtra productos en stock y top_k según embedding de consulta.
    No hace inferencias ni calcula precios.
    """
    # Combina últimas consultas de usuario para mayor contexto
    consulta = query
    if historial:
        msgs = [m["content"] for m in historial[-4:] if m["role"]=="user"]
        if msgs:
            consulta = " ".join(msgs[-2:]) + " " + query

    # Filtrado básico de stock
    catalog_filtrado = [p for p in catalog if p.get("Stock Status", "").lower() == "instock" and "embedding" in p]
    if not catalog_filtrado:
        return []

    # Calcular similitudes
    emb_query = client.embeddings.create(model="text-embedding-3-small", input=consulta).data[0].embedding
    similitudes = [(vector_similaridad(emb_query, p["embedding"]), p) for p in catalog_filtrado]
    similitudes.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in similitudes[:top_k]]

def limpiar_respuesta(respuesta):
    # Eliminar precios o links accidentales generados por la IA
    respuesta = re.sub(r'\(S/ \d+(\.\d+)?\)', '', respuesta)
    lineas = [l.strip() for l in respuesta.split('\n') if l.strip()]
    return "\n".join(lineas)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_msg = data.get("message", "").strip()
    session_id = data.get("session_id")
    if not user_msg:
        return jsonify({"error": "Mensaje vacío"}), 400
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {"history": []}

    session_data = sessions[session_id]

    # Buscar productos usando embeddings
    productos_relevantes = buscar_productos(user_msg, session_data["history"], catalog, top_k=2)

    # Armar contenido para la IA (mantener precios exactos)
    productos_texto = "\n".join([f"{p['Title']} (S/ {p['Sale Price']})" for p in productos_relevantes])
    contenido_usuario = user_msg
    if productos_relevantes:
        contenido_usuario += f"\nEstos productos están disponibles:\n{productos_texto}\nResponde de manera natural y haz preguntas de seguimiento si aplica."

    # Preparar mensajes para OpenAI
    mensajes = [{"role": "system", "content": PROMPT_BASE}] + session_data["history"]
    mensajes.append({"role": "user", "content": contenido_usuario})

    try:
        completion = client.chat.completions.create(model="gpt-4o", messages=mensajes, temperature=0.7)
        respuesta = completion.choices[0].message.content
    except Exception:
        respuesta = "Para ayudarte mejor, necesito algunos detalles:\n- Rango de precio?\n- Marca preferida?\n- Color o material deseado?"

    # Guardar historial
    session_data["history"].append({"role": "user", "content": user_msg})
    session_data["history"].append({"role": "assistant", "content": respuesta})

    # Limpiar respuesta de precios inventados
    respuesta_final = limpiar_respuesta(respuesta)

    # Preparar JSON
    response_data = {
        "session_id": session_id,
        "respuesta": respuesta_final,
        "mostrar_productos": bool(productos_relevantes)
    }

    if productos_relevantes:
        response_data["productos"] = [
            {
                "nombre": p.get("Title", ""),
                "precio": f"S/ {p.get('Sale Price',0)}",
                "imagen": p.get("Image URL", ""),
                "enlace": p.get("Permalink", "")
            } for p in productos_relevantes
        ]

    return jsonify(response_data)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
