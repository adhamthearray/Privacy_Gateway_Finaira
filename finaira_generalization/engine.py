from dataclasses import dataclass, asdict
from pathlib import Path
import re
from sqlalchemy import select
from sqlalchemy.orm import Session
from .age_date import age, date_generalize
from .db import Occupation, OccupationAlias, IscoGroup, NationalityAlias, Country, make_engine
from .normalization import normalize

SUPPORTED = {"OCCUPATION","JOB_TITLE","NATIONALITY","AGE","DATE"}
@dataclass
class Result:
    entity_type: str; matched: bool; canonical_id: str|None=None; taxonomy: str|None=None; taxonomy_code: str|None=None
    generalization_level: str|None=None; replacement: str|None=None; language: str|None=None; status: str="NOT_FOUND"
    reason_code: str|None=None; source: str|None=None
    def to_dict(self): return asdict(self)

class Generalizer:
    def __init__(self, db_path="data/processed/finaira_generalization.db"):
        self.engine = make_engine(db_path)

    def generalize(self, entity_type, value, output_language="en", level=None, context=None):
        t = entity_type.upper()
        if t == "OCCUPATION":
            t = "JOB_TITLE"
        if t not in SUPPORTED: return Result(t,False,status="UNSUPPORTED_LEVEL",reason_code="UNSUPPORTED_ENTITY_TYPE")
        try:
            if t == "AGE": return Result(t,True,replacement=age(value,output_language),language=output_language,status="VERIFIED",source="Finaira policy")
            if t == "DATE": return Result(t,True,replacement=date_generalize(value,level or "quarter",output_language,(context or {}).get("date_format")),language=output_language,status="VERIFIED",source="Finaira policy")
            with Session(self.engine) as s:
                if t == "NATIONALITY": return self._nationality(s,value,output_language,level)
                return self._occupation(s,value,output_language,level)
        except ValueError as e: return Result(t,False,language=output_language,status=str(e),reason_code=str(e))

    @staticmethod
    def _occupation_phrase_key(value, lang):
        return " ".join(re.findall(r"[^\W_]+", normalize(value, lang), flags=re.UNICODE))

    @staticmethod
    def _occupation_alias_variants(alias_text):
        return [part.strip() for part in re.split(r"\s*/\s*", alias_text) if part.strip()]

    @staticmethod
    def _occupation_query_languages(value, output_language):
        primary = "ar" if re.search(r"[\u0600-\u06ff]", value or "") else "en"
        languages = [primary]
        if output_language in {"ar", "en"} and output_language not in languages:
            languages.append(output_language)
        for language in ("ar", "en"):
            if language not in languages:
                languages.append(language)
        return languages

    def _occupation_lookup(self, s, value, query_language):
        rows=s.scalars(select(OccupationAlias).where(OccupationAlias.language==query_language)).all()
        exact_index={}
        variant_exact_index={}
        phrase_index={}
        for row in rows:
            if row.review_status not in ("OFFICIAL","REVIEWED"):
                continue
            exact_index.setdefault(row.normalized_alias,set()).add(row.occupation_id)
            for variant in self._occupation_alias_variants(row.alias_text):
                variant_exact_index.setdefault(normalize(variant,query_language),set()).add(row.occupation_id)
                phrase=self._occupation_phrase_key(variant,query_language)
                if phrase:
                    phrase_index.setdefault(phrase,set()).add(row.occupation_id)
        ids=exact_index.get(normalize(value,query_language),set())
        phrase=self._occupation_phrase_key(value,query_language)
        shortened=False
        if not ids:
            ids=variant_exact_index.get(normalize(value,query_language),set())
        if not ids and phrase:
            ids=phrase_index.get(phrase,set())
        if not ids:
            tokens=phrase.split()
            for size in range(len(tokens)-1,0,-1):
                found=[]
                for start in range(0,len(tokens)-size+1):
                    candidate=" ".join(tokens[start:start+size])
                    candidate_ids=phrase_index.get(candidate,set())
                    if candidate_ids:
                        found.append(candidate_ids)
                if found:
                    ids=set().union(*found)
                    shortened=True
                    break
        return ids, shortened

    def _occupation(self,s,value,output_language,level):
        for query_language in self._occupation_query_languages(value, output_language):
            ids, shortened = self._occupation_lookup(s, value, query_language)
            if not ids:
                continue
            if len(ids)>1:
                return Result("JOB_TITLE",False,language=output_language,status="AMBIGUOUS",reason_code="ALIAS_COLLISION")
            occ=s.get(Occupation,next(iter(ids))); code=occ.isco_code; target=level or "2"
            if target not in {"1","2","3","4"}: return Result("JOB_TITLE",False,language=output_language,status="UNSUPPORTED_LEVEL",reason_code="INVALID_ISCO_LEVEL")
            group=s.get(IscoGroup,code[:int(target)])
            if not group: return Result("JOB_TITLE",False,language=output_language,status="FALLBACK_REQUIRED",reason_code="MISSING_ISCO_GROUP")
            return Result("JOB_TITLE",True,occ.occupation_id,"ISCO-08",group.isco_code,target,group.label_ar if output_language=="ar" and group.label_ar else group.label_en,output_language,"VERIFIED",reason_code="LONGEST_PHRASE_MATCH" if shortened else None,source="ESCO + ISCO-08")
        return Result("JOB_TITLE",False,replacement="Job title 1" if output_language!="ar" else "المسمى الوظيفي 1",language=output_language,status="FALLBACK_REQUIRED",reason_code="UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK",source="Finaira safe generic fallback")

    def _nationality(self,s,value,lang,level):
        rows=s.scalars(select(NationalityAlias).where(NationalityAlias.normalized_alias==normalize(value,lang),NationalityAlias.language==lang)).all()
        countries={r.country_iso2 for r in rows if r.review_status in ("OFFICIAL","REVIEWED")}
        if len(countries)>1: return Result("NATIONALITY",False,language=lang,status="AMBIGUOUS",reason_code="ALIAS_COLLISION")
        if not countries: return Result("NATIONALITY",False,language=lang,status="FALLBACK_REQUIRED",reason_code="UNRECOGNIZED_NATIONALITY")
        c=s.get(Country,next(iter(countries)))
        if not c or not level: return Result("NATIONALITY",False,canonical_id=next(iter(countries)),language=lang,status="FALLBACK_REQUIRED",reason_code="M49_DATA_MISSING")
        name=(c.subregion_ar if level=="subregion" and lang=="ar" else c.subregion_en if level=="subregion" else c.region_ar if lang=="ar" else c.region_en) if c else None
        code=c.subregion_code if level=="subregion" else c.region_code
        if level not in {"subregion","region"}: return Result("NATIONALITY",False,language=lang,status="UNSUPPORTED_LEVEL",reason_code="INVALID_NATIONALITY_LEVEL")
        if not name or not code: return Result("NATIONALITY",False,canonical_id=c.iso2,language=lang,status="FALLBACK_REQUIRED",reason_code="M49_ENGLISH_LABEL_MISSING" if lang=="en" else "M49_DATA_MISSING")
        repl=(f"تحمل جنسية دولة تقع في {name}" if lang=="ar" else f"Holds the nationality of a country in {name}")
        return Result("NATIONALITY",True,c.iso2,"UN_M49",code,level,repl,lang,"VERIFIED",source="Wikidata + UN M49")
