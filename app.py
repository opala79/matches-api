from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return "API Online 🚀"

@app.route("/matches")
def matches():
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": "8961c2d775f0096722b5f104d39a4080"}
    params = {"date": "2025-09-24"}  # pode deixar dinâmico depois
    
    r = requests.get(url, headers=headers, params=params, timeout=20)
    data = r.json()
    
    # devolve tudo em JSON
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
