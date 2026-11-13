"""Fetch verified Arabic/English Wikidata demonyms for Natural Earth countries.

This is an offline-build step. Runtime lookup never calls Wikidata. Only
Wikidata P1549 values are exported; country names are not fabricated into
demonym aliases.
"""

from __future__ import annotations

import csv
import argparse
import json
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NE_CSV = ROOT / "data/sources/natural_earth/ne_10m_admin_0_countries_v5.1.1.csv"
DEFAULT_LEGACY_ALIAS_CSV = Path.home() / "Downloads" / "Finaira_Generalization_DB_Codex_Handoff_2026-11-12_ext" / "inputs/nationality/wikidata_nationality_aliases.csv"
OUT_DIR = ROOT / "data/sources/wikidata"
ALIAS_CSV = OUT_DIR / "wikidata_nationality_aliases_ar_en_v2.csv"
COVERAGE_CSV = OUT_DIR / "wikidata_nationality_coverage_v2.csv"
ENDPOINT = "https://query.wikidata.org/sparql"


def query(qids: list[str]) -> list[dict[str, str]]:
    values = " ".join(f"wd:{qid}" for qid in qids)
    sparql = f'''
SELECT ?country ?nationality WHERE {{
  VALUES ?country {{ {values} }}
  ?country wdt:P1549 ?nationality .
  FILTER(LANG(?nationality) IN ("ar", "en"))
}}
'''
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": sparql, "format": "json"})
    request = urllib.request.Request(url, headers={"User-Agent": "Finaira-GeneralizationDB/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = json.load(response)
    output = []
    for item in payload["results"]["bindings"]:
        output.append({
            "qid": item["country"]["value"].rsplit("/", 1)[-1],
            "nationality": item["nationality"]["value"],
            "language": item["nationality"].get("xml:lang", "").lower(),
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-alias", type=Path, default=DEFAULT_LEGACY_ALIAS_CSV)
    args = parser.parse_args()
    with NE_CSV.open(encoding="utf-8-sig", newline="") as handle:
        countries = list(csv.DictReader(handle))
    qids = sorted({row["wikidata_qid"] for row in countries if row.get("wikidata_qid", "").startswith("Q")})
    fetched: list[dict[str, str]] = []
    for offset in range(0, len(qids), 40):
        fetched.extend(query(qids[offset : offset + 40]))
        if offset + 40 < len(qids):
            time.sleep(0.5)

    by_qid = {row["wikidata_qid"]: row for row in countries if row.get("wikidata_qid", "").startswith("Q")}
    # Preserve the supplied handoff aliases and overlay the current Wikidata
    # P1549 response. This keeps previously supplied evidence auditable while
    # adding newly available verified forms.
    aliases_by_key: dict[tuple[str, str, str], dict[str, str]] = {}
    if args.legacy_alias.exists():
        with args.legacy_alias.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                qid = row.get("country", "").rsplit("/", 1)[-1]
                language = row.get("language", "").lower()
                nationality = row.get("nationality", "")
                if qid.startswith("Q") and language in {"ar", "en"} and nationality:
                    aliases_by_key[(qid, language, nationality)] = {
                        "country": f"http://www.wikidata.org/entity/{qid}",
                        "countryLabel": row.get("countryLabel", ""),
                        "iso2": row.get("iso2", ""),
                        "nationality": nationality,
                        "language": language,
                        "source_property": "wdt:P1549:handoff",
                    }
    for row in fetched:
        key = (row["qid"], row["language"], row["nationality"])
        if row["language"] not in {"ar", "en"} or row["qid"] not in by_qid:
            continue
        country = by_qid[row["qid"]]
        aliases_by_key[key] = {
            "country": f"http://www.wikidata.org/entity/{row['qid']}",
            "countryLabel": country.get("name_en", ""),
            "iso2": country.get("iso_a2", ""),
            "nationality": row["nationality"],
            "language": row["language"],
            "source_property": "wdt:P1549",
        }
    aliases = list(aliases_by_key.values())
    aliases.sort(key=lambda row: (row["country"], row["language"], row["nationality"]))

    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in aliases:
        counts[row["country"].rsplit("/", 1)[-1]][row["language"]] += 1
    coverage = []
    for country in sorted(countries, key=lambda row: row["natural_earth_id"]):
        qid = country.get("wikidata_qid", "")
        count = counts.get(qid, Counter())
        coverage.append({
            "natural_earth_id": country.get("natural_earth_id", ""),
            "wikidata_qid": qid,
            "iso_a2": country.get("iso_a2", ""),
            "name_en": country.get("name_en", ""),
            "name_ar": country.get("name_ar", ""),
            "ar_alias_count": count["ar"],
            "en_alias_count": count["en"],
            "alias_status": "ALIASES_AVAILABLE" if count else "NO_VERIFIED_AR_EN_DEMONYM",
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with ALIAS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(aliases[0]))
        writer.writeheader()
        writer.writerows(aliases)
    with COVERAGE_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(coverage[0]))
        writer.writeheader()
        writer.writerows(coverage)
    print(json.dumps({"natural_earth_countries": len(countries), "wikidata_qids": len(qids), "aliases": len(aliases), "countries_with_aliases": sum(1 for row in coverage if row["alias_status"] == "ALIASES_AVAILABLE"), "countries_without_verified_ar_en_demonym": sum(1 for row in coverage if row["alias_status"] != "ALIASES_AVAILABLE"), "alias_csv": str(ALIAS_CSV), "coverage_csv": str(COVERAGE_CSV)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
