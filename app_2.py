from flask import Flask, jsonify
import requests

app = Flask(__name__)

# Lista completa de países da Europa + Brasil
ALLOWED_COUNTRIES = [
    "Brazil", "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan", "Belarus",
    "Belgium", "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Denmark", "England", "Estonia", "Faroe Islands", "Finland", "France", "Georgia",
    "Germany", "Gibraltar", "Greece", "Hungary", "Iceland", "Ireland", "Israel",
    "Italy", "Kazakhstan", "Kosovo", "Latvia", "Liechtenstein", "Lithuania", "Luxembourg",
    "Malta", "Moldova", "Monaco", "Montenegro", "Netherlands", "North Macedonia", "Norway",
    "Poland", "Portugal", "Romania", "Russia", "San Marino", "Scotland", "Serbia",
    "Slovakia", "Slovenia", "Spain", "Sweden", "Switzerland", "Turkey", "Ukraine", "Wales"
]

# Endpoint da API que já está no Azure
API_URL = "https://tstmvs03.azurewebsites.net/matches"
HEADERS = {
    "x-apisports-key": "8961c2d775f0096722b5f104d39a4080"
}

@app.route("/matches_filtered/<date>", methods=["GET"])
def get_matches_filtered(date):
    try:
        # Busca os jogos do dia
        response = requests.get(f"{API_URL}?date={date}", headers=HEADERS)
        data = response.json()

        filtered_matches = []

        # Filtra apenas jogos de Europa + Brasil e reorganiza campos
        for match in data.get("response", []):
            league_country = match.get("league", {}).get("country", "")
            if league_country in ALLOWED_COUNTRIES:
                filtered_matches.append({
                    "fixture_id": match["fixture"]["id"],
                    "date": match["fixture"]["date"],
                    "status": match["fixture"]["status"]["short"],
                    "elapsed": match["fixture"]["status"].get("elapsed"),
                    "referee": match["fixture"].get("referee"),
                    "venue": match["fixture"].get("venue"),
                    "league": match.get("league"),
                    "teams": match.get("teams"),
                    "score": match.get("score")
                })

        return jsonify({
            "date": date,
            "matches_count": len(filtered_matches),
            "matches": filtered_matches
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
