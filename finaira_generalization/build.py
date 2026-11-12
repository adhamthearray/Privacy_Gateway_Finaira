"""Reproducible SQLite build from the supplied local files."""
import csv, hashlib, json, re, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
from sqlalchemy import delete
from sqlalchemy.orm import Session
from .db import init_db, DataSource, Occupation, OccupationAlias, IscoGroup, NationalityAlias, AgeBand, DateRule, Country
from .normalization import normalize, looks_mojibake

ROOT=Path(__file__).resolve().parents[1]
DEFAULTS={
 "esco_ar": Path(r"C:\Users\domma\Downloads\ESCO dataset - v1.2.1 - classification - ar - csv\occupations_ar.csv"),
 "esco_en": Path(r"C:\Users\domma\Downloads\ESCO dataset - v1.2.1 - classification - en - csv\occupations_en.csv"),
 "nationality": Path(r"C:\Users\domma\Downloads\query.csv"),
 "isco": Path(r"C:\Users\domma\Downloads\ISCO-08 EN.csv"),
 "m49": next(iter(Path(r"C:\Users\domma\Downloads").glob("UNSD*.xlsx")), Path("")),
}

def checksum(p):
    h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()
def source(s,p): return DataSource(name=s,version="supplied",source_url=str(p),checksum=checksum(p) if Path(p).exists() else None)
def read_csv(p):
    for enc in ("utf-8-sig","utf-8","cp1252","cp1256"):
        try: return pd.read_csv(p,encoding=enc),enc
        except UnicodeDecodeError: continue
    raise ValueError(f"ENCODING_ERROR:{p}")
def split_labels(v): return [x.strip() for x in str(v).splitlines() if x.strip() and x.lower()!="nan"]
def code_text(v):
    s=str(v).strip()
    if s.endswith(".0"): s=s[:-2]
    return s

def read_m49_xlsx(p):
    ns={"x":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(p) as z:
        root=ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        rows=[]
        for row in root.findall(".//x:sheetData/x:row",ns)[1:]:
            cells={}
            for c in row.findall("x:c",ns):
                v=c.find("x:v",ns); isel=c.find("x:is",ns); val="" if v is None else v.text
                if isel is not None: val="".join(t.text or "" for t in isel.findall(".//x:t",ns))
                cells[re.match(r"[A-Z]+",c.attrib["r"]).group()] = val
            if cells.get("K") and cells.get("J"): rows.append(cells)
        return rows

def build_database(db_path=ROOT/"data/processed/finaira_generalization.db", paths=None, report_dir=ROOT/"reports"):
    paths={**DEFAULTS,**(paths or {})}; report_dir=Path(report_dir); report_dir.mkdir(parents=True,exist_ok=True); Path(db_path).parent.mkdir(parents=True,exist_ok=True)
    engine=init_db(db_path); warnings=[]; metrics={};
    with Session(engine) as s:
        s.execute(delete(OccupationAlias)); s.execute(delete(Occupation)); s.execute(delete(IscoGroup)); s.execute(delete(NationalityAlias)); s.execute(delete(Country)); s.execute(delete(AgeBand)); s.execute(delete(DateRule)); s.execute(delete(DataSource)); s.commit()
        sources={}
        for k,p in paths.items():
            if Path(p).exists():
                ds=source(k,p); s.add(ds); s.flush(); sources[k]=ds.source_id
            else: warnings.append(f"MISSING_SOURCE:{k}:{p}")
        en,_=read_csv(paths["esco_en"]); ar,_=read_csv(paths["esco_ar"])
        en=en[en.conceptType.eq("Occupation")]; ar=ar[ar.conceptType.eq("Occupation")]
        duplicate_en=int(en.conceptUri.duplicated().sum())
        if duplicate_en: warnings.append(f"DUPLICATE_ENGLISH_ESCO_URIS:{duplicate_en}")
        en=en.drop_duplicates("conceptUri", keep="first")
        duplicate_ar=int(ar.conceptUri.duplicated().sum())
        if duplicate_ar: warnings.append(f"DUPLICATE_ARABIC_ESCO_URIS:{duplicate_ar}")
        armap=ar.drop_duplicates("conceptUri", keep="first").set_index("conceptUri").to_dict("index")
        imported_occupations=0
        for row in en.to_dict("records"):
            uri=row["conceptUri"]; a=armap.get(uri,{}); code=code_text(row.get("iscoGroup") or "").split(".")[0]
            if not code or len(code)!=4: warnings.append(f"MALFORMED_ESCO_ISCO:{uri}"); continue
            imported_occupations += 1
            s.add(Occupation(occupation_id=uri,label_ar=a.get("preferredLabel"),label_en=row.get("preferredLabel"),isco_code=code,source_id=sources["esco_en"]))
            for lang,rr,sid in (("en",row,sources["esco_en"]),("ar",a,sources["esco_ar"])):
                for label in [rr.get("preferredLabel"),*split_labels(rr.get("altLabels"))]:
                    if label and str(label)!="nan": s.add(OccupationAlias(occupation_id=uri,alias_text=label,normalized_alias=normalize(label,lang),language=lang,source_id=sid))
            if not a: warnings.append(f"MISSING_ARABIC_TRANSLATION:{uri}")
        metrics["esco_occupations"]=imported_occupations; metrics["esco_source_rows_deduplicated"]=len(en); metrics["esco_ar_rows"]=len(ar); metrics["esco_ar_coverage"]=sum(1 for x in en.conceptUri if x in armap)
        isco,_=read_csv(paths["isco"])
        labels={}
        for r in isco.to_dict("records"):
            for col,level in (("major",1),("sub_major",2),("minor",3),("unit",4)):
                code=code_text(r.get(col) or "")
                label=str((r.get("description") if col=="unit" else r.get(col+"_label")) or "").strip()
                if code and code!="nan" and label and code not in labels: labels[code]=label
        for code,label in labels.items(): s.add(IscoGroup(isco_code=code,parent_code=code[:-1] if len(code)>1 else None,level=len(code),label_en=label,arabic_label_status="MISSING"))
        metrics["isco_groups"]=len(labels); metrics["esco_isco_unmatched"]=sum(1 for x in en.iscoGroup if code_text(x) not in labels)
        nat,_=read_csv(paths["nationality"]); nat=nat.dropna(subset=["nationality","iso2"])
        for r in nat.to_dict("records"):
            lang=str(r["language"]).lower(); iso=str(r["iso2"]).upper()
            s.add(NationalityAlias(alias_text=str(r["nationality"]),normalized_alias=normalize(r["nationality"],lang),language=lang,country_iso2=iso,source_id=sources["nationality"]))
        metrics["nationality_aliases"]=len(nat); metrics["nationality_ar"]=int((nat.language=="ar").sum()); metrics["nationality_en"]=int((nat.language=="en").sum())
        if Path(paths["m49"]).exists():
            m49rows=read_m49_xlsx(paths["m49"])
            for r in m49rows:
                s.add(Country(iso2=r["K"].upper(),country_ar=r.get("I"),m49_code=code_text(r.get("J")),subregion_code=code_text(r.get("E")),subregion_ar=r.get("F"),region_code=code_text(r.get("C")),region_ar=r.get("D")))
            metrics["m49_countries"]=len(m49rows); metrics["m49_status"]="ARABIC_IMPORTED"
        else:
            metrics["m49_countries"]=0; metrics["m49_status"]="MISSING_SUPPLIED_DATA"
        for i,(lo,hi,ar_label,en_label) in enumerate([(0,17,"أقل من 18 سنة","Under 18"),(18,24,"18–24 سنة","18–24 years"),(25,34,"25–34 سنة","25–34 years"),(35,44,"35–44 سنة","35–44 years"),(45,54,"45–54 سنة","45–54 years"),(55,64,"55–64 سنة","55–64 years"),(65,120,"65 سنة فأكثر","65 years and over")],1): s.add(AgeBand(band_id=i,scheme="default",min_age=lo,max_age=hi,label_ar=ar_label,label_en=en_label))
        for i,p in enumerate(("month","quarter","year"),1): s.add(DateRule(rule_id=i,precision=p,calendar="gregorian",enabled=True))
        s.commit()
    metrics["warnings"]=len(warnings); metrics.setdefault("m49_status","MISSING_SUPPLIED_DATA")
    (report_dir/"validation_report.csv").write_text("metric,value\n"+"\n".join(f"{k},{json.dumps(v,ensure_ascii=False)}" for k,v in metrics.items()),encoding="utf-8")
    (report_dir/"import_report.md").write_text("# Import report\n\n"+"\n".join(f"- **{k}**: {v}" for k,v in metrics.items())+"\n\n## Warnings\n"+"\n".join(f"- {w}" for w in warnings),encoding="utf-8")
    (report_dir/"coverage_report.md").write_text("# Coverage report\n\n"+"\n".join(f"- {k}: {v}" for k,v in metrics.items())+"\n\nThe supplied UNSD workbook is an Arabic M49 table. Arabic geography is imported. English country, region, and subregion labels are absent, so English nationality rendering fails safely with `M49_ENGLISH_LABEL_MISSING`.\n",encoding="utf-8")
    return metrics
