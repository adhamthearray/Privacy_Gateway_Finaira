"""Small stdlib-only reader for the official Natural Earth DBF distribution."""

from __future__ import annotations

import csv
import struct
import zipfile
from pathlib import Path

REQUIRED_FIELDS = {
    "NE_ID",
    "WIKIDATAID",
    "ISO_A2",
    "NAME_EN",
    "NAME_AR",
    "SUBREGION",
    "REGION_UN",
    "CONTINENT",
}
OUTPUT_FIELDS = [
    "natural_earth_id",
    "wikidata_qid",
    "iso_a2",
    "name_en",
    "name_ar",
    "subregion",
    "region_un",
    "continent",
    "adm0_a3",
]


def _read_dbf(raw: bytes) -> list[dict[str, str]]:
    record_count = struct.unpack_from("<I", raw, 4)[0]
    header_length = struct.unpack_from("<H", raw, 8)[0]
    record_length = struct.unpack_from("<H", raw, 10)[0]
    fields: list[tuple[str, int]] = []
    offset = 32
    while raw[offset] != 0x0D:
        name = raw[offset : offset + 11].split(b"\0", 1)[0].decode("ascii")
        fields.append((name, raw[offset + 16]))
        offset += 32
    rows: list[dict[str, str]] = []
    for index in range(record_count):
        record = raw[header_length + index * record_length : header_length + (index + 1) * record_length]
        if not record or record[0:1] == b"*":
            continue
        cursor = 1
        row: dict[str, str] = {}
        for name, width in fields:
            value = record[cursor : cursor + width]
            cursor += width
            row[name] = value.decode("utf-8", errors="replace").strip(" \x00")
        rows.append(row)
    return rows


def read_natural_earth_dbf(zip_path: str | Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(zip_path) as archive:
        dbf_names = [name for name in archive.namelist() if name.lower().endswith(".dbf")]
        if len(dbf_names) != 1:
            raise ValueError(f"NATURAL_EARTH_DBf_COUNT:{len(dbf_names)}")
        rows = _read_dbf(archive.read(dbf_names[0]))
    if len(rows) != 258:
        raise ValueError(f"NATURAL_EARTH_ROW_COUNT:{len(rows)}")
    missing = REQUIRED_FIELDS.difference(rows[0])
    if missing:
        raise ValueError(f"NATURAL_EARTH_REQUIRED_FIELDS_MISSING:{','.join(sorted(missing))}")
    return rows


def extract_natural_earth_csv(zip_path: str | Path, csv_path: str | Path) -> dict[str, int | str]:
    rows = read_natural_earth_dbf(zip_path)
    output = Path(csv_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "natural_earth_id": row["NE_ID"],
                    "wikidata_qid": row["WIKIDATAID"],
                    "iso_a2": row["ISO_A2"].upper() if row["ISO_A2"] not in {"", "-99"} else "",
                    "name_en": row["NAME_EN"] or row["NAME"],
                    "name_ar": row["NAME_AR"],
                    "subregion": row["SUBREGION"],
                    "region_un": row["REGION_UN"],
                    "continent": row["CONTINENT"],
                    "adm0_a3": row["ADM0_A3"],
                }
            )
    return {"rows": len(rows), "columns": len(OUTPUT_FIELDS), "path": str(output)}
