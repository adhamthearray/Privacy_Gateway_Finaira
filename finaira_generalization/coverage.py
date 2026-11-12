from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .db import make_engine, GeneralizationScheme, GeneralizationLevel, GeneralizationCandidate

def candidate_coverage(db_path="data/processed/finaira_generalization.db", report_path="reports/candidate_coverage.md"):
    with Session(make_engine(db_path)) as s:
        schemes=s.scalars(select(GeneralizationScheme)).all(); lines=["# Candidate coverage",""]
        for sc in schemes:
            levels=s.scalars(select(GeneralizationLevel).where(GeneralizationLevel.scheme_id==sc.scheme_id).order_by(GeneralizationLevel.specificity_rank)).all()
            lines.append(f"## {sc.entity_type} / {sc.scheme_id}")
            for level in levels:
                count=s.scalar(select(func.count()).select_from(GeneralizationCandidate).where(GeneralizationCandidate.scheme_id==sc.scheme_id,GeneralizationCandidate.level_id==level.level_id))
                if sc.entity_type in {"AGE","DATE"} or sc.scheme_id == "NATIONALITY_NATURAL_EARTH":
                    lines.append(f"- {level.specificity_rank} `{level.level_code}`: dynamic/value-dependent (stored rule level; not pre-materialized)")
                else:
                    lines.append(f"- {level.specificity_rank} `{level.level_code}`: {count}")
            lines.append("")
    Path(report_path).write_text("\n".join(lines),encoding="utf-8")
