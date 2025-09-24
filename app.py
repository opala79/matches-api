# app.py
from flask import Flask, request, jsonify
import requests
import os
import time
import statistics
from typing import Dict, Any, List

app = Flask(__name__)

API_KEY = os.getenv("API_FOOTBALL_KEY", "8961c2d775f0096722b5f104d39a4080")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# Países/ligas alvo: Europa top + Brazil (pode ajustar)
ALLOWED_COUNTRIES = [
    "England", "Spain", "Italy", "Germany", "France", "Portugal", "Netherlands",
    "Belgium", "Switzerland", "Austria", "Denmark", "Sweden", "Norway", "Poland",
    "Czech Republic", "Croatia", "Serbia", "Greece", "Turkey", "Scotland", "Brazil"
]

TOP_LEAGUES = {
    "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1",
    "Primeira Liga", "Eredivisie"
}

# Simple in-memory caches with TTL to avoid repeated API calls
team_history_cache: Dict[int, Dict[str, Any]] = {}
odds_cache: Dict[int, Dict[str, Any]] = {}
CACHE_TTL = 300  # seconds


def now_ts() -> float:
    return time.time()


def cache_get(cache: Dict, key):
    entry = cache.get(key)
    if not entry:
        return None
    if now_ts() - entry["ts"] > CACHE_TTL:
        del cache[key]
        return None
    return entry["value"]


def cache_set(cache: Dict, key, value):
    cache[key] = {"ts": now_ts(), "value": value}


session = requests.Session()
session.headers.update(HEADERS)
session.timeout = 20


def safe_get_json(url: str, params: dict = None) -> dict:
    """GET wrapper with basic error handling."""
    try:
        resp = session.get(url, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        # return minimal structure to allow caller to continue
        return {"errors": [str(e)], "response": []}


def summarize_last_fixtures(fixtures: List[dict], team_id: int) -> dict:
    """Given fixtures (API response list) calculate simple stats for the team."""
    goals_for = []
    goals_against = []
    results = []  # "W","D","L"
    for f in fixtures:
        # determine if team is home or away
        home = f.get("teams", {}).get("home", {})
        away = f.get("teams", {}).get("away", {})
        score = f.get("score", {}).get("fulltime", {})
        # skip fixtures with no score
        if score.get("home") is None or score.get("away") is None:
            continue
        if home.get("id") == team_id:
            gf = score.get("home", 0)
            ga = score.get("away", 0)
            if gf > ga:
                results.append("W")
            elif gf == ga:
                results.append("D")
            else:
                results.append("L")
        elif away.get("id") == team_id:
            gf = score.get("away", 0)
            ga = score.get("home", 0)
            if gf > ga:
                results.append("W")
            elif gf == ga:
                results.append("D")
            else:
                results.append("L")
        else:
            # fixture not involving the team (shouldn't happen)
            continue
        goals_for.append(gf)
        goals_against.append(ga)

    avg_for = round(statistics.mean(goals_for), 2) if goals_for else None
    avg_against = round(statistics.mean(goals_against), 2) if goals_against else None
    win_rate = round(results.count("W") / len(results), 3) if results else None

    return {
        "last_results": results,
        "games_counted": len(results),
        "avg_goals_for": avg_for,
        "avg_goals_against": avg_against,
        "win_rate": win_rate
    }


def get_team_last5(team_id: int) -> List[dict]:
    """Return last 5 fixtures for a team (cached)."""
    cached = cache_get(team_history_cache, team_id)
    if cached is not None:
        return cached

    url = f"{BASE_URL}/fixtures"
    params = {"team": team_id, "last": 5}
    res = safe_get_json(url, params=params)
    fixtures = res.get("response", [])
    cache_set(team_history_cache, team_id, fixtures)
    return fixtures


def get_odds_for_fixture(fixture_id: int) -> List[dict]:
    """Return odds list for a fixture (cached)."""
    cached = cache_get(odds_cache, fixture_id)
    if cached is not None:
        return cached

    url = f"{BASE_URL}/odds"
    params = {"fixture": fixture_id}
    res = safe_get_json(url, params=params)
    odds_list = res.get("response", [])
    cache_set(odds_cache, fixture_id, odds_list)
    return odds_list


def extract_betano(odds_list: List[dict]) -> dict:
    """Search odds_list for bookmaker 'Betano' (case-insensitive). Return structured if found."""
    for o in odds_list:
        # API format: each element may have 'bookmaker' or 'bookmaker' nested
        # try common patterns
        bm = o.get("bookmaker") or o.get("bookmaker", {})
        name = ""
        if isinstance(bm, dict):
            name = bm.get("name", "")
        elif isinstance(o.get("bookmaker"), str):
            name = o.get("bookmaker")
        if "betano" in name.lower():
            return o
    # not found: try to return the first bookmaker's main bets (fallback)
    if odds_list:
        return odds_list[0]
    return {}


@app.route("/matches")
def matches_simple():
    """Existing simple matches endpoint (proxy to your matches source)"""
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "date is required"}), 400

    # This assumes your existing endpoint (the one you already run) is accessible
    src_url = f"https://tstmvs03.azurewebsites.net/matches?date={date}"
    data = safe_get_json(src_url)
    # your source returns an object with 'matches' or 'response' depending on your format;
    # try to normalize: if it already has matches list, return as-is. Otherwise return by best-effort.
    if isinstance(data, dict) and "matches" in data:
        return jsonify(data)
    return jsonify(data)


@app.route("/matches/full")
def matches_full():
    """Enriched endpoint: matches + history (last5) + odds (Betano if present)."""
    date = request.args.get("date")
    only_top = request.args.get("only_top", "false").lower() in ("1", "true", "yes")
    if not date:
        return jsonify({"error": "date is required"}), 400

    # get base matches from your existing source
    src_url = f"https://tstmvs03.azurewebsites.net/matches?date={date}"
    src = safe_get_json(src_url)

    # normalize to list of matches
    matches_list = []
    if isinstance(src, dict):
        # if it already has a 'matches' key
        if "matches" in src:
            matches_list = src["matches"]
        elif "response" in src:
            # some formats use response
            matches_list = src.get("response", [])
        else:
            # if it's already a list (unlikely), try to use that
            if isinstance(src, list):
                matches_list = src
    elif isinstance(src, list):
        matches_list = src

    enriched = []
    for m in matches_list:
        country = m.get("country") or (m.get("league", {}).get("country") if isinstance(m.get("league"), dict) else None)
        league_name = m.get("league") if isinstance(m.get("league"), str) else (m.get("league", {}).get("name") if isinstance(m.get("league"), dict) else None)

        # filter by allowed countries
        if country not in ALLOWED_COUNTRIES:
            continue

        # optional: if only_top, filter by league name in TOP_LEAGUES
        if only_top and league_name not in TOP_LEAGUES:
            continue

        # try to obtain fixture id and team ids if present. If not, we'll skip enrichment for history/odds
        fixture_id = m.get("fixture_id") or (m.get("fixture", {}).get("id") if isinstance(m.get("fixture"), dict) else None)
        home_id = m.get("home_id") or (m.get("teams", {}).get("home", {}).get("id") if isinstance(m.get("teams"), dict) else None)
        away_id = m.get("away_id") or (m.get("teams", {}).get("away", {}).get("id") if isinstance(m.get("teams"), dict) else None)

        # fetch odds
        odds_info = {}
        if fixture_id:
            odds_list = get_odds_for_fixture(fixture_id)
            betano = extract_betano(odds_list)
            odds_info = {"betano": betano, "all": odds_list}

        # fetch last 5 fixtures for each team
        home_last5 = []
        away_last5 = []
        home_summary = {}
        away_summary = {}
        if home_id:
            fixtures = get_team_last5(home_id)
            home_last5 = fixtures
            home_summary = summarize_last_fixtures(fixtures, home_id)
        if away_id:
            fixtures = get_team_last5(away_id)
            away_last5 = fixtures
            away_summary = summarize_last_fixtures(fixtures, away_id)

        enriched_item = {
            "base": m,
            "fixture_id": fixture_id,
            "home_id": home_id,
            "away_id": away_id,
            "odds": odds_info,
            "home_last5": home_last5,
            "away_last5": away_last5,
            "home_summary": home_summary,
            "away_summary": away_summary
        }
        enriched.append(enriched_item)

    return jsonify({"date": date, "matches_count": len(enriched), "matches": enriched})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
