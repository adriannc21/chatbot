from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os, json, numpy as np
from openai import OpenAI
import uuid
import re

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

def detectar_tipo_producto(query, historial):
    consulta = query.lower()
    if historial:
        for msg in historial[-4:]:
            if msg["role"] == "user":
                consulta += " " + msg["content"].lower()
    if any(w in consulta for w in ["impresora", "impresor"]):
        if any(w in consulta for w in ["resina", "sla", "lcd", "detalle", "miniatura"]):
            return {"tipo": "impresora", "tecnologia": "resina"}
        elif any(w in consulta for w in ["fdm", "filamento", "pla", "abs", "petg"]):
            return {"tipo": "impresora", "tecnologia": "fdm"}
        else:
            return {"tipo": "impresora", "tecnologia": None}
    if any(w in consulta for w in ["filamento", "pla", "abs", "petg", "tpu"]):
        return {"tipo": "filamento"}
    if "resina" in consulta and not any(w in consulta for w in ["impresora", "impresor"]):
        return {"tipo": "resina_material"}
    return {"tipo": "general"}

def filtrar_por_tipo(catalog, deteccion):
    if deteccion["tipo"] == "impresora":
        res = []
        for p in catalog:
            cats = p.get("Categorías del producto", [])
            es_impresora = any(cat.get("Categoría","").lower()=="impresoras 3d" for cat in cats)
            if es_impresora:
                if deteccion.get("tecnologia")=="resina":
                    if any(cat.get("Subcategoría","").lower() in ["resina","lcd","sla"] for cat in cats):
                        res.append(p)
                elif deteccion.get("tecnologia")=="fdm":
                    if not any(cat.get("Subcategoría","").lower() in ["resina","lcd","sla"] for cat in cats):
                        res.append(p)
                else:
                    res.append(p)
        return res
    elif deteccion["tipo"]=="filamento":
        return [p for p in catalog if any(cat.get("Categoría","").lower()=="filamentos" for cat in p.get("Categorías del producto",[]))]
    elif deteccion["tipo"]=="resina_material":
        return [p for p in catalog if any(cat.get("Categoría","").lower()=="resinas" for cat in p.get("Categorías del producto",[]))]
    return catalog

def buscar_productos_contextuales(query, historial, catalog, top_k=2):
    deteccion = detectar_tipo_producto(query, historial)
    consulta = query
    if historial:
        msgs = [m["content"] for m in historial[-6:] if m["role"]=="user"]
        if msgs:
            consulta = " ".join(msgs[-2:]) + " " + query
    catalog_tipo = filtrar_por_tipo(catalog, deteccion)
    catalog_filtrado = [p for p in catalog_tipo if p.get("Stock Status","").lower()=="instock" and "embedding" in p]
    if not catalog_filtrado:
        return []
    emb_query = client.embeddings.create(model="text-embedding-3-small", input=consulta).data[0].embedding
    similitudes = [(vector_similaridad(emb_query, p["embedding"]), p) for p in catalog_filtrado]
    similitudes.sort(key=lambda x: x[0], reverse=True)
    return [p for _,p in similitudes[:top_k]]

def debe_mostrar_productos(respuesta):
    indicadores = ["según tu consulta, se encontraron", "aquí tienes las opciones", "estos son los productos", "recomiendo los siguientes", "[ver producto]", "s/"]
    return any(i in respuesta.lower() for i in indicadores)

def limpiar_respuesta_productos(respuesta):
    patron = r'- \[.*?\] \(S/.*?\) \[Ver producto\].*?(?=\n|$)'
    respuesta = re.sub(patron, '', respuesta, flags=re.MULTILINE|re.DOTALL)
    lineas = respuesta.split('\n')
    lineas_limpias = [l.strip() for l in lineas if l.strip() and not l.startswith('- [') and l!='-']
    respuesta_limpia = '\n'.join(lineas_limpias)
    return re.sub(r'\n\s*\n+', '\n\n', respuesta_limpia).strip()

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_msg = data.get("message","").strip()
    session_id = data.get("session_id")
    if not user_msg:
        return jsonify({"error":"Mensaje vacío"}),400
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {"history":[]}
    session_data = sessions[session_id]

    productos_relevantes = buscar_productos_contextuales(user_msg, session_data["history"], catalog, top_k=2)

    # Preparar texto para IA
    if productos_relevantes:
        productos_texto = "\n".join([f"- {p.get('Title','')} | Precio: S/ {p.get('Sale Price',0)} | Link: {p.get('Permalink','')}" for p in productos_relevantes])
    else:
        productos_texto = "No se encontraron productos relevantes en stock."

    mensajes = [{"role":"system","content":PROMPT_BASE}] + session_data["history"]
    mensajes.append({"role":"user","content": f"{user_msg}\n\nProductos disponibles en catálogo:\n{productos_texto}"})

    # Llamada principal a OpenAI con fallback para preguntas abiertas
    try:
        completion = client.chat.completions.create(model="gpt-4o", messages=mensajes, temperature=0.7)
        respuesta = completion.choices[0].message.content
    except Exception:
        # fallback si algo falla
        respuesta = "Para ayudarte mejor, necesito algunos detalles:\n- Rango de precio?\n- Marca preferida?\n- Color o material deseado?"

    session_data["history"].append({"role":"user","content":user_msg})
    session_data["history"].append({"role":"assistant","content":respuesta})

    incluir_productos = debe_mostrar_productos(respuesta) and productos_relevantes
    respuesta_final = limpiar_respuesta_productos(respuesta) if incluir_productos else respuesta

    response_data = {
        "session_id": session_id,
        "respuesta": respuesta_final,
        "mostrar_productos": incluir_productos
    }

    if incluir_productos:
        response_data["productos"] = [
            {
                "nombre": p.get("Title",""),
                "precio": f"S/ {p.get('Sale Price',0)}",
                "imagen": p.get("Image URL",""),
                "enlace": p.get("Permalink","")
            } for p in productos_relevantes
        ]

    return jsonify(response_data)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
