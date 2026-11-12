import argparse, json, sys
from .build import build_database, ROOT
from .db import init_db
from .engine import Generalizer
from .layers import generate_levels
from .schema_tools import migrate_layered, generate_schema_reports, generate_gap_reports, table_snapshot
from .coverage import candidate_coverage
from .candidates import GeneralizationDB
from .handoff import import_handoff, DEFAULT_HANDOFF
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session
from .db import make_engine, GeneralizationScheme, GeneralizationLevel, GeneralizationCandidate

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("init-db"); sub.add_parser("import-all"); sub.add_parser("inspect-datasets"); sub.add_parser("validate"); sub.add_parser("coverage")
    sub.add_parser("migrate-layered"); sub.add_parser("generate-levels"); sub.add_parser("validate-levels"); sub.add_parser("candidate-coverage"); sub.add_parser("show-schema")
    h=sub.add_parser("import-handoff"); h.add_argument("--handoff",default=str(DEFAULT_HANDOFF)); h.add_argument("--db",default=str(ROOT/"data/processed/finaira_generalization.db")); h.add_argument("--no-backup",action="store_true")
    g=sub.add_parser("generalize"); g.add_argument("--type",required=True); g.add_argument("--value",required=True); g.add_argument("--language",default="en"); g.add_argument("--level"); g.add_argument("--db",default=str(ROOT/"data/processed/finaira_generalization.db"))
    c=sub.add_parser("candidates"); c.add_argument("--type",required=True); c.add_argument("--value",required=True); c.add_argument("--language",default="en"); c.add_argument("--db",default=str(ROOT/"data/processed/finaira_generalization.db")); c.add_argument("--date-format")
    a=p.parse_args()
    if a.cmd=="init-db": init_db(ROOT/"data/processed/finaira_generalization.db"); print("initialized"); return
    if a.cmd=="import-all": print(json.dumps(build_database(),ensure_ascii=False,indent=2)); return
    if a.cmd=="migrate-layered": print(f"backup: {migrate_layered()}"); return
    if a.cmd=="import-handoff":
        print(json.dumps(import_handoff(a.db, a.handoff, ROOT/"reports", backup=not a.no_backup),ensure_ascii=False,indent=2)); return
    if a.cmd=="generate-levels": print(json.dumps(generate_levels(),ensure_ascii=False,indent=2)); generate_schema_reports(); generate_gap_reports(); candidate_coverage(); return
    if a.cmd=="candidate-coverage": candidate_coverage(); print((ROOT/"reports/candidate_coverage.md").read_text(encoding="utf-8")); return
    if a.cmd=="validate-levels":
        with Session(make_engine(ROOT/"data/processed/finaira_generalization.db")) as s:
            errors=[]
            for sc in s.scalars(select(GeneralizationScheme)).all():
                lv=s.scalars(select(GeneralizationLevel).where(GeneralizationLevel.scheme_id==sc.scheme_id)).all()
                if len({x.specificity_rank for x in lv})!=len(lv): errors.append(f"DUPLICATE_RANK:{sc.scheme_id}")
                for c in s.scalars(select(GeneralizationCandidate).where(GeneralizationCandidate.scheme_id==sc.scheme_id)).all():
                    seen=set(); cur=c
                    while cur.parent_candidate_id:
                        if cur.candidate_id in seen: errors.append(f"CYCLE:{c.candidate_id}"); break
                        seen.add(cur.candidate_id); cur=s.get(GeneralizationCandidate,cur.parent_candidate_id)
                        if cur is None: errors.append(f"MISSING_PARENT:{c.candidate_id}"); break
            print(json.dumps({"status":"PASS" if not errors else "FAIL","errors":errors},ensure_ascii=False,indent=2)); return
    if a.cmd=="show-schema":
        e=make_engine(ROOT/"data/processed/finaira_generalization.db"); i=inspect(e)
        with e.connect() as conn:
            for t in i.get_table_names():
                print(f"TABLE {t} rows={conn.exec_driver_sql(f'SELECT COUNT(*) FROM \"{t}\"').scalar()}")
                print("  columns:", ", ".join(x['name']+":"+str(x['type']) for x in i.get_columns(t)))
                for fk in i.get_foreign_keys(t): print("  fk:",fk['constrained_columns'],"->",fk['referred_table'],fk['referred_columns'])
        return
    if a.cmd in {"inspect-datasets","validate","coverage"}: print((ROOT/"reports"/("import_report.md" if a.cmd=="inspect-datasets" else "coverage_report.md")).read_text(encoding="utf-8") if (ROOT/"reports").exists() else "Run import-all first"); return
    if a.cmd=="candidates":
        sys.stdout.reconfigure(encoding="utf-8")
        context={"date_format":a.date_format} if a.date_format else None
        print(json.dumps(GeneralizationDB(a.db).get_candidates(a.type,a.value,a.language,context),ensure_ascii=False,indent=2)); return
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(Generalizer(a.db).generalize(a.type,a.value,a.language,a.level).to_dict(),ensure_ascii=False,indent=2))
if __name__=="__main__": main()
