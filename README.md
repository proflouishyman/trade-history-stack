# Trade history stack

The same historical trade data served three ways, for the "full stack" lecture.
Data: bilateral trade 1827-2014, 2,495,357 rows (exporter, importer, year, value in nominal current British pounds).

| Mode | What runs | Files |
|---|---|---|
| 1. Server | Flask answers `/api/country/<ISO>` from a SQLite database | `build_db.py`, `app.py` |
| 2. Static | The same JSON pre-written to files; any web host works (GitHub Pages) | `export_static.py`, `docs/` |
| 3. In the browser | SQLite compiled to WebAssembly (sql.js) queries a small db file, no server | `build_small_db.py`, `docs/sqljs.html` |

## Files
- `data/flows_all_years.csv.gz` - the source data (redistributed with attribution, see below)
- `build_db.py` - csv.gz to `trade.db` (SQLite, gitignored). Fails loudly on a wrong row count, duplicate (exporter, importer, year), or a region conflict
- `sql_vs_excel.py` - writes `results/sql_vs_excel.json`: row count vs Excel's 1,048,576 limit, file sizes, five example queries with SQL and results, index timing, pandas comparison. Every number on the slides comes from this file
- `app.py` - Flask app; `country_json(iso)` is the one query function
- `export_static.py` - imports `country_json` from `app.py` and writes `docs/data/<ISO>.json` and `docs/data/countries.json`
- `docs/index.html`, `docs/app.js` - the page: country dropdown, year slider, two bar charts, a line chart (Chart.js 4.4.1). One line in `app.js` picks Flask or static data
- `docs/sqljs.html` - SQL box running in the browser (sql.js 1.10.3)
- `build_small_db.py` - writes `docs/data/trade_1870_1914.db` (positive flows 1870-1914 only)
- `screenshots/` - images of each mode

## Run it
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python build_db.py            # about 5 s, makes trade.db
python sql_vs_excel.py        # results/sql_vs_excel.json
python export_static.py       # docs/data/*.json
python build_small_db.py      # docs/data/trade_1870_1914.db
```
Mode 1: `python app.py`, open http://localhost:5001/ (port 5001, because macOS AirPlay Receiver occupies 5000).
Modes 2 and 3: `cd docs && python -m http.server 8000`, open http://localhost:8000/ and http://localhost:8000/sqljs.html.
The charts load Chart.js and sql.js from cdnjs, so an internet connection is needed.

## Data contract
`flows(exporter TEXT, importer TEXT, year INTEGER, value_gbp REAL)`: one row per (exporter, importer, year). `value_gbp` is nominal current GBP.
**NULL = no record (never zero). 0 = reported nil.** "Positive flow" always means `value_gbp > 0`.
`countries(iso TEXT PRIMARY KEY, name TEXT NULL, region TEXT)`: 319 codes. `name` is NULL for all rows: the source file (`TRADHIST_v4.dta`) has no country-name column, and names are not invented. Codes include non-sovereign entities (e.g. GBRIND, ZOLL, USSR).

JSON returned by `/api/country/<ISO>` and stored in `docs/data/<ISO>.json` (byte-identical):
```
{"iso": "GBR", "name": null, "region": "NWEUR",
 "years": {"1913": {"exports": [["GBRIND", 78388150.0], ...], "imports": [[partner_iso, value_gbp], ...]}, ...},
 "note": "...", "source": "..."}
```
- `years`: only years with at least one positive flow. Per year, at most 10 export partners and 10 import partners, largest first. This keeps `docs/data` near 8 MB; the `note` field says so.
- `name`: string or null. Unknown ISO gives HTTP 404 `{"error": ...}`.
- `docs/data/countries.json`: `[{"iso", "name", "region", "n_years"}, ...]`.

## Attribution and licence
Fouquin, M. and Hugot, J. (2016) *Two Centuries of Bilateral Trade and Gravity Data: 1827-2014*. CEPII Working Paper 2016-14. Dataset TRADHIST v4, https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=32 .
Licence: Etalab Open Licence 2.0, which permits redistribution with attribution. The data here is a derived extract (selected columns), not modified in value.
Caveats: nominal current pounds (not inflation-adjusted); entities are not all sovereign states; each directed pair is a single value, with importer reports preferred where available (see the working paper).
