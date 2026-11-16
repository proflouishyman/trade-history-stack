"""Build docs/data/trade_1870_1914.db: positive flows 1870-1914 only, small enough to load in a browser."""
import os, sqlite3, sys

SRC, OUT = "trade.db", "docs/data/trade_1870_1914.db"


def main():
    if os.path.exists(OUT):
        os.remove(OUT)
    con = sqlite3.connect(OUT)
    con.execute(f"ATTACH DATABASE '{SRC}' AS big")
    con.execute("CREATE TABLE flows (exporter TEXT, importer TEXT, year INTEGER, value_gbp REAL)")
    con.execute("INSERT INTO flows SELECT exporter, importer, year, value_gbp FROM big.flows "
                "WHERE value_gbp > 0 AND year BETWEEN 1870 AND 1914")
    con.execute("CREATE TABLE countries AS SELECT * FROM big.countries")
    con.execute("CREATE INDEX idx_exp ON flows(exporter, year)")
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM flows").fetchone()[0]
    con.execute("DETACH DATABASE big"); con.execute("VACUUM"); con.close()
    size = os.path.getsize(OUT)
    print(f"{OUT}: {n:,} positive flows, {size/1e6:.2f} MB")
    if size > 10e6 or n == 0:
        raise RuntimeError("small db empty or over 10 MB")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        sys.exit(1)
