"""Evidence for "why a database instead of an Excel file". Writes results/sql_vs_excel.json.

NULL handling: NULL in value_gbp = no record (never zero). Every "positive flow"
test is value_gbp > 0, which also excludes NULL (comparisons with NULL are not true).
"""
import json, os, shutil, sqlite3, statistics, sys, tempfile, time
import pandas as pd

DB, CSV = "trade.db", "data/flows_all_years.csv.gz"
EXCEL_MAX_ROWS = 1_048_576

QUERIES = {
    "a_gbr_top10_export_destinations_1913": (
        "Britain's (GBR) top 10 export destinations in 1913",
        """SELECT importer, ROUND(value_gbp) AS gbp FROM flows
WHERE exporter = 'GBR' AND year = 1913 AND value_gbp > 0
ORDER BY value_gbp DESC LIMIT 10"""),
    "b_trade_by_importer_region_1913": (
        "JOIN with countries: total 1913 trade by importing region",
        """SELECT c.region, ROUND(SUM(f.value_gbp)) AS total_gbp, COUNT(*) AS n_flows
FROM flows f JOIN countries c ON c.iso = f.importer
WHERE f.year = 1913 AND f.value_gbp > 0
GROUP BY c.region ORDER BY total_gbp DESC"""),
    "c_positive_flows_per_decade": (
        "GROUP BY decade: number of recorded positive flows",
        """SELECT (year / 10) * 10 AS decade, COUNT(*) AS positive_flows FROM flows
WHERE value_gbp > 0 GROUP BY decade ORDER BY decade"""),
    "d_pairs_trade_fell_over_half_1913_to_1920": (
        "Self-join: every exporter-importer pair whose trade fell by more than 50% from 1913 to 1920 (count, then the 10 largest falls)",
        """SELECT a.exporter, a.importer, ROUND(a.value_gbp) AS gbp_1913,
       ROUND(b.value_gbp) AS gbp_1920, ROUND(a.value_gbp - b.value_gbp) AS fall
FROM flows a JOIN flows b
  ON a.exporter = b.exporter AND a.importer = b.importer
WHERE a.year = 1913 AND b.year = 1920
  AND a.value_gbp > 0 AND b.value_gbp < 0.5 * a.value_gbp
ORDER BY fall DESC LIMIT 10"""),
    "e_gbr_export_partners_new_since_1870": (
        "Partners Britain exported to in 1913 but had no positive recorded flow to in 1870 (NULL or 0)",
        """SELECT importer, ROUND(value_gbp) AS gbp_1913 FROM flows
WHERE exporter = 'GBR' AND year = 1913 AND value_gbp > 0
  AND importer NOT IN (SELECT importer FROM flows
                       WHERE exporter = 'GBR' AND year = 1870 AND value_gbp > 0)
ORDER BY value_gbp DESC"""),
}
COUNT_D = """SELECT COUNT(*) FROM flows a JOIN flows b
ON a.exporter = b.exporter AND a.importer = b.importer
WHERE a.year = 1913 AND b.year = 1920 AND a.value_gbp > 0 AND b.value_gbp < 0.5 * a.value_gbp"""

# The query used for the index timing demo: one country, one year, out of 2.5 million rows
TIMED_SQL = "SELECT importer, value_gbp FROM flows WHERE exporter = 'GBR' AND year = 1913 AND value_gbp > 0 ORDER BY value_gbp DESC LIMIT 10"


def run(con, sql):
    """Execute sql and return {columns, rows}."""
    cur = con.execute(sql)
    return {"columns": [d[0] for d in cur.description], "rows": [list(r) for r in cur.fetchall()]}


def median_ms(fn, repeats=5):
    """Median wall-clock milliseconds of fn() over several runs."""
    times = []
    for _ in range(repeats):
        t = time.perf_counter(); fn(); times.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(times), 2)


def index_timing():
    """Time TIMED_SQL on a temporary copy of the db with and without the indexes."""
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "copy.db")
    shutil.copy(DB, path)
    con = sqlite3.connect(path)
    con.execute("DROP INDEX idx_exp"); con.execute("DROP INDEX idx_imp"); con.commit()
    without = median_ms(lambda: con.execute(TIMED_SQL).fetchall())
    con.execute("CREATE INDEX idx_exp ON flows(exporter, year)"); con.commit()
    with_idx = median_ms(lambda: con.execute(TIMED_SQL).fetchall())
    con.close(); shutil.rmtree(tmp)
    return {"sql": TIMED_SQL, "ms_without_index": without, "ms_with_index": with_idx,
            "speedup_x": round(without / with_idx, 1), "method": "median of 5 runs, temp copy of trade.db"}


def pandas_equivalent():
    """Query (a) in pandas; load time and query time are reported separately."""
    t = time.perf_counter(); df = pd.read_csv(CSV); load_ms = (time.perf_counter() - t) * 1000
    code = ("df[(df.iso_o == 'GBR') & (df.year == 1913) & (df.FLOW > 0)]"
            ".nlargest(10, 'FLOW')[['iso_d', 'FLOW']]")
    q_ms = median_ms(lambda: eval(code, {"df": df}))
    return {"code": code, "load_csv_ms": round(load_ms), "query_ms": q_ms,
            "rows": eval(code, {"df": df}).round(0).values.tolist(),
            "note": "pandas must read all 2.5M rows into memory first; SQLite reads only what the index points to"}


def main():
    con = sqlite3.connect(DB)
    total = con.execute("SELECT COUNT(*) FROM flows").fetchone()[0]
    nulls = con.execute("SELECT COUNT(*) FROM flows WHERE value_gbp IS NULL").fetchone()[0]
    zeros = con.execute("SELECT COUNT(*) FROM flows WHERE value_gbp = 0").fetchone()[0]
    pos = con.execute("SELECT COUNT(*) FROM flows WHERE value_gbp > 0").fetchone()[0]
    out = {
        "about": "Evidence for slides: why SQL instead of an Excel file. Source: TRADHIST v4 (Fouquin & Hugot 2016). NULL = no record, never zero.",
        "size_vs_excel": {
            "source_rows": total, "excel_row_limit": EXCEL_MAX_ROWS,
            "rows_over_limit": total - EXCEL_MAX_ROWS,
            "times_the_limit": round(total / EXCEL_MAX_ROWS, 2),
            "rows_null_no_record": nulls, "rows_zero_reported_nil": zeros, "rows_positive": pos,
            "csv_gz_bytes": os.path.getsize(CSV), "trade_db_bytes": os.path.getsize(DB),
            "csv_gz_mb": round(os.path.getsize(CSV) / 1e6, 1), "trade_db_mb": round(os.path.getsize(DB) / 1e6, 1)},
        "queries": {},
    }
    for key, (question, sql) in QUERIES.items():
        t = time.perf_counter()
        res = run(con, sql)
        out["queries"][key] = {"question": question, "sql": sql, "ms": round((time.perf_counter() - t) * 1000, 1), **res}
    out["queries"]["d_pairs_trade_fell_over_half_1913_to_1920"]["total_pairs_matching"] = con.execute(COUNT_D).fetchone()[0]
    out["index_timing"] = index_timing()
    out["pandas_equivalent_of_query_a"] = pandas_equivalent()
    os.makedirs("results", exist_ok=True)
    with open("results/sql_vs_excel.json", "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        sys.exit(1)
