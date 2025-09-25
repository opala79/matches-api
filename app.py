from flask import Flask, jsonify, request
import requests
from datetime import datetime

app = Flask(__name__)

API_URL = "https://v3.football.api-sports.io/fixtures"
API_KEY = "8961c2d775f0096722b5f104d39a4080"

# Lista de países permitidos (Europa + Brasil)
ALLOWED_COUNTRIES = {
    "Brazil", "England", "Spain", "Italy", "Germany", "France", 
    "Portugal", "Netherlands", "Belgium", "Switzerland", 
    "Austria", "Scotland", "Russia", "Ukraine", "Poland",
    "Turkey", "Greece", "Denmark", "Sweden", "Norway"
}

@app.route('/')
def home():
    return "API Online 🚀 Use /matches?date=YYYY-MM-DD"

@app.route('/test')
def test():
    return jsonify({
        "status": "success", 
        "message": "Test route is working!",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/debug/countries')
def debug_countries():
    return jsonify({
        "allowed_countries": sorted(list(ALLOWED_COUNTRIES)),
        "total_countries": len(ALLOWED_COUNTRIES)
    })

@app.route('/matches')
def matches():
    date = request.args.get('date')
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    
    headers = {'x-apisports-key': API_KEY}
    params = {'date': date}
    
    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'error': 'API request failed', 'status_code': response.status_code}), 500
            
        data = response.json()
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    filtered_matches = []
    
    for match in data.get('response', []):
        country = match.get('league', {}).get('country')
        
        # Aplicar filtro
        if country not in ALLOWED_COUNTRIES:
            continue
            
        fixture = match.get('fixture', {})
        teams = match.get('teams', {})
        score = match.get('score', {})
        fulltime = score.get('fulltime', {})
        
        match_info = {
            'home': teams.get('home', {}).get('name'),
            'away': teams.get('away', {}).get('name'),
            'score': f"{fulltime.get('home', '-')}-{fulltime.get('away', '-')}",
            'status': fixture.get('status', {}).get('short'),
            'league': match.get('league', {}).get('name'),
            'country': country,
            'date': fixture.get('date')
        }
        filtered_matches.append(match_info)
    
    return jsonify({
        'date': date,
        'total_matches': len(filtered_matches),
        'matches': filtered_matches
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
