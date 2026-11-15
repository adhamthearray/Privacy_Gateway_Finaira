"""Run a small local browser UI for experimenting with the generalization DB."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finaira_generalization.candidates import BANK_MODEL_FORM_LABELS, GeneralizationDB
from finaira_generalization.date_detector import detect_date
from finaira_generalization.db import (
    Bank,
    BankAlias,
    GeneralizationCandidate,
    GovernmentAlias,
    GovernmentEntity,
    IscoGroup,
    NaturalEarthCountry,
    NaturalEarthCountryAlias,
    NationalityGeoJoin,
    NationalityAliasV2,
    Occupation,
    OccupationAlias,
    Organization,
    OrganizationAlias,
    make_engine,
)
from finaira_generalization.normalization import normalize
from finaira_generalization.layers import stable_id


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Finaira Generalization DB Explorer</title>
  <style>
    :root { color-scheme: dark; --bg:#111827; --panel:#1f2937; --line:#374151; --muted:#9ca3af; --good:#34d399; --warn:#fbbf24; --bad:#f87171; }
    * { box-sizing: border-box; }
    body { margin:0; background:var(--bg); color:#f3f4f6; font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif; }
    main { max-width:1250px; margin:0 auto; padding:28px 20px 56px; }
    h1 { margin:0 0 5px; font-size:28px; }
    h2 { margin:26px 0 12px; font-size:19px; }
    .sub { color:var(--muted); margin:0 0 22px; }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:18px; }
    .form { display:grid; grid-template-columns:minmax(260px,1fr) 190px 150px auto; gap:12px; align-items:end; }
    label { display:block; color:var(--muted); font-size:12px; margin-bottom:5px; }
    input, select, button { width:100%; border:1px solid #4b5563; border-radius:7px; padding:10px 11px; background:#111827; color:#f9fafb; font:inherit; }
    input:focus, select:focus { outline:2px solid #60a5fa; outline-offset:1px; }
    button { background:#2563eb; border-color:#2563eb; cursor:pointer; font-weight:600; }
    button:hover { background:#1d4ed8; }
    .options { display:flex; align-items:center; gap:8px; margin-top:13px; color:var(--muted); }
    .options input { width:auto; }
    .date-context { margin-top:14px; padding-top:14px; border-top:1px solid var(--line); }
    .date-context[hidden] { display:none; }
    .date-context-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:10px 12px; }
    .hint { color:var(--muted); font-size:12px; margin-top:10px; }
    .status { display:flex; flex-wrap:wrap; gap:10px; align-items:center; }
    .badge { display:inline-block; border-radius:999px; padding:4px 10px; font-weight:700; font-size:12px; background:#374151; }
    .verified { color:#052e16; background:var(--good); }
    .matched { color:#052e16; background:var(--good); }
    .generalize { color:#052e16; background:var(--good); }
    .pseudonymize { color:#450a0a; background:var(--bad); }
    .review { color:#422006; background:var(--warn); }
    .ambiguous { color:#431407; background:#fb923c; }
    .notfound, .invalid { color:#450a0a; background:var(--bad); }
    .meta { color:var(--muted); font-size:13px; margin-top:10px; word-break:break-word; }
    .candidate { border:1px solid var(--line); border-radius:10px; padding:14px; margin:10px 0; background:#172033; }
    .candidate-head { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; }
    .candidate-title { font-size:17px; font-weight:700; word-break:break-word; }
    .candidate-id { color:var(--muted); font:12px ui-monospace,SFMono-Regular,Consolas,monospace; word-break:break-all; margin-top:5px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:8px 18px; margin-top:12px; }
    .field { color:var(--muted); font-size:12px; }
    .field strong { color:#e5e7eb; display:block; font-size:13px; word-break:break-word; }
    details { margin-top:12px; }
    pre { white-space:pre-wrap; overflow:auto; background:#0b1020; border:1px solid var(--line); padding:10px; border-radius:7px; color:#d1d5db; font-size:12px; }
    .empty, .error { padding:15px; border-radius:8px; background:#172033; color:var(--muted); }
    .error { color:#fecaca; border:1px solid #7f1d1d; }
    @media (max-width:800px) { .form { grid-template-columns:1fr; } .candidate-head { display:block; } }
  </style>
</head>
<body>
<main>
  <h1>Finaira Generalization DB Explorer</h1>
  <p class="sub">Local, deterministic lookup. Search Arabic or English; all available English and Arabic labels are returned.</p>

  <section class="panel">
    <form id="query-form">
      <div>
        <label for="value">Text or entity value</label>
        <input id="value" name="value" autocomplete="off" placeholder="e.g. مدير الموارد البشرية" required>
      </div>
      <div>
        <label for="type">Entity type</label>
        <select id="type" name="type">
          <option>JOB_TITLE</option><option>OCCUPATION</option><option>COUNTRY</option>
          <option>NATIONALITY</option><option>BANK</option><option>CORPORATION</option>
          <option>ORGANIZATION</option><option>UNIVERSITY</option><option>GOVERNMENT_ENTITY</option>
          <option>AGE</option><option>DATE</option>
        </select>
      </div>
      <button type="submit">Query database</button>
    </form>
    <div class="options">
      <input id="review" type="checkbox">
      <label for="review" style="margin:0">Include review-only candidates</label>
    </div>
    <div id="date-context" class="date-context" hidden>
      <div class="hint" style="margin-top:0;margin-bottom:10px">Date controls are optional. Leave them automatic to see ambiguity safely; provide context only when the source format is known.</div>
      <div class="date-context-grid">
        <div>
          <label for="date-format">Explicit format</label>
          <input id="date-format" placeholder="e.g. %d/%m/%Y" autocomplete="off">
        </div>
        <div>
          <label for="date-order">Numeric order</label>
          <select id="date-order"><option value="">Automatic</option><option value="DMY">Day / month / year</option><option value="MDY">Month / day / year</option><option value="YMD">Year / month / day</option></select>
        </div>
        <div>
          <label for="date-calendar">Calendar hint</label>
          <select id="date-calendar"><option value="">Automatic</option><option value="GREGORIAN">Gregorian</option><option value="HIJRI">Hijri</option><option value="SOLAR_HIJRI">Solar Hijri</option></select>
        </div>
        <div>
          <label for="date-hint">Value hint</label>
          <select id="date-hint"><option value="">Automatic</option><option value="year">Year only</option><option value="epoch_seconds">Epoch seconds</option><option value="epoch_milliseconds">Epoch milliseconds</option></select>
        </div>
        <div>
          <label for="anchor-date">Relative-date anchor</label>
          <input id="anchor-date" type="date">
        </div>
        <div>
          <label for="two-digit-year-base">2-digit year base</label>
          <input id="two-digit-year-base" type="number" min="0" max="9900" placeholder="e.g. 2000">
        </div>
      </div>
    </div>
    <div class="hint">The input language is detected automatically. Review-only results remain gated. This tool shows database candidates; it does not pseudonymize or select a disclosure policy.</div>
  </section>

  <section id="result" style="display:none">
    <h2>Resolution</h2>
    <div class="panel" id="summary"></div>
    <h2>Final decision</h2>
    <div class="panel" id="final-decision"></div>
    <h2>Candidate chain</h2>
    <div id="candidates"></div>
    <h2 id="aggregate-heading" style="display:none">Generalization from common matched hierarchy</h2>
    <div id="aggregate"></div>
    <h2 id="suggestion-heading" style="display:none">Substring suggestions</h2>
    <div id="suggestions"></div>
  </section>
</main>
<script>
const form = document.getElementById('query-form');
const result = document.getElementById('result');
const summary = document.getElementById('summary');
const finalDecision = document.getElementById('final-decision');
const candidates = document.getElementById('candidates');
const aggregateHeading = document.getElementById('aggregate-heading');
const aggregate = document.getElementById('aggregate');
const suggestionHeading = document.getElementById('suggestion-heading');
const suggestions = document.getElementById('suggestions');
const typeSelect = document.getElementById('type');
const dateContext = document.getElementById('date-context');
const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const json = value => esc(JSON.stringify(value ?? {}, null, 2));
const cls = status => String(status || '').toLowerCase().replace(/[^a-z]/g, '');

function syncDateContext() {
  dateContext.hidden = typeSelect.value !== 'DATE';
}

typeSelect.addEventListener('change', syncDateContext);
syncDateContext();

function field(label, value) {
  const shown = value && typeof value === 'object' ? (value.name || value.label || JSON.stringify(value)) : value;
  return `<div class="field">${esc(label)}<strong>${esc(shown === undefined || shown === null || shown === '' ? '—' : shown)}</strong></div>`;
}

function bilingualFields(item) {
  return `${field('English label', item.label_en)}${field('Arabic label', item.label_ar)}`;
}

function renderFinalDecision(data) {
  const decision = data.final_decision;
  if (!decision) {
    finalDecision.innerHTML = '<div class="empty">No final decision was produced.</div>';
    return;
  }
  const action = decision.action || 'PSEUDONYMIZE';
  const why = (decision.why || []).map(item => `<li>${esc(item)}</li>`).join('');
  const path = (decision.path || []).map(item => `${esc(item.level_code)}${item.representation ? `: ${esc(item.representation)}` : ''}`).join(' â†’ ');
  const selected = decision.selected_candidate || {};
  finalDecision.innerHTML = `<div class="status"><span class="badge ${action === 'GENERALIZE' ? 'generalize' : 'pseudonymize'}">${esc(action)}</span><span class="badge">${esc(decision.reason_code)}</span></div>`
    + `<div class="grid">${field('Final response', decision.final_response)}${field('English response', selected.label_en)}${field('Arabic response', selected.label_ar)}${field('Match method', decision.match_method)}${field('Common ancestor', decision.common_ancestor)}${field('Matched values', decision.matched_count)}</div>`
    + `<div class="meta"><strong>Why</strong><ul>${why}</ul></div>`
    + `<div class="meta"><strong>Retained hierarchy</strong><div>${path || 'None'}</div></div>`
    + (decision.selected_candidate ? `<details><summary>Final candidate provenance</summary><pre>${json(decision.selected_candidate)}</pre></details>` : '')
    + `<details><summary>Decision trace</summary><pre>${json(decision)}</pre></details>`;
}

function render(data) {
  result.style.display = 'block';
  renderFinalDecision(data);
  const status = data.resolution_status || 'UNKNOWN';
  summary.innerHTML = `<div class="status"><span class="badge ${cls(status)}">${esc(status)}</span>${data.reason_code ? `<span class="badge">${esc(data.reason_code)}</span>` : ''}</div>`
    + `<div class="grid">${field('Entity type', data.entity_type)}${field('Canonical ID', data.canonical_id)}${field('Candidates', (data.candidates || []).length)}</div>`
    + (data.date_detection ? `<details><summary>Date detection details</summary><div class="grid">${field('Detector status', data.date_detection.status)}${field('Calendar', data.date_detection.calendar)}${field('Precision', data.date_detection.precision)}${field('Format family', data.date_detection.format_family)}${field('Detected date', data.date_detection.date_iso)}${field('Confidence', data.date_detection.confidence)}${field('Time', data.date_detection.time_text)}${field('Timezone', data.date_detection.timezone_text)}</div><pre>${json(data.date_detection)}</pre></details>` : '');
  const rows = data.candidates || [];
  if (!rows.length) { candidates.innerHTML = '<div class="empty">No candidates returned.</div>'; return; }
  candidates.innerHTML = rows.map((item, index) => {
    const flags = [item.is_exact && 'EXACT', item.is_local_only && 'LOCAL_ONLY', item.is_suppression && 'SUPPRESSION', item.available === false && 'UNAVAILABLE'].filter(Boolean);
    return `<article class="candidate"><div class="candidate-head"><div><div class="candidate-title">${esc(item.label_en || item.label_ar || item.representation || item.level_code || 'Unnamed candidate')}</div><div class="candidate-id">${esc(item.candidate_id)}</div></div><span class="badge">rank ${esc(item.specificity_rank ?? index)}</span></div><div class="grid">${bilingualFields(item)}${field('Level', item.level_code)}${field('Verification', item.verification_status)}${field('Source', item.source)}${field('Taxonomy', item.taxonomy)}${field('Taxonomy code', item.taxonomy_code)}${field('Flags', flags.join(' · '))}</div><details><summary>Labels and provenance</summary><pre>${json({label_en:item.label_en,label_ar:item.label_ar,provenance:item.provenance,metadata:item.metadata})}</pre></details></article>`;
  }).join('');
  const common = data.substring_generalization;
  aggregateHeading.style.display = common && common.candidates && common.candidates.length ? 'block' : 'none';
  aggregate.innerHTML = common && common.candidates && common.candidates.length ? `<div class="panel"><div class="status"><span class="badge review">REVIEW ONLY</span><span class="badge">${esc(common.reason)}</span></div><div class="grid">${field('Matched occupations', common.matched_occupation_count)}${field('Common ISCO code', common.common_isco_code)}${field('Common ancestor', common.common_isco_label)}${field('Starts at', common.start_level)}</div>${common.candidates.map(item => `<article class="candidate"><div class="candidate-head"><div><div class="candidate-title">${esc(item.representation || item.level_code || 'Unnamed candidate')}</div><div class="candidate-id">${esc(item.candidate_id)}</div></div><span class="badge">${esc(item.level_code)}</span></div><div class="grid">${field('Verification', item.verification_status)}${field('Source', item.source)}${field('Taxonomy code', item.taxonomy_code)}${field('Flags', [item.is_exact && 'EXACT', item.is_local_only && 'LOCAL_ONLY', item.is_suppression && 'SUPPRESSION'].filter(Boolean).join(' · '))}</div></article>`).join('')}</div>` : '';
  const related = data.substring_suggestions || [];
  const attempted = data.substring_search_performed === true;
  suggestionHeading.style.display = attempted ? 'block' : 'none';
  suggestions.innerHTML = related.length ? related.map(item => `<article class="candidate"><div class="candidate-head"><div><div class="candidate-title">${esc(item.label || item.alias_text || 'Unnamed suggestion')}</div><div class="candidate-id">${esc(item.canonical_id)}</div></div><span class="badge review">REVIEW ONLY</span></div><div class="grid">${field('Matched alias', item.alias_text)}${field('Language', item.language)}${field('Match kind', item.match_kind)}${field('Verification', item.verification_status)}${field('Lookup enabled', item.enabled_for_lookup ? 'yes' : 'no')}${field('Source', item.source)}</div><details><summary>Suggestion details</summary><pre>${json(item)}</pre></details></article>`).join('') : attempted ? '<div class="empty">No stored alias contains this text. This is a database-breadth gap, not a verified match.</div>' : '';
  result.scrollIntoView({behavior:'smooth', block:'start'});
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  const value = document.getElementById('value').value.trim();
  const type = document.getElementById('type').value;
  const review = document.getElementById('review').checked ? '1' : '0';
  const params = new URLSearchParams({value, type, review});
  if (type === 'DATE') {
    const dateFields = {
      date_format: document.getElementById('date-format').value.trim(),
      date_order: document.getElementById('date-order').value,
      calendar: document.getElementById('date-calendar').value,
      date_hint: document.getElementById('date-hint').value,
      anchor_date: document.getElementById('anchor-date').value,
      two_digit_year_base: document.getElementById('two-digit-year-base').value.trim(),
    };
    Object.entries(dateFields).forEach(([key, fieldValue]) => { if (fieldValue) params.set(key, fieldValue); });
  }
  summary.innerHTML = '<div class="empty">Querying the local database…</div>';
  finalDecision.innerHTML = '<div class="empty">Calculating the final deterministic decision...</div>';
  candidates.innerHTML = '';
  aggregate.innerHTML = '';
  aggregateHeading.style.display = 'none';
  suggestions.innerHTML = '';
  suggestionHeading.style.display = 'none';
  result.style.display = 'block';
  try {
    const response = await fetch(`/api/query?${params.toString()}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Query failed');
    render(data);
  } catch (error) {
    summary.innerHTML = `<div class="error">${esc(error.message)}</div>`;
    candidates.innerHTML = '';
  }
});
</script>
</body>
</html>
"""


def _query_languages(value: str, output_language: str) -> list[str]:
    primary = "ar" if any("\u0600" <= char <= "\u06ff" for char in value) else "en"
    languages = [primary]
    if output_language in {"ar", "en"} and output_language not in languages:
        languages.append(output_language)
    for language in ("ar", "en"):
        if language not in languages:
            languages.append(language)
    return languages


def _split_aliases(value: str) -> list[str]:
    return [part.strip() for part in value.split("/") if part.strip()]


def _match_kind(needle: str, haystack: str, index: int) -> str:
    if index == 0:
        return "PREFIX_SUBSTRING"
    before = haystack[index - 1] if index else " "
    return "TOKEN_SUBSTRING" if before.isspace() else "MIDDLE_SUBSTRING"


def substring_suggestions(db_path: Path, entity_type: str, value: str, output_language: str, limit: int = 40) -> list[dict]:
    """Return deterministic, review-only alias substring suggestions.

    This intentionally does not change the resolver result. It is an explorer
    aid for finding possible aliases such as ``مدرسة`` inside longer titles.
    """
    canonical_type = {"OCCUPATION": "JOB_TITLE", "ORGANIZATION": "CORPORATION", "UNIVERSITY": "CORPORATION"}.get(entity_type, entity_type)
    if canonical_type in {"AGE", "DATE"}:
        return []
    suggestions = []
    seen = set()
    with Session(make_engine(db_path)) as session:
        for query_language in _query_languages(value, output_language):
            needle = normalize(value, query_language)
            if not needle:
                continue
            if canonical_type == "JOB_TITLE":
                rows = session.scalars(select(OccupationAlias).where(OccupationAlias.language == query_language, OccupationAlias.normalized_alias.contains(needle, autoescape=True))).all()
                for row in rows:
                    if row.review_status not in {"OFFICIAL", "REVIEWED"}:
                        continue
                    occupation = session.get(Occupation, row.occupation_id)
                    for alias in _split_aliases(row.alias_text):
                        haystack = normalize(alias, query_language)
                        index = haystack.find(needle)
                        key = (row.occupation_id, haystack, query_language)
                        if index < 0 or key in seen:
                            continue
                        seen.add(key)
                        suggestions.append({
                            "canonical_id": row.occupation_id,
                            "alias_text": alias,
                            "label": (occupation.label_ar if output_language == "ar" else occupation.label_en) if occupation else alias,
                            "language": query_language,
                            "match_kind": _match_kind(needle, haystack, index),
                            "match_position": index,
                            "verification_status": row.review_status,
                            "enabled_for_lookup": True,
                            "source": "ESCO substring suggestion",
                            "review_required": True,
                        })
            elif canonical_type == "BANK":
                rows = session.scalars(select(BankAlias).where(BankAlias.language == query_language, BankAlias.normalized_alias.contains(needle, autoescape=True))).all()
                for row in rows:
                    haystack = normalize(row.alias_text, query_language)
                    index = haystack.find(needle)
                    if index < 0:
                        continue
                    bank = session.get(Bank, row.bank_id)
                    key = (row.bank_id, haystack, query_language)
                    if key in seen:
                        continue
                    seen.add(key)
                    suggestions.append({"canonical_id": row.bank_id, "alias_text": row.alias_text, "label": (bank.name_ar if output_language == "ar" else bank.name_en) if bank else row.alias_text, "language": query_language, "match_kind": _match_kind(needle, haystack, index), "match_position": index, "verification_status": row.review_status, "enabled_for_lookup": row.enabled_for_lookup, "source": "Bank alias substring suggestion", "review_required": True})
            elif canonical_type == "COUNTRY":
                rows = session.scalars(select(NaturalEarthCountryAlias).where(NaturalEarthCountryAlias.language == query_language, NaturalEarthCountryAlias.normalized_alias.contains(needle, autoescape=True))).all()
                for row in rows:
                    haystack = normalize(row.alias_text, query_language); index = haystack.find(needle)
                    if index < 0: continue
                    country = session.get(NaturalEarthCountry, row.natural_earth_id); key = (row.natural_earth_id, haystack, query_language)
                    if key in seen: continue
                    seen.add(key)
                    suggestions.append({"canonical_id": country.iso_a2 if country else row.natural_earth_id, "alias_text": row.alias_text, "label": (country.name_ar if output_language == "ar" else country.name_en) if country else row.alias_text, "language": query_language, "match_kind": _match_kind(needle, haystack, index), "match_position": index, "verification_status": row.verification_status, "enabled_for_lookup": row.enabled_for_lookup, "source": "Natural Earth alias substring suggestion", "review_required": True})
            elif canonical_type == "NATIONALITY":
                rows = session.scalars(select(NationalityAliasV2).where(NationalityAliasV2.language == query_language, NationalityAliasV2.normalized_alias.contains(needle, autoescape=True))).all()
                for row in rows:
                    haystack = normalize(row.alias_text, query_language); index = haystack.find(needle)
                    if index < 0: continue
                    key = (row.country_qid, haystack, query_language)
                    if key in seen: continue
                    seen.add(key)
                    suggestions.append({"canonical_id": row.country_qid, "alias_text": row.alias_text, "label": row.alias_text, "language": query_language, "match_kind": _match_kind(needle, haystack, index), "match_position": index, "verification_status": row.verification_status, "enabled_for_lookup": True, "source": "Wikidata demonym substring suggestion", "review_required": True})
            elif canonical_type == "CORPORATION":
                rows = session.scalars(select(OrganizationAlias).where(OrganizationAlias.language == query_language, OrganizationAlias.normalized_alias.contains(needle, autoescape=True))).all()
                for row in rows:
                    haystack = normalize(row.alias_text, query_language); index = haystack.find(needle)
                    if index < 0: continue
                    organization = session.get(Organization, row.organization_qid); key = (row.organization_qid, haystack, query_language)
                    if key in seen: continue
                    seen.add(key)
                    suggestions.append({"canonical_id": row.organization_qid, "alias_text": row.alias_text, "label": (organization.name_ar if output_language == "ar" else organization.name_en) if organization else row.alias_text, "language": query_language, "match_kind": _match_kind(needle, haystack, index), "match_position": index, "verification_status": row.verification_status, "enabled_for_lookup": row.enabled_for_lookup, "source": "Wikidata organization substring suggestion", "review_required": True})
            elif canonical_type == "GOVERNMENT_ENTITY":
                rows = session.scalars(select(GovernmentAlias).where(GovernmentAlias.language == query_language, GovernmentAlias.normalized_alias.contains(needle, autoescape=True))).all()
                for row in rows:
                    haystack = normalize(row.alias_text, query_language); index = haystack.find(needle)
                    if index < 0: continue
                    government = session.get(GovernmentEntity, row.entity_id); key = (row.entity_id, haystack, query_language)
                    if key in seen: continue
                    seen.add(key)
                    suggestions.append({"canonical_id": row.entity_id, "alias_text": row.alias_text, "label": (government.name_ar if output_language == "ar" else government.name_en_provisional) if government else row.alias_text, "language": query_language, "match_kind": _match_kind(needle, haystack, index), "match_position": index, "verification_status": row.verification_status, "enabled_for_lookup": row.enabled_for_lookup, "source": "Government alias substring suggestion", "review_required": True})
    suggestions.sort(key=lambda item: (item["match_position"], len(item["alias_text"]), item["canonical_id"]))
    return suggestions[:limit]


def substring_occupation_ids(db_path: Path, value: str) -> set[str]:
    """Find every occupation whose stored alias contains the input fragment."""
    occupation_ids: set[str] = set()
    with Session(make_engine(db_path)) as session:
        for query_language in _query_languages(value, "en"):
            needle = normalize(value, query_language)
            if not needle:
                continue
            rows = session.scalars(select(OccupationAlias).where(OccupationAlias.language == query_language, OccupationAlias.normalized_alias.contains(needle, autoescape=True))).all()
            for row in rows:
                if row.review_status not in {"OFFICIAL", "REVIEWED"}:
                    continue
                if any(needle in normalize(alias, query_language) for alias in _split_aliases(row.alias_text)):
                    occupation_ids.add(row.occupation_id)
    return occupation_ids


def substring_generalization(db_path: Path, entity_type: str, value: str, output_language: str) -> dict | None:
    """Build a shared ISCO chain for substring-resolved job-title concepts."""
    canonical_type = {"OCCUPATION": "JOB_TITLE"}.get(entity_type, entity_type)
    if canonical_type != "JOB_TITLE":
        return None
    occupation_ids = substring_occupation_ids(db_path, value)
    if not occupation_ids:
        return None
    db = GeneralizationDB(db_path)
    with Session(db.engine) as session:
        occupations = [session.get(Occupation, occupation_id) for occupation_id in sorted(occupation_ids)]
        codes = sorted({str(row.isco_code) for row in occupations if row and row.isco_code})
        groups = {row.isco_code: row for row in session.scalars(select(IscoGroup)).all()}
        common_code = None
        for length in range(4, 0, -1):
            prefixes = {code[:length] for code in codes if len(code) >= length}
            if len(prefixes) == 1 and next(iter(prefixes)) in groups:
                common_code = next(iter(prefixes))
                break
        if common_code is None:
            suppressed = session.get(GeneralizationCandidate, stable_id("JOB_TITLE_ISCO08", "SUPPRESSED"))
            candidates = db._rows(session, "JOB_TITLE_ISCO08", [suppressed] if suppressed else [], output_language)
            return {"status": "NO_COMMON_ISCO_ANCESTOR", "reason": "SUBSTRING_MATCHES_HAVE_NO_SHARED_ISCO_BRANCH", "matched_occupation_count": len(occupation_ids), "matched_occupation_ids": sorted(occupation_ids), "start_level": "SUPPRESSED", "review_required": True, "candidates": candidates}
        candidate = session.scalar(select(GeneralizationCandidate).where(GeneralizationCandidate.scheme_id == "JOB_TITLE_ISCO08", GeneralizationCandidate.taxonomy_code == common_code))
        if candidate is None:
            return None
        all_candidates = {row.candidate_id: row for row in session.scalars(select(GeneralizationCandidate).where(GeneralizationCandidate.scheme_id == "JOB_TITLE_ISCO08")).all()}
        chain = []
        current = candidate
        while current:
            chain.append(current)
            current = all_candidates.get(current.parent_candidate_id)
        candidates = db._rows(session, "JOB_TITLE_ISCO08", chain, output_language)
        return {
            "status": "REVIEW_ONLY",
            "reason": "SUBSTRING_MATCH_COMMON_ISCO_ANCESTOR",
            "matched_occupation_count": len(occupation_ids),
            "matched_occupation_ids": sorted(occupation_ids),
            "common_isco_code": common_code,
            "common_isco_label": groups[common_code].label_ar if output_language == "ar" else groups[common_code].label_en,
            "start_level": candidates[0]["level_code"] if candidates else None,
            "review_required": True,
            "candidates": candidates,
        }


def _canonical_entity_type(entity_type: str) -> str:
    return {
        "OCCUPATION": "JOB_TITLE",
        "ORGANIZATION": "CORPORATION",
        "UNIVERSITY": "CORPORATION",
    }.get(entity_type.upper(), entity_type.upper())


def _candidate_usable(candidate: dict, resolution_status: str) -> bool:
    metadata = candidate.get("metadata") or {}
    provenance = candidate.get("provenance") or metadata.get("provenance") or {}
    if candidate.get("is_exact", metadata.get("is_exact", False)):
        return False
    if candidate.get("is_suppression", metadata.get("is_suppression", False)):
        return False
    if not candidate.get("available", True) or not candidate.get("representation"):
        return False
    if metadata.get("review_only") or provenance.get("requires_policy_approval"):
        return False
    if metadata.get("disclosure_approved") is False:
        return False
    return resolution_status in {"MATCHED", "VERIFIED"}


def _final_from_direct(payload: dict) -> dict | None:
    has_exact = any(
        item.get("is_exact") and not item.get("is_suppression")
        for item in payload.get("candidates", [])
    )
    if not has_exact or payload.get("resolution_status") not in {"MATCHED", "VERIFIED"}:
        return None
    eligible = [
        item for item in payload.get("candidates", [])
        if _candidate_usable(item, payload.get("resolution_status", ""))
    ]
    if not eligible:
        return {
            "action": "PSEUDONYMIZE",
            "final_response": "PSEUDONYMIZE_REQUIRED",
            "reason_code": "DIRECT_MATCH_HAS_NO_USABLE_GENERALIZATION",
            "match_method": "DIRECT_MATCH",
            "why": [
                "A direct entity match was found.",
                "All non-exact candidates are unavailable, review-only, suppressed, or not disclosure-approved.",
            ],
            "path": [
                {"level_code": item.get("level_code"), "representation": item.get("representation")}
                for item in payload.get("candidates", [])
            ],
            "matched_count": 1,
        }
    selected = max(eligible, key=lambda item: (item.get("specificity_rank", 0), item.get("candidate_id", "")))
    return {
        "action": "GENERALIZE",
        "final_response": selected.get("representation"),
        "reason_code": "DIRECT_MATCH_UPPER_HIERARCHY",
        "match_method": "DIRECT_MATCH",
        "why": [
            "A unique direct or normalized alias match was found.",
            "The exact value was excluded from the final response.",
            "The broadest verified, disclosure-approved upper-layer candidate was selected.",
        ],
        "selected_candidate": selected,
        "path": [
            {"level_code": item.get("level_code"), "representation": item.get("representation")}
            for item in payload.get("candidates", [])
        ],
        "matched_count": 1,
    }


def _simple_final_candidate(candidate_id: str, level_code: str, label_en: str | None, label_ar: str | None, language: str, *, taxonomy: str, taxonomy_code: str | None = None, reason: str | None = None) -> dict:
    representation = label_ar if language == "ar" else label_en
    return {
        "candidate_id": candidate_id,
        "level_code": level_code,
        "specificity_rank": 1,
        "representation": representation,
        "language": language,
        "taxonomy": taxonomy,
        "taxonomy_code": taxonomy_code,
        "source": "Finaira common-ancestor resolver",
        "verification_status": "SOURCE_VERIFIED",
        "available": representation is not None,
        "missing_reason": None if representation is not None else "MISSING_VERIFIED_TRANSLATION",
        "label_en": label_en,
        "label_ar": label_ar,
        "is_exact": False,
        "is_local_only": False,
        "is_suppression": False,
        "provenance": {"common_ancestor_reason": reason} if reason else {},
        "metadata": {"disclosure_approved": representation is not None},
    }


def _pseudonym_decision(reason_code: str, why: list[str], *, match_method: str, suggestions: list[dict] | None = None, path: list[dict] | None = None) -> dict:
    return {
        "action": "PSEUDONYMIZE",
        "final_response": "PSEUDONYMIZE_REQUIRED",
        "reason_code": reason_code,
        "match_method": match_method,
        "why": why,
        "matched_count": len(suggestions or []),
        "matched_suggestions": suggestions or [],
        "path": path or [],
    }


def _country_common_ancestor(db_path: Path, entity_type: str, suggestions: list[dict], language: str) -> tuple[dict | None, list[dict], str | None]:
    countries = []
    with Session(make_engine(db_path)) as session:
        for suggestion in suggestions:
            if entity_type == "NATIONALITY":
                join = session.get(NationalityGeoJoin, suggestion["canonical_id"])
                country = session.get(NaturalEarthCountry, join.natural_earth_id) if join and join.natural_earth_id else None
            else:
                country = session.scalar(select(NaturalEarthCountry).where(NaturalEarthCountry.iso_a2 == suggestion["canonical_id"]))
            if country:
                countries.append(country)
    if not countries:
        return None, [], None
    for field, level in (("subregion", "SUBREGION"), ("region_un", "REGION_UN"), ("continent", "CONTINENT")):
        values = {getattr(country, field) for country in countries if getattr(country, field)}
        if len(values) == 1:
            value = next(iter(values))
            candidate = _simple_final_candidate(
                stable_id("COUNTRY_NATURAL_EARTH", level, value),
                level,
                value if language == "en" else None,
                None,
                language,
                taxonomy="NATURAL_EARTH",
                taxonomy_code=value,
                reason=f"All {len(countries)} substring matches share {level}={value}.",
            )
            return candidate, [{"level_code": level, "representation": candidate["representation"]}], value
    return None, [], None


def _substring_final_decision(db_path: Path, entity_type: str, value: str, language: str, suggestions: list[dict], payload: dict) -> dict:
    canonical_type = _canonical_entity_type(entity_type)
    enabled = [
        item for item in suggestions
        if item.get("enabled_for_lookup")
        and str(item.get("verification_status", "")).upper() not in {"HISTORICAL", "REJECTED", "UNVERIFIED"}
    ]
    if not enabled:
        return _pseudonym_decision(
            "NO_ENABLED_SUBSTRING_MATCH",
            [
                "No direct match was found.",
                "Substring suggestions were absent or all were disabled, historical, or unverified.",
            ],
            match_method="NONE" if not suggestions else "SUBSTRING_MATCH",
            suggestions=suggestions,
        )

    if canonical_type == "JOB_TITLE":
        aggregate = substring_generalization(db_path, canonical_type, value, language)
        if aggregate and aggregate.get("status") == "REVIEW_ONLY" and aggregate.get("candidates"):
            candidates = [item for item in aggregate["candidates"] if not item.get("is_suppression") and item.get("representation")]
            if candidates:
                selected = max(candidates, key=lambda item: (item.get("specificity_rank", 0), item.get("candidate_id", "")))
                return {
                    "action": "GENERALIZE",
                    "final_response": selected["representation"],
                    "reason_code": "SUBSTRING_COMMON_ANCESTOR",
                    "match_method": "SUBSTRING_COMMON_ANCESTOR",
                    "why": [
                        "No direct alias match was found.",
                        f"{len(enabled)} verified substring matches were traced through ESCO/ISCO.",
                        f"All matches share the ISCO ancestor {aggregate.get('common_isco_code')}.",
                        "Only the common ancestor and its upper layers were retained.",
                    ],
                    "selected_candidate": selected,
                    "common_ancestor": aggregate.get("common_isco_code"),
                    "path": [
                        {"level_code": item.get("level_code"), "representation": item.get("representation")}
                        for item in aggregate["candidates"]
                    ],
                    "matched_count": len(enabled),
                    "matched_suggestions": enabled,
                }
        return _pseudonym_decision(
            "NO_COMMON_ANCESTOR",
            [
                "No direct alias match was found.",
                f"{len(enabled)} verified substring matches were found.",
                "Their ESCO/ISCO branches have no usable common ancestor.",
            ],
            match_method="SUBSTRING_MATCH",
            suggestions=enabled,
        )

    if canonical_type in {"COUNTRY", "NATIONALITY"}:
        candidate, path, ancestor = _country_common_ancestor(db_path, canonical_type, enabled, language)
        if candidate and candidate.get("representation"):
            return {
                "action": "GENERALIZE",
                "final_response": candidate["representation"],
                "reason_code": "SUBSTRING_COMMON_ANCESTOR",
                "match_method": "SUBSTRING_COMMON_ANCESTOR",
                "why": [
                    "No direct alias match was found.",
                    f"{len(enabled)} verified country or nationality matches were traced to Natural Earth.",
                    f"All matches share the {candidate['level_code']} ancestor {ancestor}.",
                ],
                "selected_candidate": candidate,
                "common_ancestor": ancestor,
                "path": path,
                "matched_count": len(enabled),
                "matched_suggestions": enabled,
            }
        return _pseudonym_decision(
            "NO_COMMON_ANCESTOR",
            [
                "No direct alias match was found.",
                f"{len(enabled)} country or nationality matches were found.",
                "They do not share a usable verified Natural Earth ancestor in the requested language.",
            ],
            match_method="SUBSTRING_MATCH",
            suggestions=enabled,
        )

    if canonical_type == "BANK":
        with Session(make_engine(db_path)) as session:
            models = {session.get(Bank, item["canonical_id"]).finance_model for item in enabled if session.get(Bank, item["canonical_id"])}
        if len(models) == 1:
            model = next(iter(models))
            label_en, label_ar = BANK_MODEL_FORM_LABELS.get(model, (None, None))
            candidate = _simple_final_candidate(
                f"BANK_FINANCE_MODEL__{model}", "FINANCE_MODEL", label_en, label_ar, language,
                taxonomy="FINAIR_BANK", taxonomy_code=model,
                reason=f"All {len(enabled)} substring matches share banking model {model}.",
            )
            if candidate["representation"]:
                return {
                    "action": "GENERALIZE",
                    "final_response": candidate["representation"],
                    "reason_code": "SUBSTRING_COMMON_ANCESTOR",
                    "match_method": "SUBSTRING_COMMON_ANCESTOR",
                    "why": [
                        "No direct bank alias match was found.",
                        f"{len(enabled)} enabled bank substring matches were traced.",
                        f"All matches share the verified banking model {model}.",
                    ],
                    "selected_candidate": candidate,
                    "common_ancestor": model,
                    "path": [{"level_code": "FINANCE_MODEL", "representation": candidate["representation"]}],
                    "matched_count": len(enabled),
                    "matched_suggestions": enabled,
                }
        candidate = _simple_final_candidate(
            "BANKING_INSTITUTION__COMMON", "BANKING_INSTITUTION", "Banking institution", "مؤسسة مصرفية", language,
            taxonomy="FINAIR_BANK", reason=f"All {len(enabled)} bank matches share the banking-institution ancestor.",
        )
        if candidate["representation"]:
            return {
                "action": "GENERALIZE",
                "final_response": candidate["representation"],
                "reason_code": "SUBSTRING_COMMON_ANCESTOR",
                "match_method": "SUBSTRING_COMMON_ANCESTOR",
                "why": [
                    "No direct bank alias match was found.",
                    f"{len(enabled)} enabled bank substring matches were traced.",
                    "The matches have different banking models, so the shared ancestor is Banking institution.",
                ],
                "selected_candidate": candidate,
                "common_ancestor": "BANKING_INSTITUTION",
                "path": [{"level_code": "BANKING_INSTITUTION", "representation": candidate["representation"]}],
                "matched_count": len(enabled),
                "matched_suggestions": enabled,
            }

    if canonical_type == "CORPORATION":
        fallback = GeneralizationDB(db_path).get_candidates("CORPORATION", "__no_direct_match__", language)
        candidate = next((item for item in fallback.get("candidates", []) if not item.get("is_suppression")), None)
        if candidate:
            return {
                "action": "GENERALIZE",
                "final_response": candidate["representation"],
                "reason_code": "SUBSTRING_COMMON_ANCESTOR",
                "match_method": "SUBSTRING_COMMON_ANCESTOR",
                "why": [
                    "No direct corporation alias match was found.",
                    f"{len(enabled)} corporation-like substring matches were traced.",
                    "All organization, university, and corporation matches share the generic Corporation form.",
                ],
                "selected_candidate": candidate,
                "common_ancestor": "CORPORATION_GENERIC",
                "path": [{"level_code": candidate.get("level_code"), "representation": candidate.get("representation")}],
                "matched_count": len(enabled),
                "matched_suggestions": enabled,
            }

    if canonical_type == "GOVERNMENT_ENTITY":
        fallback = GeneralizationDB(db_path).get_candidates("GOVERNMENT_ENTITY", "__no_direct_match__", language)
        candidate = next((item for item in fallback.get("candidates", []) if not item.get("is_suppression")), None)
        if candidate:
            return {
                "action": "GENERALIZE",
                "final_response": candidate["representation"],
                "reason_code": "SUBSTRING_COMMON_ANCESTOR",
                "match_method": "SUBSTRING_COMMON_ANCESTOR",
                "why": [
                    "No direct government-entity alias match was found.",
                    f"{len(enabled)} government substring matches were traced.",
                    "All matches share the generic Government entity form.",
                ],
                "selected_candidate": candidate,
                "common_ancestor": "GOVERNMENT_ENTITY_GENERIC",
                "path": [{"level_code": candidate.get("level_code"), "representation": candidate.get("representation")}],
                "matched_count": len(enabled),
                "matched_suggestions": enabled,
            }

    return _pseudonym_decision(
        "NO_COMMON_ANCESTOR",
        [
            "No direct alias match was found.",
            f"{len(enabled)} substring matches were found.",
            f"No common verified hierarchy is defined for {canonical_type}.",
        ],
        match_method="SUBSTRING_MATCH",
        suggestions=enabled,
    )


def final_decision(db_path: Path, entity_type: str, value: str, language: str, payload: dict, suggestions: list[dict]) -> dict:
    direct = _final_from_direct(payload)
    if direct:
        return direct
    if payload.get("resolution_status") in {"AMBIGUOUS", "INVALID_INPUT", "NEEDS_CONTEXT", "UNSUPPORTED"}:
        reason = payload.get("reason_code") or payload.get("resolution_status")
        return _pseudonym_decision(
            reason,
            [
                f"The resolver returned {payload.get('resolution_status')}.",
                "A deterministic generalized representation cannot be selected safely.",
            ],
            match_method="AMBIGUOUS_OR_INVALID",
            suggestions=suggestions,
        )
    if not suggestions:
        return _pseudonym_decision(
            "NO_MATCH",
            [
                "No direct alias match was found.",
                "No enabled substring match was found.",
                "No verified generalization form is available.",
            ],
            match_method="NONE",
        )
    return _substring_final_decision(db_path, entity_type, value, language, suggestions, payload)


def _date_context(params: dict[str, list[str]]) -> dict:
    """Build only supported detector context from browser query parameters."""
    context = {}
    for key in ("date_format", "date_order", "calendar", "date_hint", "anchor_date"):
        value = params.get(key, [""])[0].strip()
        if value:
            context[key] = value
    year_base = params.get("two_digit_year_base", [""])[0].strip()
    if year_base:
        try:
            context["two_digit_year_base"] = int(year_base)
        except ValueError:
            raise ValueError("2-digit year base must be an integer")
    return context


def _date_detection_payload(value: str, context: dict) -> dict:
    detected = detect_date(value, context)
    return {
        "raw": detected.raw,
        "status": detected.status,
        "reason_code": detected.reason_code,
        "calendar": detected.calendar,
        "precision": detected.precision,
        "language": detected.language,
        "format_family": detected.format_family,
        "confidence": detected.confidence,
        "date_iso": detected.date_iso,
        "time_text": detected.time_text,
        "timezone_text": detected.timezone_text,
        "is_relative": detected.is_relative,
        "is_ambiguous": detected.is_ambiguous,
        "candidates": detected.candidates,
        "metadata": detected.metadata,
    }


class Handler(BaseHTTPRequestHandler):
    db_path: Path

    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._send(HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/query":
            params = parse_qs(parsed.query)
            value = params.get("value", [""])[0].strip()
            entity_type = params.get("type", [""])[0].strip().upper()
            language = "ar" if any("\u0600" <= char <= "\u06ff" for char in value) else "en"
            include_review = params.get("review", ["0"])[0] == "1"
            if not value:
                self._send(json.dumps({"error": "Enter a value to query."}).encode(), "application/json", 400)
                return
            if language not in {"ar", "en"}:
                self._send(json.dumps({"error": "Output language must be ar or en."}).encode(), "application/json", 400)
                return
            try:
                context = _date_context(params) if entity_type == "DATE" else {}
                payload = GeneralizationDB(self.db_path).get_candidates(entity_type, value, "en", context=context, include_review_candidates=include_review, input_language=language)
                payload["input_language"] = language
                if entity_type == "DATE":
                    payload["date_detection"] = _date_detection_payload(value, context)
                has_exact = any(item.get("is_exact") and not item.get("is_suppression") for item in payload.get("candidates", []))
                suggestions = []
                if not has_exact:
                    payload["substring_search_performed"] = True
                    suggestions = substring_suggestions(self.db_path, entity_type, value, language)
                    payload["substring_suggestions"] = suggestions
                    payload["substring_generalization"] = substring_generalization(self.db_path, entity_type, value, language)
                payload["final_decision"] = final_decision(self.db_path, entity_type, value, language, payload, suggestions)
                self._send(json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            except Exception as exc:  # Keep the local UI usable while exposing the actual failure.
                self._send(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", 500)
            return
        self._send(b"Not found", "text/plain; charset=utf-8", 404)

    def log_message(self, format: str, *args) -> None:
        print(f"[ui] {self.address_string()} - {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "data/processed/finaira_generalization.db")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not args.db.exists():
        raise SystemExit(f"Database not found: {args.db}")
    Handler.db_path = args.db
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Finaira Generalization DB Explorer: http://{args.host}:{args.port}/")
    print(f"Database: {args.db}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping UI")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
