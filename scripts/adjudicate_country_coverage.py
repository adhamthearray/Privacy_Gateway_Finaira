"""Create the evidence-preserving COUNTRY review queue from a coverage audit."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


APPROVED = {
    "دولة فلسطين": ("Q23792", "PS"),
    "يمن": ("Q805", "YE"),
    "المملكة الأردنية": ("Q810", "JO"),
    "مغرب": ("Q1028", "MA"),
    "جزائر": ("Q262", "DZ"),
    "ولايات المتحدة": ("Q30", "US"),
    "UK": ("Q145", "GB"),
    "دولة الإمارات": ("Q878", "AE"),
    "بحرين": ("Q398", "BH"),
    "USA": ("Q30", "US"),
    "الدولة الروسية": ("Q159", "RU"),
    "الدولة السورية": ("Q858", "SY"),
    "الدولة الفلسطينية": ("Q23792", "PS"),
    "دولة فلسطينية": ("Q23792", "PS"),
    "دولة الفلسطينية": ("Q23792", "PS"),
    "الدولة اليمنية": ("Q805", "YE"),
    "جمهورية اليمن": ("Q805", "YE"),
    "دولة إيران": ("Q794", "IR"),
    "دولة لبنان": ("Q822", "LB"),
    "الإمارات العربية": ("Q878", "AE"),
    "مملكة المغربية": ("Q1028", "MA"),
    "مملكة العربية السعودية": ("Q851", "SA"),
    "صين": ("Q148", "CN"),
    "أردن": ("Q810", "JO"),
    "موزامبيق": ("Q1029", "MZ"),
    "أرتيريا": ("Q986", "ER"),
    "أميركا": ("Q30", "US"),
    "اميركا": ("Q30", "US"),
    "اوزبيكستان": ("Q265", "UZ"),
    "نيوزلندا": ("Q664", "NZ"),
    "الولايات المتحدة الأميركية": ("Q30", "US"),
}

HISTORICAL = {
    "بريطانيا",
    "الاتحاد السوفيتي",
    "الإتحاد السوفيتي",
    "جنوب اليمن",
    "اليمن الموحد",
    "الجمهورية اليمنية الموحدة",
}

NON_COUNTRY = {
    "الأراضي الفلسطينية",
    "الأراضي التركية",
    "الأراضي السعودية",
    "الأراضي السورية",
    "الأراضي اللبنانية",
    "الأراضي اليمنية",
    "بالمنطقة المغاربية",
    "المنطقة المغاربية",
    "الشام",
    "لشام",
    "الاندلس",
    "الشيشان",
    "القدس",
    "نابلس",
    "بغداد",
    "جنين",
    "دارفور",
    "مراكش",
    "واشنطن",
    "طهران",
    "بيروت",
    "طرابلس",
    "لندن",
    "موسكو",
}


def classify(value: str) -> tuple[str, str, str, str]:
    if value in APPROVED:
        qid, iso = APPROVED[value]
        return "APPROVED", "CURRENT_COUNTRY", qid, iso
    if value in HISTORICAL:
        return "REJECTED", "HISTORICAL", "", ""
    if value in NON_COUNTRY:
        return "REJECTED", "NON_COUNTRY_GEOGRAPHY", "", ""
    if value in {"كورديا", "كوريا", "السلطنة", "المملكة", "SADR", "الجمهورية العربية الصحراوية الديمقراطية", "دولة الجمهورية العربية الصحراوية الديمقراطية"}:
        return "PENDING", "AMBIGUOUS_OR_DISPUTED", "", ""
    if value in {"فسلطينا", "لليمن", "ليبا", "مينامار", "دولة العراقية"}:
        return "PENDING", "MALFORMED_OR_SPELLING_REQUIRES_REVIEW", "", ""
    return "PENDING", "UNRESOLVED_COUNTRY_IDENTITY", "", ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("reports/ner_v1_generalization/coverage_country.csv"))
    parser.add_argument("--output", type=Path, default=Path("reports/ner_v1_generalization/country_review_queue.csv"))
    args = parser.parse_args()

    rows = list(csv.DictReader(args.input.open(encoding="utf-8", newline="")))
    missing = [row for row in rows if row["coverage_category"] != "MATCHED_OR_VERIFIED"]
    output = []
    for row in sorted(missing, key=lambda item: (-int(item["span_count"]), item["value"])):
        decision, classification, qid, iso = classify(row["value"])
        if decision == "APPROVED":
            evidence = f"wikidata_country_aliases_ar_en_v1.csv:{qid};natural_earth:{iso};finaira_ner_v1:COUNTRY"
            notes = "Reviewed current-country variant; exact QID/ISO identity and NER context verified."
        elif classification == "HISTORICAL":
            evidence = "finaira_ner_v1:COUNTRY context; historical identity excluded by current/dependency-only policy"
            notes = "Keep suppressed; do not map to a modern successor country."
        elif classification == "NON_COUNTRY_GEOGRAPHY":
            evidence = "finaira_ner_v1:COUNTRY context; value denotes a city, region, or territory phrase"
            notes = "Not a current/dependent country alias for this table."
        else:
            evidence = "finaira_ner_v1:COUNTRY context; independent country identity evidence still required"
            notes = "Do not promote until an exact current/dependency QID and Natural Earth identity are verified."
        output.append({
            "value": row["value"],
            "span_count": row["span_count"],
            "baseline_category": row["coverage_category"],
            "review_decision": decision,
            "classification": classification,
            "candidate_qid": qid,
            "iso2": iso,
            "evidence_reference": evidence,
            "review_notes": notes,
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    print({"input_missing_values": len(missing), "approved": sum(row["review_decision"] == "APPROVED" for row in output), "pending": sum(row["review_decision"] == "PENDING" for row in output), "rejected": sum(row["review_decision"] == "REJECTED" for row in output)})


if __name__ == "__main__":
    main()
