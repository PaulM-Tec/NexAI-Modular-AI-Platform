import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
 
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
app = Flask(__name__)
CORS(app)
 
# -------------------------
# VEHICLE AI
# -------------------------
def vehicle_ai(msg):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role":"system",
                "content":"You are an automotive assistant. Only answer vehicle-related queries. Be concise."
            },
            {"role":"user","content":msg}
        ]
    )
    return response.choices[0].message.content
 
 
# -------------------------
# IT AI
# -------------------------
def it_ai(msg):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role":"system",
                "content":"You are an enterprise IT admin assistant (Exchange, Entra, M365). Use backend/admin perspective only."
            },
            {"role":"user","content":msg}
        ]
    )
    return response.choices[0].message.content
 
 
# -------------------------
# ROUTES
# -------------------------
 
@app.get("/vehicle")
def vehicle_ui():
    return send_from_directory(".", "index_vehicle.html")
 
@app.get("/it")
def it_ui():
    return send_from_directory(".", "index_it.html")
 
 
# IMPORTANT: MODULE PARAM USED
@app.post("/chat")
def chat():
 
    data = request.get_json()
    msg = data.get("message", "")
    module = data.get("module", "")  # KEY FIX
 
    if module == "vehicle":
        reply = vehicle_ai(msg)
 
    elif module == "it":
        reply = it_ai(msg)
 
    else:
        return jsonify({"response": "Invalid module request."})
 
    return jsonify({"response": reply})
 
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",5000)))