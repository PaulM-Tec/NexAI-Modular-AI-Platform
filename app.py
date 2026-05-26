import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
 
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
app = Flask(__name__)
CORS(app)
 
def vehicle_ai(msg):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":"Automotive assistant. Short structured responses only."},
            {"role":"user","content":msg}
        ]
    )
    return response.choices[0].message.content
 
def it_ai(msg):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":"Enterprise IT admin assistant. Use PowerShell or Admin Center. Keep answers short."},
            {"role":"user","content":msg}
        ]
    )
    return response.choices[0].message.content
 
def detect(msg):
    m = msg.lower()
 
    if any(w in m for w in ["api","azure","app","permission","exchange","mailbox","tenant","group"]):
        return "it"
 
    if any(w in m for w in ["car","engine","oil","leak","vehicle","brake"]):
        return "vehicle"
 
    return "it"
 
@app.get("/vehicle")
def vehicle_ui():
    return send_from_directory(".", "index_vehicle.html")
 
@app.get("/it")
def it_ui():
    return send_from_directory(".", "index_it.html")
 
@app.post("/chat")
def chat():
    msg = request.get_json().get("message","")
 
    if detect(msg) == "vehicle":
        reply = vehicle_ai(msg)
    else:
        reply = it_ai(msg)
 
    return jsonify({"response": reply})
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",5000)))