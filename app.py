from flask import Flask, jsonify, request
import requests
from datetime import datetime

app = Flask(__name__)

API_URL = "https://v3.football.api-sports.io/fixtures"
API_KEY = "8961c2d775f0096722b5f104d39a4080"

# Lista COMPLETA de países da Europa + Brasil
ALLOWED_COUNTRIES = {
    # Brasil
    "Brazil",
    
    # Europa Ocidental
    "England", "Spain", "Italy", "Germany", "France", "Portugal", 
    "Netherlands", "Belgium", "Switzerland", "Austria", "Scotland",
    "Ireland", "Wales", "Luxembourg", "Monaco"
}

@app.route("/")
def home():
    return "API Online 🚀 Use /matches?date=YYYY-MM-DD"

@app.route("/matches")
def matches():
    date = request.args.get("date")
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    headers = {"x-apisports-key": API_KEY}
    params = {"date": date}
    
    try:
        print(f"Buscando jogos para: {date}")
        r = requests.get(API_URL, headers=headers, params=params, timeout=30)
        
        if r.status_code != 200:
            return jsonify({
                "error": f"Erro na API Football: {r.status_code}",
                "message": "Limite de requisições excedido ou API indisponível"
            }), 500
            
        data = r.json()
        
        if data.get("errors"):
            return jsonify({
                "error": "API Football retornou erro",
                "details": data.get("errors")
            }), 500
            
    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": "Falha ao conectar com API de jogos",
            "details": str(e)
        }), 500
    
    filtered = []
    response_data = data.get("response", [])
    
    print(f"Encontrados {len(response_data)} jogos totais")
    
    # Coletar países encontrados para debug
    countries_found = set()
    filtered_countries = set()
    
    for match in response_data:
        league = match.get("league", {})
        country = league.get("country")
        countries_found.add(country)
        
        # DEBUG: Log para verificar o que está sendo processado
        home_team = match.get('teams', {}).get('home', {}).get('name', 'Unknown')
        away_team = match.get('teams', {}).get('away', {}).get('name', 'Unknown')
        
        # Filtro por países permitidos
        if country not in ALLOWED_COUNTRIES:
            print(f"FILTRO: Ignorando jogo de {country}: {home_team} vs {away_team}")
            continue
        
        filtered_countries.add(country)
        print(f"INCLUÍDO: Jogo de {country}: {home_team} vs {away_team}")

        fixture = match.get("fixture", {})
        teams = match.get("teams", {})
        score = match.get("score", {})
        
        fulltime = score.get('fulltime', {})
        home_score = fulltime.get('home', '-')
        away_score = fulltime.get('away', '-')
        
        if home_score is None: home_score = '-'
        if away_score is None: away_score = '-'

        match_data = {
            "home": teams.get("home", {}).get("name"),
            "away": teams.get("away", {}).get("name"),
            "score": f"{home_score}-{away_score}",
            "status": fixture.get("status", {}).get("short"),
            "league": league.get("name"),
            "country": country,
            "date": fixture.get("date")
        }
        
        filtered.append(match_data)
    
    print(f"Países encontrados na API: {countries_found}")
    print(f"Países que passaram no filtro: {filtered_countries}")
    print(f"Filtrados {len(filtered)} jogos da Europa/Brasil")
    
    return jsonify({
        "date": date,
        "total_matches": len(filtered),
        "countries_found": list(countries_found),
        "countries_filtered": list(filtered_countries),
        "matches": filtered
    })

@app.route("/debug/countries")
def debug_countries():
    """Endpoint para verificar países permitidos"""
    return jsonify({
        "allowed_countries": sorted(list(ALLOWED_COUNTRIES)),
        "total_countries": len(ALLOWED_COUNTRIES)
    })

@app.route("/test")
def test():
    """Endpoint de teste simples"""
    return jsonify({
        "status": "ok",
        "message": "API está funcionando",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)