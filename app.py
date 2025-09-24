from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# 🔑 Chave da API
API_KEY = os.getenv("API_FOOTBALL_KEY", "8961c2d775f0096722b5f104d39a4080")
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

# 🌍 Endpoint simples: retorna só os jogos
@app.route("/matches")
def get_matches():
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "Parâmetro 'date' é obrigatório"}), 400

    url = f"{BASE_URL}/fixtures?date={date}"
    resp = requests.get(url, headers=HEADERS)

    if resp.status_code != 200:
        return jsonify({"error": "Falha ao consultar API-Football"}), 500

    return jsonify(resp.json())


# 🌍 Endpoint completo: jogos + odds (Betano) + últimos 5 jogos dos times
@app.route("/matches/full")
def get_matches_full():
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "Parâmetro 'date' é obrigatório"}), 400

    url = f"{BASE_URL}/fixtures?date={date}"
    resp = requests.get(url, headers=HEADERS)

    if resp.status_code != 200:
        return jsonify({"error": "Falha ao consultar API-Football"}), 500

    data = resp.json()
    enriched_matches = []

    for match in data.get("response", []):
        fixture_id = match["fixture"]["id"]
        home_id = match["teams"]["home"]["id"]
        away_id = match["teams"]["away"]["id"]

        # --- Odds (Betano, ID = 8) ---
        odds_url = f"{BASE_URL}/odds?fixture={fixture_id}&bookmaker=8"
        odds_resp = requests.get(odds_url, headers=HEADERS).json()
        odds = odds_resp.get("response", [])

        # --- Últimos 5 jogos do time da casa ---
        home_stats_url = f"{BASE_URL}/fixtures?team={home_id}&last=5"
        home_stats = requests.get(home_stats_url, headers=HEADERS).json().get("response", [])

        # --- Últimos 5 jogos do time visitante ---
        away_stats_url = f"{BASE_URL}/fixtures?team={away_id}&last=5"
        away_stats = requests.get(away_stats_url, headers=HEADERS).json().get("response", [])

        # --- Monta estrutura enriquecida ---
        enriched_matches.append({
            "fixture": match["fixture"],
            "league": match["league"],
            "teams": match["teams"],
            "odds": odds,
            "home_last5": home_stats,
            "away_last5": away_stats
        })

    return jsonify({"date": date, "matches": enriched_matches})


if __name__ == "__main__":
    app.run(debug=True)
