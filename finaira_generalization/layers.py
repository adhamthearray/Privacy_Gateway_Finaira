"""Static layered candidate materialization for source-backed taxonomies."""
from datetime import datetime, timezone
import hashlib
from sqlalchemy import delete, select, func, text
from sqlalchemy.orm import Session
from .db import (
    GeneralizationScheme, GeneralizationLevel, GeneralizationCandidate,
    CandidateMetadata, CandidateProvenance, OccupationCandidateRef,
    NationalityCandidateRef, Occupation, IscoGroup, NationalityAlias,
    Country, DataSource, AgeBand, DateRule, AgeSchemeRule, DateSchemeRule, OccupationIscoRef, NationalityAliasCountryRef, M49Region, CountryM49Link, make_engine, init_db,
)

def stable_id(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:32]

def _source_map(s):
    return {x.name: x for x in s.scalars(select(DataSource)).all()}

def _scheme(s, scheme_id, entity_type, name, taxonomy, version, description, source_id=None):
    obj=s.get(GeneralizationScheme, scheme_id)
    if not obj:
        obj=GeneralizationScheme(scheme_id=scheme_id,entity_type=entity_type,scheme_name=name,taxonomy_name=taxonomy,taxonomy_version=version,description=description,source_id=source_id,enabled=True); s.add(obj)
    return obj

def _levels(s, scheme_id, defs):
    existing={x.level_code:x for x in s.scalars(select(GeneralizationLevel).where(GeneralizationLevel.scheme_id==scheme_id)).all()}
    out={}
    for rank, code, desc, kind, exact, suppression, local in defs:
        x=existing.get(code)
        if not x:
            x=GeneralizationLevel(scheme_id=scheme_id,level_code=code,specificity_rank=rank,description=desc,representation_kind=kind,is_exact=exact,is_suppression=suppression,default_local_only=local); s.add(x); s.flush()
        out[code]=x
    return out

COMMON_OCC=[(0,"EXACT","Recognized ESCO occupation", "exact",True,False,True),(1,"ISCO_UNIT","ISCO unit group","taxonomy",False,False,False),(2,"ISCO_MINOR","ISCO minor group","taxonomy",False,False,False),(3,"ISCO_SUB_MAJOR","ISCO sub-major group","taxonomy",False,False,False),(4,"ISCO_MAJOR","ISCO major group","taxonomy",False,False,False),(5,"SUPPRESSED","Occupation information unspecified","suppression",False,True,False)]
NAT=[(0,"EXACT","Recognized nationality", "exact",True,False,True),(1,"SUBREGION","M49 subregion nationality category","taxonomy",False,False,False),(2,"REGION","M49 region nationality category","taxonomy",False,False,False),(3,"SUPPRESSED","Nationality unspecified","suppression",False,True,False)]
NATURAL_EARTH=[(0,"EXACT","Recognized nationality", "exact",True,False,True),(1,"SUBREGION","Natural Earth subregion descriptor","taxonomy",False,False,False),(2,"CONTINENT","Natural Earth continent descriptor","taxonomy",False,False,False),(3,"SUPPRESSED","Nationality unspecified","suppression",False,True,False)]
AGE=[(0,"EXACT","Exact age", "exact",True,False,True),(1,"NARROW_BAND","Configured narrow age band","interval",False,False,False),(2,"WIDE_BAND","Configured wide age band","interval",False,False,False),(3,"BROAD_CATEGORY","Broad age category","category",False,False,False),(4,"SUPPRESSED","Age unspecified","suppression",False,True,False)]
DATE=[(0,"EXACT","Exact Gregorian date", "exact",True,False,True),(1,"MONTH","Calendar month","temporal_interval",False,False,False),(2,"QUARTER","Calendar quarter","temporal_interval",False,False,False),(3,"YEAR","Calendar year","temporal_interval",False,False,False),(4,"SUPPRESSED","Date unspecified","suppression",False,True,False)]

def _add(s, candidate, level, *, taxonomy_depth=None, count=None, exact=False, suppression=False, local=False, preserves_exact=False, preserves_category=False, preserves_identity=False, numeric=False, interval_start=None, interval_end=None, interval_width=None, source=None, ref=None, note=None):
    if not s.get(GeneralizationCandidate,candidate.candidate_id):
        s.add(candidate); s.flush()
        s.add(CandidateMetadata(candidate_id=candidate.candidate_id,specificity_rank=level.specificity_rank,taxonomy_depth=taxonomy_depth,underlying_category_count=count,is_exact=exact,is_suppression=suppression,is_local_only=local,preserves_exact_value=preserves_exact,preserves_category=preserves_category,preserves_entity_identity=preserves_identity,preserves_numeric_precision=numeric,representation_kind=level.representation_kind,verification_status=candidate.review_status,interval_start=interval_start,interval_end=interval_end,interval_width=interval_width))
        s.add(CandidateProvenance(candidate_id=candidate.candidate_id,source_id=source.source_id if source else None,source_version=source.version if source else None,source_checksum=source.checksum if source else None,derivation_method=candidate.derivation_method,validation_status="VALIDATED",review_status=candidate.review_status,notes=note))
        if ref:
            s.add(ref)

def generate_levels(db_path="data/processed/finaira_generalization.db"):
    engine=init_db(db_path); generated={}
    with Session(engine) as s:
        # Rebuild only derived layered rows. Base imported tables remain untouched.
        for model in (CountryM49Link, M49Region, OccupationIscoRef, NationalityAliasCountryRef, AgeSchemeRule, DateSchemeRule, OccupationCandidateRef, NationalityCandidateRef, CandidateProvenance, CandidateMetadata, GeneralizationCandidate, GeneralizationLevel, GeneralizationScheme): s.execute(delete(model))
        sources=_source_map(s); isco_src=sources.get("isco"); m49_src=sources.get("m49") or sources.get("UNSD — Methodology.xlsx")
        schemes={}
        ne_src=sources.get("natural_earth_admin0_10m_v5.1.1_csv")
        for sid, et, name, tax, ver, desc, defs, src in [
            ("OCCUPATION_ISCO08","OCCUPATION","Occupation ISCO-08 layers","ISCO-08","08","ESCO occupation to ISCO hierarchy",COMMON_OCC,isco_src),
            ("JOB_TITLE_ISCO08","JOB_TITLE","Job title ISCO-08 layers","ISCO-08","08","Job title using shared ESCO/ISCO infrastructure",COMMON_OCC,isco_src),
            ("NATIONALITY_M49","NATIONALITY","Nationality UN M49 layers","UN M49","current","Legacy M49 compatibility layers; not used by active nationality retrieval",NAT,m49_src),
            ("NATIONALITY_NATURAL_EARTH","NATIONALITY","Nationality Natural Earth layers","NATURAL_EARTH","5.1.1","Nationality to Natural Earth descriptors; candidates are generated at read time",NATURAL_EARTH,ne_src),
            ("AGE_STANDARD","AGE","Configurable age layers","Finaira policy","1","Rule-based age intervals",AGE,None),
            ("DATE_GREGORIAN","DATE","Gregorian date layers","Gregorian","1","Rule-based Gregorian intervals",DATE,None),
        ]:
            schemes[sid]=_scheme(s,sid,et,name,tax,ver,desc,src.source_id if src else None)
            _levels(s,sid,defs)
        for band in s.scalars(select(AgeBand)).all(): s.add(AgeSchemeRule(scheme_id="AGE_STANDARD",band_id=band.band_id))
        for rule in s.scalars(select(DateRule)).all(): s.add(DateSchemeRule(scheme_id="DATE_GREGORIAN",rule_id=rule.rule_id))
        s.commit()
        occs=s.scalars(select(Occupation)).all(); groups={x.isco_code:x for x in s.scalars(select(IscoGroup)).all()}
        for o in occs:
            if o.isco_code in groups: s.add(OccupationIscoRef(occupation_id=o.occupation_id,isco_code=o.isco_code,source_id=o.source_id))
        for a in s.scalars(select(NationalityAlias)).all():
            if s.get(Country,a.country_iso2): s.add(NationalityAliasCountryRef(alias_id=a.alias_id,iso2=a.country_iso2))
        s.flush()
        occ_counts={k:0 for k in groups}
        for o in occs:
            for code in (o.isco_code,o.isco_code[:-1],o.isco_code[:-2],o.isco_code[:1]):
                if code in occ_counts: occ_counts[code]+=1
        for scheme_id in ("OCCUPATION_ISCO08","JOB_TITLE_ISCO08"):
            levels={x.level_code:x for x in s.scalars(select(GeneralizationLevel).where(GeneralizationLevel.scheme_id==scheme_id)).all()}; cat={}
            supid=stable_id(scheme_id,"SUPPRESSED")
            _add(s,GeneralizationCandidate(candidate_id=supid,scheme_id=scheme_id,level_id=levels["SUPPRESSED"].level_id,canonical_entity_id=None,taxonomy_code=None,parent_candidate_id=None,label_ar="معلومات المهنة غير محددة",label_en="Occupation information unspecified",source_id=None,review_status="OFFICIAL",derivation_method="rule:suppression"),levels["SUPPRESSED"],suppression=True)
            for code in sorted(groups, key=lambda x: (len(x), x)):
                g=groups[code]
                rank={4:"ISCO_UNIT",3:"ISCO_MINOR",2:"ISCO_SUB_MAJOR",1:"ISCO_MAJOR"}.get(len(code));
                if not rank: continue
                cid=stable_id(scheme_id,rank,code); parent_code=code[:-1] if len(code)>1 else None; parent=cat.get(parent_code)
                cat[code]=cid
                _add(s,GeneralizationCandidate(candidate_id=cid,scheme_id=scheme_id,level_id=levels[rank].level_id,canonical_entity_id=None,taxonomy_code=code,parent_candidate_id=parent,label_ar=g.label_ar,label_en=g.label_en,source_id=isco_src.source_id if isco_src else None,review_status="OFFICIAL",derivation_method="source:isco_groups"),levels[rank],taxonomy_depth=len(code),count=occ_counts.get(code),preserves_category=True,source=isco_src,note="Shared ISCO category; label is not copied from ESCO occupation." )
                s.flush()
            for o in occs:
                ex=stable_id(scheme_id,"EXACT",o.occupation_id); unit=cat.get(o.isco_code); unit_parent=unit
                _add(s,GeneralizationCandidate(candidate_id=ex,scheme_id=scheme_id,level_id=levels["EXACT"].level_id,canonical_entity_id=o.occupation_id,taxonomy_code=None,parent_candidate_id=unit_parent,label_ar=o.label_ar,label_en=o.label_en,source_id=o.source_id,review_status="OFFICIAL",derivation_method="source:esco_occupation"),levels["EXACT"],exact=True,local=True,preserves_exact=True,preserves_identity=True,source=s.get(DataSource,o.source_id),ref=OccupationCandidateRef(candidate_id=ex,occupation_id=o.occupation_id))
                s.flush()
            generated[scheme_id]=len(occs)+len(cat)+1
        # Nationality candidates are one exact candidate per ISO country plus shared M49 categories.
        levels={x.level_code:x for x in s.scalars(select(GeneralizationLevel).where(GeneralizationLevel.scheme_id=="NATIONALITY_M49")).all()}; countries=s.scalars(select(Country)).all(); aliases=s.scalars(select(NationalityAlias)).all(); by_iso={}
        for a in aliases: by_iso.setdefault(a.country_iso2,{"ar":[],"en":[]}).setdefault(a.language,[]).append(a.alias_text)
        sub_counts={}; reg_counts={}
        regions={}
        for c in countries:
            if c.region_code and c.region_code not in regions: regions[c.region_code]=M49Region(code=c.region_code,parent_code=None,level=1,label_ar=c.region_ar,label_en=c.region_en); s.add(regions[c.region_code])
            if c.subregion_code and c.subregion_code not in regions: regions[c.subregion_code]=M49Region(code=c.subregion_code,parent_code=c.region_code,level=2,label_ar=c.subregion_ar,label_en=c.subregion_en); s.add(regions[c.subregion_code])
        s.flush()
        for c in countries: s.add(CountryM49Link(iso2=c.iso2,subregion_code=c.subregion_code,region_code=c.region_code))
        for c in countries: sub_counts[c.subregion_code]=sub_counts.get(c.subregion_code,0)+1; reg_counts[c.region_code]=reg_counts.get(c.region_code,0)+1
        supid=stable_id("NATIONALITY_M49","SUPPRESSED"); _add(s,GeneralizationCandidate(candidate_id=supid,scheme_id="NATIONALITY_M49",level_id=levels["SUPPRESSED"].level_id,label_ar="الجنسية غير محددة",label_en="Nationality unspecified",review_status="OFFICIAL",derivation_method="rule:suppression"),levels["SUPPRESSED"],suppression=True)
        regs={}; subs={}
        for c in countries:
            if c.region_code and c.region_code not in regs:
                cid=stable_id("NATIONALITY_M49","REGION",c.region_code); regs[c.region_code]=cid; _add(s,GeneralizationCandidate(candidate_id=cid,scheme_id="NATIONALITY_M49",level_id=levels["REGION"].level_id,taxonomy_code=c.region_code,parent_candidate_id=supid,label_ar=c.region_ar,label_en=c.region_en,source_id=m49_src.source_id if m49_src else None,review_status="OFFICIAL",derivation_method="source:m49"),levels["REGION"],taxonomy_depth=1,count=reg_counts.get(c.region_code),preserves_category=True,source=m49_src)
            if c.subregion_code and c.subregion_code not in subs:
                cid=stable_id("NATIONALITY_M49","SUBREGION",c.subregion_code); subs[c.subregion_code]=cid; _add(s,GeneralizationCandidate(candidate_id=cid,scheme_id="NATIONALITY_M49",level_id=levels["SUBREGION"].level_id,taxonomy_code=c.subregion_code,parent_candidate_id=regs.get(c.region_code,supid),label_ar=c.subregion_ar,label_en=c.subregion_en,source_id=m49_src.source_id if m49_src else None,review_status="OFFICIAL",derivation_method="source:m49"),levels["SUBREGION"],taxonomy_depth=2,count=sub_counts.get(c.subregion_code),preserves_category=True,source=m49_src)
            labels=by_iso.get(c.iso2,{})
            cid=stable_id("NATIONALITY_M49","EXACT",c.iso2); _add(s,GeneralizationCandidate(candidate_id=cid,scheme_id="NATIONALITY_M49",level_id=levels["EXACT"].level_id,canonical_entity_id=c.iso2,parent_candidate_id=subs.get(c.subregion_code,supid),label_ar=sorted(labels.get("ar",[]))[0] if labels.get("ar") else c.country_ar,label_en=sorted(labels.get("en",[]))[0] if labels.get("en") else c.country_en,taxonomy_code=c.iso2,source_id=m49_src.source_id if m49_src else None,review_status="OFFICIAL",derivation_method="source:wikidata+m49"),levels["EXACT"],exact=True,local=True,preserves_exact=True,preserves_identity=True,source=m49_src,ref=NationalityCandidateRef(candidate_id=cid,iso2=c.iso2))
        generated["NATIONALITY_M49"]=len(countries)+len(subs)+len(regs)+1
        s.execute(text("INSERT OR REPLACE INTO build_metadata(key,value) VALUES ('layered_schema_version','1')")); s.commit()
    return generated
