from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

API_URL = "https://v3.football.api-sports.io/fixtures"
API_KEY = "8961c2d775f0096722b5f104d39a4080"  # substitua pela sua chave real

# Definir países/ligas que interessam (Europa + Brasil)
ALLOWED_COUNTRIES = ["Brazil", "England", "Spain", "Italy", "Germany", "France", "Portugal", "Netherlands", "Belgium", "Switzerland", "Austria", "Scotland"]  # adicione mais se quiser

@app.route("/")
def home():
    return "API Online 🚀"

@app.route("/matches")
def matches():
    date = request.args.get("date", "2025-09-24")
    
    headers = {"x-apisports-key": API_KEY}
    params = {"date": date}
    
    r = requests.get(API_URL, headers=headers, params=params, timeout=20)
    data = r.json()
    
    filtered = []
    
    for match in data.get("response", []):
        league = match.get("league", {})
        if league.get("country") not in ALLOWED_COUNTRIES:
            continue  # ignora jogos de outros países

        fixture = match.get("fixture", {})
        teams = match.get("teams", {})
        score = match.get("score", {})

        # histórico dos times - pegar últimos 5 jogos (apenas resultados)
        history = {}
        for side in ["home", "away"]:
            team_id = teams.get(side, {}).get("id")
            hist_resp = requests.get(
                "https://v3.football.api-sports.io/fixtures",
                headers=headers,
                params={"team": team_id, "last": 5}
            ).json()
            # guardar apenas resultados simples
            history[side] = [
                {
                    "opponent": h["teams"]["away"]["name"] if side=="home" else h["teams"]["home"]["name"],
                    "score": f"{h['score']['fulltime']['home']}-{h['score']['fulltime']['away']}",
                    "status": h["fixture"]["status"]["short"]
                } for h in hist_resp.get("response", [])
            ]
        
        filtered.append({
            "home": teams.get("home", {}).get("name"),
            "away": teams.get("away", {}).get("name"),
            "home_id": teams.get("home", {}).get("id"),
            "away_id": teams.get("away", {}).get("id"),
            "score": f"{score.get('fulltime', {}).get('home', '-')}-{score.get('fulltime', {}).get('away', '-')}",
            "status": fixture.get("status", {}).get("short"),
            "league": league.get("name"),
            "league_id": league.get("id"),
            "date": fixture.get("date"),
            "history": history
        })
    
    return jsonify(filtered)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
