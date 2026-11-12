from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2
from sqlalchemy import inspect, text
from .db import make_engine, init_db

ROOT=Path(__file__).resolve().parents[1]

def table_snapshot(db_path):
    e=make_engine(db_path); i=inspect(e); rows=[]
    with e.connect() as c:
        for t in i.get_table_names(): rows.append((t,c.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()))
    return rows

def schema_markdown(db_path, title="Schema"):
    e=make_engine(db_path); i=inspect(e); lines=[f"# {title}",""]
    with e.connect() as c:
        for t in i.get_table_names():
            lines += [f"## `{t}`", "", f"Rows: {c.execute(text(f'SELECT COUNT(*) FROM \"{t}\"')).scalar()}", "", "| Column | Type | Key | Nullable | References | Purpose |", "|---|---|---|---|---|---|"]
            fks={x['constrained_columns'][0]:f"{x['referred_table']}.{x['referred_columns'][0]}" for x in i.get_foreign_keys(t) if x.get('constrained_columns')}
            pk=set(i.get_pk_constraint(t).get('constrained_columns') or [])
            purpose=f"Persisted Finaira reference data or layered metadata for `{t}`."
            for col in i.get_columns(t): lines.append(f"| {col['name']} | {col['type']} | {'PK' if col['name'] in pk else ''} | {'YES' if col['nullable'] else 'NO'} | {fks.get(col['name'],'')} | {purpose} |")
            idx=[x['name'] for x in i.get_indexes(t)]
            if idx: lines += ["", "Indexes: "+", ".join(idx)]
            lines.append("")
    return "\n".join(lines)

def export_sql(db_path, out_path):
    e=make_engine(db_path); lines=["-- Exported from SQLite sqlite_master", "PRAGMA foreign_keys=ON;", ""]
    with e.connect() as c:
        rows=c.execute(text("SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END, name")).all()
        for typ,name,sql in rows: lines.extend([f"-- {typ}: {name}",sql+";",""])
    Path(out_path).write_text("\n".join(lines),encoding="utf-8")

def export_erd(db_path,out_path):
    i=inspect(make_engine(db_path)); lines=["erDiagram"]
    for t in i.get_table_names():
        lines.append(f"    {t} {{")
        pk=set(i.get_pk_constraint(t).get('constrained_columns') or [])
        for c in i.get_columns(t): lines.append(f"        {str(c['type']).replace(' ','_')} {c['name']} {'PK' if c['name'] in pk else ''}".rstrip())
        lines.append("    }")
    for t in i.get_table_names():
        for fk in i.get_foreign_keys(t):
            if fk.get('referred_table'):
                lines.append(f"    {fk['referred_table']} ||--o{{ {t} : \"{fk['constrained_columns'][0]}\"")
    Path(out_path).write_text("\n".join(lines)+"\n",encoding="utf-8")

def migrate_layered(db_path="data/processed/finaira_generalization.db", report_dir="reports"):
    db=Path(db_path); report=Path(report_dir); report.mkdir(parents=True,exist_ok=True)
    before=schema_markdown(db,"Schema before layered migration") if db.exists() else "# Schema before layered migration\n\nDatabase did not exist."
    (report/"schema_before.md").write_text(before,encoding="utf-8")
    backup=db.with_name(f"{db.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{db.suffix}")
    if db.exists(): copy2(db,backup)
    init_db(db)
    (report/"migration_report.md").write_text(f"# Layered migration\n\n- Backup: `{backup}`\n- Applied: {datetime.now(timezone.utc).isoformat()}\n- Strategy: additive SQLAlchemy `create_all`; existing imported tables were preserved.\n",encoding="utf-8")
    return backup

def generate_schema_reports(db_path="data/processed/finaira_generalization.db", report_dir="reports"):
    report=Path(report_dir); report.mkdir(parents=True,exist_ok=True)
    (report/"schema_after.md").write_text(schema_markdown(db_path,"Schema after layered migration"),encoding="utf-8")
    export_sql(db_path,report/"database_schema.sql")
    export_erd(db_path,report/"database_erd.mmd")

def generate_gap_reports(db_path="data/processed/finaira_generalization.db", report_dir="reports"):
    """Write factual missing-data reports from the current database."""
    from sqlalchemy.orm import Session
    from .db import Occupation, Country, GeneralizationCandidate, GeneralizationScheme, NaturalEarthCountry, NationalityGeoJoin, Bank, Organization, GovernmentEntity
    report=Path(report_dir); report.mkdir(parents=True,exist_ok=True)
    with Session(make_engine(db_path)) as s:
        missing_t=["table,record_key,language,reason"]
        for o in s.query(Occupation).all():
            if not o.label_ar: missing_t.append(f"occupations,{o.occupation_id},ar,MISSING_TRANSLATION")
            if not o.label_en: missing_t.append(f"occupations,{o.occupation_id},en,MISSING_TRANSLATION")
        for c in s.query(Country).all():
            if not c.country_ar: missing_t.append(f"countries,{c.iso2},ar,MISSING_TRANSLATION")
            if not c.country_en: missing_t.append(f"countries,{c.iso2},en,MISSING_TRANSLATION")
            if not c.subregion_en: missing_t.append(f"countries,{c.iso2},en,MISSING_SUBREGION_TRANSLATION")
            if not c.region_en: missing_t.append(f"countries,{c.iso2},en,MISSING_REGION_TRANSLATION")
        for c in s.query(NaturalEarthCountry).all():
            if not c.name_ar: missing_t.append(f"natural_earth_countries,{c.natural_earth_id},ar,MISSING_TRANSLATION")
        for b in s.query(Bank).all():
            if not b.name_ar: missing_t.append(f"banks,{b.bank_id},ar,MASTER_ARABIC_NAME_UNRESOLVED")
        (report/"missing_translations.csv").write_text("\n".join(missing_t)+"\n",encoding="utf-8")
        missing_m=["entity_type,record_key,reason"]
        for c in s.query(GeneralizationCandidate).all():
            if c.review_status not in {"OFFICIAL","REVIEWED"}: missing_m.append(f"unknown,{c.candidate_id},UNVERIFIED")
        for j in s.query(NationalityGeoJoin).all():
            if j.join_status not in {"MATCHED_QID","MATCHED_ISO"}: missing_m.append(f"NATIONALITY,{j.country_qid},{j.join_status}")
        for o in s.query(Organization).all():
            if o.identity_verification_status not in {"VERIFIED","APPROVED","OFFICIAL"}: missing_m.append(f"ORGANIZATION,{o.organization_qid},PENDING_IDENTITY_VALIDATION")
        for g in s.query(GovernmentEntity).all():
            if g.identity_verification_status not in {"VERIFIED","APPROVED","OFFICIAL"}: missing_m.append(f"GOVERNMENT_ENTITY,{g.entity_id},REVIEW_REQUIRED")
        (report/"missing_mappings.csv").write_text("\n".join(missing_m)+"\n",encoding="utf-8")
