"""Mode 2: write the same JSON as the Flask API to docs/data/, for hosting on GitHub Pages."""
import json, os, sqlite3, sys
from app import country_json   # the very same function the Flask route uses

OUT = "docs/data"


def main():
    con = sqlite3.connect("trade.db")
    codes = [r[0] for r in con.execute("SELECT iso FROM countries ORDER BY iso")]
    os.makedirs(OUT, exist_ok=True)
    listing, empty = [], []
    for iso in codes:
        data = country_json(iso, con)
        if data is None:
            raise RuntimeError(f"country {iso} listed but no data returned")
        if not data["years"]:
            empty.append(iso)   # counted and reported, still written
        with open(f"{OUT}/{iso}.json", "w") as f:
            json.dump(data, f, separators=(",", ":"))
            f.write("\n")   # Flask ends its JSON with a newline; match it byte for byte
        listing.append({"iso": iso, "name": data["name"], "region": data["region"],
                        "n_years": len(data["years"])})
    with open(f"{OUT}/countries.json", "w") as f:
        json.dump(listing, f, separators=(",", ":"))
    size = sum(os.path.getsize(f"{OUT}/{n}") for n in os.listdir(OUT) if n.endswith(".json"))
    print(f"wrote {len(codes)} country files + countries.json; {size/1e6:.1f} MB")
    print(f"{len(empty)} countries with no positive flows in any year: {empty}")
    if size > 25e6:
        raise RuntimeError(f"docs/data is {size/1e6:.1f} MB, over the 25 MB budget")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        sys.exit(1)
