"""Load the TRADHIST csv.gz into a SQLite database, trade.db.

Tables
  flows(exporter, importer, year, value_gbp)  value_gbp is NULL when no record exists
  countries(iso PRIMARY KEY, name, region)    name is NULL: the source file has no names
Any contract violation raises, so the script exits non-zero.
"""
import sqlite3, sys
import pandas as pd

CSV = "data/flows_all_years.csv.gz"
DB = "trade.db"
EXPECTED_ROWS = 2_495_357   # row count documented for the source file


def load_flows():
    """Read the csv as-is (original TRADHIST column names)."""
    return pd.read_csv(CSV)


def build_countries(df):
    """One row per ISO code, region taken from the exporter and importer columns.
    Raises if a code appears with two different regions."""
    a = df[["iso_o", "REGIO_o"]].set_axis(["iso", "region"], axis=1)
    b = df[["iso_d", "REGIO_d"]].set_axis(["iso", "region"], axis=1)
    pairs = pd.concat([a, b]).drop_duplicates()
    conflicts = pairs[pairs.duplicated("iso", keep=False)]
    if len(conflicts):
        raise ValueError(f"region conflict for iso codes:\n{conflicts.sort_values('iso')}")
    pairs["name"] = None   # no name column in TRADHIST_v4.dta: codes only, never invented
    return pairs[["iso", "name", "region"]].sort_values("iso")


def main():
    df = load_flows()
    if len(df) != EXPECTED_ROWS:
        raise ValueError(f"row count {len(df)} != expected {EXPECTED_ROWS}")
    dups = df.duplicated(["iso_o", "iso_d", "year"]).sum()
    if dups:
        raise ValueError(f"{dups} duplicate (exporter, importer, year) rows")
    countries = build_countries(df)

    import os
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE flows (exporter TEXT, importer TEXT, year INTEGER, value_gbp REAL)")
    con.execute("CREATE TABLE countries (iso TEXT PRIMARY KEY, name TEXT NULL, region TEXT)")
    # NaN becomes NULL: convert to object so None is written
    flows = df[["iso_o", "iso_d", "year", "FLOW"]]
    flows = flows.astype({"FLOW": "object"}).where(flows.notna(), None)
    con.executemany("INSERT INTO flows VALUES (?,?,?,?)", flows.itertuples(index=False, name=None))
    con.executemany("INSERT INTO countries VALUES (?,?,?)", countries.itertuples(index=False, name=None))
    con.execute("CREATE INDEX idx_exp ON flows(exporter, year)")
    con.execute("CREATE INDEX idx_imp ON flows(importer, year)")
    con.commit()

    n = con.execute("SELECT COUNT(*) FROM flows").fetchone()[0]
    if n != EXPECTED_ROWS:
        raise ValueError(f"database holds {n} rows, expected {EXPECTED_ROWS}")
    nulls = con.execute("SELECT COUNT(*) FROM flows WHERE value_gbp IS NULL").fetchone()[0]
    print(f"flows: {n:,} rows ({nulls:,} NULL = no record); countries: {len(countries)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        sys.exit(1)
