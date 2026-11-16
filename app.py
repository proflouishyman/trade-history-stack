"""Mode 1: a Flask server (port 5001). /api/country/<iso> answers from trade.db; / serves docs/."""
import sqlite3
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__, static_folder="docs", static_url_path="")
app.json.sort_keys = False   # keep key order identical to the static files
TOP_N = 10
NOTE = f"Per year, top {TOP_N} export partners and top {TOP_N} import partners; positive flows only (NULL and 0 excluded). Values: nominal current GBP."
SOURCE = "Fouquin & Hugot (2016), TRADHIST v4, CEPII WP 2016-14, Etalab 2.0"


def top_partners(con, iso, column, partner):
    """Return {year: [[partner_iso, value_gbp], ...]} for the top N positive flows.
    `column` and `partner` are fixed strings chosen by our code, never user input;
    the user's `iso` is passed as a ? parameter so it can never be run as SQL."""
    rows = con.execute(
        f"SELECT year, {partner}, value_gbp FROM flows "
        f"WHERE {column} = ? AND value_gbp > 0 ORDER BY year, value_gbp DESC", (iso,))
    out = {}
    for year, other, value in rows:
        year_list = out.setdefault(str(year), [])
        if len(year_list) < TOP_N:
            year_list.append([other, value])
    return out


def country_json(iso, con=None):
    """Build the JSON-ready dict for one country, or None if the code is unknown."""
    con = con or sqlite3.connect("trade.db")
    row = con.execute("SELECT name, region FROM countries WHERE iso = ?", (iso,)).fetchone()
    if row is None:
        return None
    exports = top_partners(con, iso, "exporter", "importer")
    imports = top_partners(con, iso, "importer", "exporter")
    years = sorted(set(exports) | set(imports))
    return {"iso": iso, "name": row[0], "region": row[1], "note": NOTE, "source": SOURCE,
            "years": {y: {"exports": exports.get(y, []), "imports": imports.get(y, [])} for y in years}}


@app.route("/api/country/<iso>")
def api_country(iso):
    data = country_json(iso)
    return (jsonify(data), 200) if data else (jsonify({"error": f"unknown iso {iso}"}), 404)


@app.route("/")
def home():
    return send_from_directory("docs", "index.html")


if __name__ == "__main__":
    app.run(port=5001)   # not 5000: macOS AirPlay Receiver already uses it
