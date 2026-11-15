-- Exported from SQLite sqlite_master
PRAGMA foreign_keys=ON;

-- table: age_bands
CREATE TABLE age_bands (
	band_id INTEGER NOT NULL, 
	scheme VARCHAR(50) NOT NULL, 
	min_age INTEGER NOT NULL, 
	max_age INTEGER, 
	label_ar TEXT NOT NULL, 
	label_en TEXT NOT NULL, 
	PRIMARY KEY (band_id)
);

-- table: age_scheme_rules
CREATE TABLE age_scheme_rules (
	scheme_id VARCHAR(80) NOT NULL, 
	band_id INTEGER NOT NULL, 
	PRIMARY KEY (scheme_id, band_id), 
	FOREIGN KEY(scheme_id) REFERENCES generalization_schemes (scheme_id), 
	FOREIGN KEY(band_id) REFERENCES age_bands (band_id)
);

-- table: bank_aliases
CREATE TABLE bank_aliases (
	alias_id VARCHAR(64) NOT NULL, 
	bank_id VARCHAR(30) NOT NULL, 
	alias_text TEXT NOT NULL, 
	normalized_alias TEXT NOT NULL, 
	language VARCHAR(2) NOT NULL, 
	alias_kind VARCHAR(50), 
	review_status VARCHAR(50) NOT NULL, 
	enabled_for_lookup BOOLEAN NOT NULL, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (alias_id), 
	CONSTRAINT uq_bank_alias UNIQUE (normalized_alias, language, bank_id), 
	FOREIGN KEY(bank_id) REFERENCES banks (bank_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: bank_audit_classifications
CREATE TABLE bank_audit_classifications (
	audit_id VARCHAR(100) NOT NULL, 
	source_record_id VARCHAR(40) NOT NULL, 
	bank_id VARCHAR(30) NOT NULL, 
	country_code VARCHAR(2) NOT NULL, 
	country VARCHAR(80) NOT NULL, 
	raw_category VARCHAR(80), 
	raw_status VARCHAR(50), 
	banking_model VARCHAR(40) NOT NULL, 
	banking_model_source VARCHAR(80) NOT NULL, 
	business_scope VARCHAR(120), 
	entity_kind VARCHAR(100), 
	operational_status VARCHAR(50) NOT NULL, 
	license_confirmation VARCHAR(100), 
	classification_evidence TEXT, 
	source_url TEXT, 
	evidence_url TEXT, 
	confidence VARCHAR(40), 
	review_action VARCHAR(80), 
	review_note TEXT, 
	license_status VARCHAR(30) NOT NULL, 
	licensed_count_eligible BOOLEAN NOT NULL, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (audit_id), 
	FOREIGN KEY(bank_id) REFERENCES banks (bank_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: bank_candidates
CREATE TABLE bank_candidates (
	candidate_id VARCHAR(120) NOT NULL, 
	bank_id VARCHAR(30) NOT NULL, 
	level_code VARCHAR(40) NOT NULL, 
	specificity_rank INTEGER NOT NULL, 
	label_en TEXT, 
	label_ar TEXT, 
	finance_model VARCHAR(20), 
	category_population_count INTEGER, 
	is_exact BOOLEAN NOT NULL, 
	is_local_only BOOLEAN NOT NULL, 
	is_suppression BOOLEAN NOT NULL, 
	disclosure_approved BOOLEAN NOT NULL, 
	evidence_status VARCHAR(80) NOT NULL, 
	verification_status VARCHAR(40) NOT NULL, 
	source_id INTEGER NOT NULL, 
	derivation_method VARCHAR(80) NOT NULL, 
	PRIMARY KEY (candidate_id), 
	CONSTRAINT uq_bank_candidate_level UNIQUE (bank_id, level_code), 
	FOREIGN KEY(bank_id) REFERENCES banks (bank_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: bank_evidence
CREATE TABLE bank_evidence (
	evidence_id VARCHAR(80) NOT NULL, 
	bank_id VARCHAR(30) NOT NULL, 
	finance_model VARCHAR(20) NOT NULL, 
	source_type VARCHAR(50) NOT NULL, 
	source_url TEXT, 
	evidence_summary_en TEXT, 
	source_publication_or_update TEXT, 
	checked_on VARCHAR(20), 
	source_strength VARCHAR(20), 
	notes TEXT, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (evidence_id), 
	FOREIGN KEY(bank_id) REFERENCES banks (bank_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: bank_generalization_cohorts
CREATE TABLE bank_generalization_cohorts (
	safe_generalization_key VARCHAR(120) NOT NULL, 
	model VARCHAR(60) NOT NULL, 
	record_count INTEGER NOT NULL, 
	countries TEXT, 
	names TEXT, 
	bank_record_ids TEXT, 
	automatic_grouping BOOLEAN NOT NULL, 
	family_id VARCHAR(80), 
	eligible_for_lookup BOOLEAN NOT NULL, 
	eligibility_reason TEXT, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (safe_generalization_key), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: bank_generalization_forms
CREATE TABLE bank_generalization_forms (
	form_id VARCHAR(160) NOT NULL, 
	source_record_id VARCHAR(40) NOT NULL, 
	canonical_bank_id VARCHAR(30) NOT NULL, 
	safe_generalization_key VARCHAR(120) NOT NULL, 
	level_code VARCHAR(40) NOT NULL, 
	specificity_rank INTEGER NOT NULL, 
	label_en TEXT, 
	label_ar TEXT, 
	banking_model VARCHAR(60), 
	verification_status VARCHAR(40) NOT NULL, 
	enabled_for_lookup BOOLEAN NOT NULL, 
	disclosure_approved BOOLEAN NOT NULL, 
	is_exact BOOLEAN NOT NULL, 
	is_local_only BOOLEAN NOT NULL, 
	is_suppression BOOLEAN NOT NULL, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (form_id), 
	FOREIGN KEY(source_record_id) REFERENCES bank_identity_model_records (record_id), 
	FOREIGN KEY(canonical_bank_id) REFERENCES banks (bank_id), 
	FOREIGN KEY(safe_generalization_key) REFERENCES bank_generalization_cohorts (safe_generalization_key), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: bank_identity_model_records
CREATE TABLE bank_identity_model_records (
	record_id VARCHAR(40) NOT NULL, 
	canonical_bank_id VARCHAR(30) NOT NULL, 
	country_code VARCHAR(2) NOT NULL, 
	source_name_en TEXT, 
	source_name_ar TEXT, 
	family_id VARCHAR(80), 
	family_display_name TEXT, 
	generalization_key VARCHAR(120), 
	bank_identity_id VARCHAR(120), 
	is_same_legal_bank_as_parent VARCHAR(40), 
	relationship_to_family VARCHAR(80), 
	banking_model_from_audit VARCHAR(60), 
	source_entity_kind TEXT, 
	source_license_confirmation TEXT, 
	group_relation_status VARCHAR(100), 
	family_evidence_basis TEXT, 
	verified_family_source_urls TEXT, 
	import_action VARCHAR(100), 
	historical_successor_record_id VARCHAR(40), 
	transition_effective_date VARCHAR(40), 
	review_note TEXT, 
	country_license_review_needed VARCHAR(20), 
	original_category VARCHAR(100), 
	canonical_name_2026 TEXT, 
	former_legal_name TEXT, 
	banking_model_effective VARCHAR(60), 
	historical_operating_model_pre_transition TEXT, 
	banking_service_profile TEXT, 
	model_evidence_tier VARCHAR(120), 
	banking_model_verified_source TEXT, 
	status_asof_2026_11_15 TEXT, 
	record_class VARCHAR(40), 
	source_original_generalization_key VARCHAR(120), 
	proposed_model_aware_key VARCHAR(120), 
	safe_generalization_key VARCHAR(120), 
	automatic_grouping BOOLEAN NOT NULL, 
	identity_resolution_confidence TEXT, 
	review_required BOOLEAN NOT NULL, 
	review_reason TEXT, 
	successor_model_aware_key_if_post_transition VARCHAR(120), 
	non_merge_reason TEXT, 
	source_bank_register_url TEXT, 
	banking_business_scope TEXT, 
	original_model_confidence VARCHAR(60), 
	aliases_en TEXT, 
	aliases_ar TEXT, 
	former_names TEXT, 
	arabic_name_confidence VARCHAR(80), 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (record_id), 
	FOREIGN KEY(canonical_bank_id) REFERENCES banks (bank_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: bank_model_aliases
CREATE TABLE bank_model_aliases (
	alias_id VARCHAR(64) NOT NULL, 
	record_id VARCHAR(40) NOT NULL, 
	canonical_bank_id VARCHAR(30) NOT NULL, 
	country_code VARCHAR(2) NOT NULL, 
	bank_name_en TEXT, 
	alias_text TEXT NOT NULL, 
	normalized_alias TEXT NOT NULL, 
	language VARCHAR(2) NOT NULL, 
	alias_type VARCHAR(80), 
	category VARCHAR(80), 
	status VARCHAR(50), 
	review_required BOOLEAN NOT NULL, 
	safe_generalization_key VARCHAR(120), 
	proposed_model_aware_key VARCHAR(120), 
	family_id VARCHAR(80), 
	bank_identity_id VARCHAR(120), 
	banking_model_effective VARCHAR(60), 
	automatic_grouping BOOLEAN NOT NULL, 
	enabled_for_lookup BOOLEAN NOT NULL, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (alias_id), 
	FOREIGN KEY(record_id) REFERENCES bank_identity_model_records (record_id), 
	FOREIGN KEY(canonical_bank_id) REFERENCES banks (bank_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: bank_model_do_not_merge
CREATE TABLE bank_model_do_not_merge (
	exclusion_id VARCHAR(64) NOT NULL, 
	record_a VARCHAR(40) NOT NULL, 
	record_b VARCHAR(40) NOT NULL, 
	why TEXT, 
	collision_type VARCHAR(80), 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (exclusion_id), 
	FOREIGN KEY(record_a) REFERENCES bank_identity_model_records (record_id), 
	FOREIGN KEY(record_b) REFERENCES bank_identity_model_records (record_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: bank_model_evidence_notes
CREATE TABLE bank_model_evidence_notes (
	note_id VARCHAR(64) NOT NULL, 
	record_id VARCHAR(40) NOT NULL, 
	risk VARCHAR(80), 
	detail TEXT, 
	source_url TEXT, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (note_id), 
	FOREIGN KEY(record_id) REFERENCES bank_identity_model_records (record_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: bank_model_relationship_evidence
CREATE TABLE bank_model_relationship_evidence (
	relationship_id VARCHAR(100) NOT NULL, 
	from_record_id VARCHAR(40) NOT NULL, 
	to_record_id VARCHAR(40) NOT NULL, 
	relationship_type VARCHAR(80) NOT NULL, 
	impact_on_generalization VARCHAR(100), 
	explanation TEXT, 
	source_url TEXT, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (relationship_id), 
	FOREIGN KEY(from_record_id) REFERENCES bank_identity_model_records (record_id), 
	FOREIGN KEY(to_record_id) REFERENCES bank_identity_model_records (record_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: bank_model_research_corrections
CREATE TABLE bank_model_research_corrections (
	correction_id VARCHAR(64) NOT NULL, 
	record_id VARCHAR(40) NOT NULL, 
	description TEXT, 
	old_values TEXT, 
	new_values TEXT, 
	source_url TEXT, 
	evidence_tier VARCHAR(80), 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (correction_id), 
	FOREIGN KEY(record_id) REFERENCES bank_identity_model_records (record_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: bank_relationships
CREATE TABLE bank_relationships (
	relationship_id VARCHAR(100) NOT NULL, 
	child_bank_id VARCHAR(30) NOT NULL, 
	parent_bank_id VARCHAR(30) NOT NULL, 
	relationship_type VARCHAR(40) NOT NULL, 
	source_record_id VARCHAR(40), 
	verification_status VARCHAR(40) NOT NULL, 
	evidence_note TEXT, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (relationship_id), 
	FOREIGN KEY(child_bank_id) REFERENCES banks (bank_id), 
	FOREIGN KEY(parent_bank_id) REFERENCES banks (bank_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: banks
CREATE TABLE banks (
	bank_id VARCHAR(30) NOT NULL, 
	cbe_list_number VARCHAR(20), 
	name_en TEXT NOT NULL, 
	name_ar TEXT, 
	finance_model VARCHAR(20) NOT NULL, 
	finance_model_label_en TEXT NOT NULL, 
	finance_model_label_ar TEXT NOT NULL, 
	classification_rule VARCHAR(80) NOT NULL, 
	evidence_status VARCHAR(80) NOT NULL, 
	evidence_confidence VARCHAR(30), 
	as_of_date VARCHAR(20), 
	evidence_review_status VARCHAR(50), 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (bank_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: build_metadata
CREATE TABLE build_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);

-- table: candidate_metadata
CREATE TABLE candidate_metadata (
	candidate_id VARCHAR(160) NOT NULL, 
	specificity_rank INTEGER NOT NULL, 
	taxonomy_depth INTEGER, 
	underlying_category_count INTEGER, 
	is_exact BOOLEAN NOT NULL, 
	is_suppression BOOLEAN NOT NULL, 
	is_local_only BOOLEAN NOT NULL, 
	preserves_exact_value BOOLEAN NOT NULL, 
	preserves_category BOOLEAN NOT NULL, 
	preserves_entity_identity BOOLEAN NOT NULL, 
	preserves_numeric_precision BOOLEAN NOT NULL, 
	representation_kind VARCHAR(40) NOT NULL, 
	verification_status VARCHAR(30) NOT NULL, 
	interval_start VARCHAR(40), 
	interval_end VARCHAR(40), 
	interval_width INTEGER, 
	PRIMARY KEY (candidate_id), 
	FOREIGN KEY(candidate_id) REFERENCES generalization_candidates (candidate_id)
);

-- table: candidate_provenance
CREATE TABLE candidate_provenance (
	provenance_id INTEGER NOT NULL, 
	candidate_id VARCHAR(160) NOT NULL, 
	source_id INTEGER, 
	source_version VARCHAR(100), 
	source_checksum VARCHAR(64), 
	derivation_method VARCHAR(80) NOT NULL, 
	validation_status VARCHAR(30) NOT NULL, 
	review_status VARCHAR(30) NOT NULL, 
	review_date VARCHAR(40), 
	notes TEXT, 
	PRIMARY KEY (provenance_id), 
	FOREIGN KEY(candidate_id) REFERENCES generalization_candidates (candidate_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: corporation_aliases
CREATE TABLE corporation_aliases (
	alias_id VARCHAR(160) NOT NULL, 
	corporation_id VARCHAR(160) NOT NULL, 
	source_entity_type VARCHAR(30) NOT NULL, 
	source_entity_id VARCHAR(80) NOT NULL, 
	alias_text TEXT NOT NULL, 
	normalized_alias TEXT NOT NULL, 
	language VARCHAR(2) NOT NULL, 
	verification_status VARCHAR(60) NOT NULL, 
	enabled_for_lookup BOOLEAN NOT NULL, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (alias_id), 
	CONSTRAINT uq_corporation_alias UNIQUE (corporation_id, normalized_alias, language), 
	FOREIGN KEY(corporation_id) REFERENCES corporation_entities (corporation_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: corporation_entities
CREATE TABLE corporation_entities (
	corporation_id VARCHAR(160) NOT NULL, 
	source_entity_type VARCHAR(30) NOT NULL, 
	source_entity_id VARCHAR(80) NOT NULL, 
	name_en TEXT, 
	name_ar TEXT, 
	verification_status VARCHAR(60) NOT NULL, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (corporation_id), 
	CONSTRAINT uq_corporation_source_entity UNIQUE (source_entity_type, source_entity_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: countries
CREATE TABLE countries (
	iso2 VARCHAR(2) NOT NULL, 
	country_ar TEXT, 
	country_en TEXT, 
	m49_code VARCHAR(3), 
	subregion_code VARCHAR(3), 
	subregion_ar TEXT, 
	subregion_en TEXT, 
	region_code VARCHAR(3), 
	region_ar TEXT, 
	region_en TEXT, 
	PRIMARY KEY (iso2)
);

-- table: country_m49_links
CREATE TABLE country_m49_links (
	iso2 VARCHAR(2) NOT NULL, 
	subregion_code VARCHAR(3), 
	region_code VARCHAR(3), 
	PRIMARY KEY (iso2), 
	FOREIGN KEY(iso2) REFERENCES countries (iso2), 
	FOREIGN KEY(subregion_code) REFERENCES m49_regions (code), 
	FOREIGN KEY(region_code) REFERENCES m49_regions (code)
);

-- table: data_sources
CREATE TABLE data_sources (
	source_id INTEGER NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	version VARCHAR(100), 
	source_url VARCHAR(500), 
	retrieved_at VARCHAR(40) NOT NULL, 
	license VARCHAR(300), 
	checksum VARCHAR(64), 
	PRIMARY KEY (source_id), 
	UNIQUE (name)
);

-- table: date_rules
CREATE TABLE date_rules (
	rule_id INTEGER NOT NULL, 
	precision VARCHAR(20) NOT NULL, 
	calendar VARCHAR(30) NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	PRIMARY KEY (rule_id)
);

-- table: date_scheme_rules
CREATE TABLE date_scheme_rules (
	scheme_id VARCHAR(80) NOT NULL, 
	rule_id INTEGER NOT NULL, 
	PRIMARY KEY (scheme_id, rule_id), 
	FOREIGN KEY(scheme_id) REFERENCES generalization_schemes (scheme_id), 
	FOREIGN KEY(rule_id) REFERENCES date_rules (rule_id)
);

-- table: generalization_candidates
CREATE TABLE generalization_candidates (
	candidate_id VARCHAR(160) NOT NULL, 
	scheme_id VARCHAR(80) NOT NULL, 
	level_id INTEGER NOT NULL, 
	canonical_entity_id VARCHAR(300), 
	taxonomy_code VARCHAR(20), 
	parent_candidate_id VARCHAR(160), 
	label_ar TEXT, 
	label_en TEXT, 
	source_id INTEGER, 
	review_status VARCHAR(30) NOT NULL, 
	derivation_method VARCHAR(80) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (candidate_id), 
	FOREIGN KEY(scheme_id) REFERENCES generalization_schemes (scheme_id), 
	FOREIGN KEY(level_id) REFERENCES generalization_levels (level_id), 
	FOREIGN KEY(parent_candidate_id) REFERENCES generalization_candidates (candidate_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: generalization_levels
CREATE TABLE generalization_levels (
	level_id INTEGER NOT NULL, 
	scheme_id VARCHAR(80) NOT NULL, 
	level_code VARCHAR(40) NOT NULL, 
	specificity_rank INTEGER NOT NULL, 
	description TEXT, 
	representation_kind VARCHAR(40) NOT NULL, 
	is_exact BOOLEAN NOT NULL, 
	is_suppression BOOLEAN NOT NULL, 
	default_local_only BOOLEAN NOT NULL, 
	PRIMARY KEY (level_id), 
	CONSTRAINT uq_level_scheme_code UNIQUE (scheme_id, level_code), 
	CONSTRAINT uq_level_scheme_rank UNIQUE (scheme_id, specificity_rank), 
	FOREIGN KEY(scheme_id) REFERENCES generalization_schemes (scheme_id)
);

-- table: generalization_schemes
CREATE TABLE generalization_schemes (
	scheme_id VARCHAR(80) NOT NULL, 
	entity_type VARCHAR(30) NOT NULL, 
	scheme_name VARCHAR(120) NOT NULL, 
	taxonomy_name VARCHAR(80) NOT NULL, 
	taxonomy_version VARCHAR(40), 
	description TEXT, 
	source_id INTEGER, 
	enabled BOOLEAN NOT NULL, 
	PRIMARY KEY (scheme_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: government_aliases
CREATE TABLE government_aliases (
	alias_id VARCHAR(64) NOT NULL, 
	entity_id VARCHAR(30) NOT NULL, 
	language VARCHAR(2) NOT NULL, 
	alias_text TEXT NOT NULL, 
	normalized_alias TEXT NOT NULL, 
	verification_status VARCHAR(50) NOT NULL, 
	enabled_for_lookup BOOLEAN NOT NULL, 
	source_url TEXT, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (alias_id), 
	FOREIGN KEY(entity_id) REFERENCES government_entities (entity_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: government_candidate_reviews
CREATE TABLE government_candidate_reviews (
	candidate_id VARCHAR(100) NOT NULL, 
	entity_id VARCHAR(30) NOT NULL, 
	level_code VARCHAR(50) NOT NULL, 
	dimension VARCHAR(30) NOT NULL, 
	specificity_rank_branch_local INTEGER NOT NULL, 
	label_ar TEXT, 
	label_en TEXT, 
	source_url TEXT, 
	verification_status VARCHAR(50) NOT NULL, 
	requires_policy_approval BOOLEAN NOT NULL, 
	is_local_only BOOLEAN NOT NULL, 
	is_suppression BOOLEAN NOT NULL, 
	default_visible BOOLEAN NOT NULL, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (candidate_id), 
	FOREIGN KEY(entity_id) REFERENCES government_entities (entity_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: government_categories
CREATE TABLE government_categories (
	category_code VARCHAR(50) NOT NULL, 
	label_ar TEXT NOT NULL, 
	label_en TEXT NOT NULL, 
	parent_category_code VARCHAR(50), 
	reidentification_risk_hint VARCHAR(30), 
	status VARCHAR(50) NOT NULL, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (category_code), 
	FOREIGN KEY(parent_category_code) REFERENCES government_categories (category_code), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: government_entities
CREATE TABLE government_entities (
	entity_id VARCHAR(30) NOT NULL, 
	name_ar TEXT NOT NULL, 
	name_en_provisional TEXT, 
	country_iso VARCHAR(2) NOT NULL, 
	organization_form_code VARCHAR(50), 
	function_code VARCHAR(50), 
	wikidata_qid VARCHAR(20), 
	official_source_url TEXT, 
	identity_verification_status VARCHAR(50) NOT NULL, 
	function_verification_status VARCHAR(50) NOT NULL, 
	english_name_verification_status VARCHAR(50) NOT NULL, 
	enabled_for_specific_mapping BOOLEAN NOT NULL, 
	dataset_status VARCHAR(50), 
	review_notes TEXT, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (entity_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: government_entity_categories
CREATE TABLE government_entity_categories (
	link_id VARCHAR(100) NOT NULL, 
	entity_id VARCHAR(30) NOT NULL, 
	category_code VARCHAR(50) NOT NULL, 
	dimension VARCHAR(30) NOT NULL, 
	verification_status VARCHAR(50) NOT NULL, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (link_id), 
	FOREIGN KEY(entity_id) REFERENCES government_entities (entity_id), 
	FOREIGN KEY(category_code) REFERENCES government_categories (category_code), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: government_review_queue
CREATE TABLE government_review_queue (
	review_id VARCHAR(64) NOT NULL, 
	entity_id VARCHAR(30) NOT NULL, 
	review_identity VARCHAR(30), 
	review_current_status VARCHAR(30), 
	review_function_category VARCHAR(30), 
	review_english_name VARCHAR(30), 
	review_wikidata_qid VARCHAR(30), 
	specific_mapping_enabled BOOLEAN NOT NULL, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (review_id), 
	FOREIGN KEY(entity_id) REFERENCES government_entities (entity_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: import_batches
CREATE TABLE import_batches (
	batch_id VARCHAR(100) NOT NULL, 
	started_at VARCHAR(40) NOT NULL, 
	completed_at VARCHAR(40), 
	status VARCHAR(30) NOT NULL, 
	manifest_path TEXT, 
	counts_json TEXT, 
	error_text TEXT, 
	PRIMARY KEY (batch_id)
);

-- table: industry_categories
CREATE TABLE industry_categories (
	category_code VARCHAR(50) NOT NULL, 
	parent_code VARCHAR(50), 
	label_en TEXT NOT NULL, 
	label_ar TEXT NOT NULL, 
	category_kind VARCHAR(30) NOT NULL, 
	license VARCHAR(100), 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (category_code), 
	FOREIGN KEY(parent_code) REFERENCES industry_categories (category_code), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: industry_qid_mappings
CREATE TABLE industry_qid_mappings (
	mapping_id VARCHAR(64) NOT NULL, 
	industry_qid VARCHAR(40) NOT NULL, 
	source_industry_label_en TEXT, 
	sector_code VARCHAR(50), 
	subcategory_code VARCHAR(50), 
	subcategory_label_en TEXT, 
	subcategory_label_ar TEXT, 
	review_status VARCHAR(50) NOT NULL, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (mapping_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: isco_groups
CREATE TABLE isco_groups (
	isco_code VARCHAR(4) NOT NULL, 
	parent_code VARCHAR(4), 
	level INTEGER NOT NULL, 
	label_ar TEXT, 
	label_en TEXT, 
	arabic_label_status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (isco_code)
);

-- table: m49_regions
CREATE TABLE m49_regions (
	code VARCHAR(3) NOT NULL, 
	parent_code VARCHAR(3), 
	level INTEGER NOT NULL, 
	label_ar TEXT, 
	label_en TEXT, 
	PRIMARY KEY (code), 
	FOREIGN KEY(parent_code) REFERENCES m49_regions (code)
);

-- table: nationality_alias_country_refs
CREATE TABLE nationality_alias_country_refs (
	alias_id INTEGER NOT NULL, 
	iso2 VARCHAR(2) NOT NULL, 
	PRIMARY KEY (alias_id), 
	FOREIGN KEY(alias_id) REFERENCES nationality_aliases (alias_id), 
	FOREIGN KEY(iso2) REFERENCES countries (iso2)
);

-- table: nationality_alias_review_provenance
CREATE TABLE nationality_alias_review_provenance (
	provenance_id VARCHAR(120) NOT NULL, 
	alias_key VARCHAR(64) NOT NULL, 
	corpus_value TEXT NOT NULL, 
	base_alias TEXT NOT NULL, 
	derivation_rule VARCHAR(120) NOT NULL, 
	evidence_reference TEXT NOT NULL, 
	review_status VARCHAR(40) NOT NULL, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (provenance_id), 
	CONSTRAINT uq_nationality_review_provenance UNIQUE (alias_key, base_alias, derivation_rule), 
	FOREIGN KEY(alias_key) REFERENCES nationality_aliases_v2 (alias_key), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: nationality_aliases
CREATE TABLE nationality_aliases (
	alias_id INTEGER NOT NULL, 
	alias_text TEXT NOT NULL, 
	normalized_alias TEXT NOT NULL, 
	language VARCHAR(2) NOT NULL, 
	country_iso2 VARCHAR(2) NOT NULL, 
	source_id INTEGER NOT NULL, 
	review_status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (alias_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: nationality_aliases_v2
CREATE TABLE nationality_aliases_v2 (
	alias_key VARCHAR(64) NOT NULL, 
	country_qid VARCHAR(20) NOT NULL, 
	iso2 VARCHAR(2) NOT NULL, 
	alias_text TEXT NOT NULL, 
	normalized_alias TEXT NOT NULL, 
	language VARCHAR(2) NOT NULL, 
	source_id INTEGER NOT NULL, 
	verification_status VARCHAR(40) NOT NULL, 
	PRIMARY KEY (alias_key), 
	FOREIGN KEY(country_qid) REFERENCES nationality_countries (country_qid), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: nationality_candidate_refs
CREATE TABLE nationality_candidate_refs (
	candidate_id VARCHAR(160) NOT NULL, 
	iso2 VARCHAR(2) NOT NULL, 
	PRIMARY KEY (candidate_id), 
	FOREIGN KEY(candidate_id) REFERENCES generalization_candidates (candidate_id), 
	FOREIGN KEY(iso2) REFERENCES countries (iso2)
);

-- table: nationality_countries
CREATE TABLE nationality_countries (
	country_qid VARCHAR(20) NOT NULL, 
	iso2 VARCHAR(2) NOT NULL, 
	country_label TEXT, 
	source_id INTEGER NOT NULL, 
	verification_status VARCHAR(40) NOT NULL, 
	PRIMARY KEY (country_qid), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: nationality_deduplications
CREATE TABLE nationality_deduplications (
	deduplication_id VARCHAR(160) NOT NULL, 
	deduplication_type VARCHAR(40) NOT NULL, 
	removed_key VARCHAR(160) NOT NULL, 
	kept_key VARCHAR(160) NOT NULL, 
	removed_country_qid VARCHAR(20), 
	kept_country_qid VARCHAR(20), 
	iso2 VARCHAR(2), 
	alias_text TEXT, 
	normalized_alias TEXT, 
	language VARCHAR(2), 
	reason TEXT NOT NULL, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (deduplication_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: nationality_geo_joins
CREATE TABLE nationality_geo_joins (
	country_qid VARCHAR(20) NOT NULL, 
	iso2 VARCHAR(2) NOT NULL, 
	natural_earth_id VARCHAR(40), 
	join_status VARCHAR(30) NOT NULL, 
	match_method VARCHAR(20), 
	audit_note TEXT, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (country_qid), 
	FOREIGN KEY(country_qid) REFERENCES nationality_countries (country_qid), 
	FOREIGN KEY(natural_earth_id) REFERENCES natural_earth_countries (natural_earth_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: natural_earth_countries
CREATE TABLE natural_earth_countries (
	natural_earth_id VARCHAR(40) NOT NULL, 
	wikidata_qid VARCHAR(20), 
	iso_a2 VARCHAR(2), 
	name_en TEXT, 
	name_ar TEXT, 
	subregion TEXT, 
	region_un TEXT, 
	continent TEXT, 
	source_id INTEGER NOT NULL, 
	source_version VARCHAR(40) NOT NULL, 
	PRIMARY KEY (natural_earth_id), 
	CONSTRAINT uq_ne_country_wikidata_qid UNIQUE (wikidata_qid), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: natural_earth_country_aliases
CREATE TABLE natural_earth_country_aliases (
	alias_id VARCHAR(100) NOT NULL, 
	natural_earth_id VARCHAR(40) NOT NULL, 
	alias_text TEXT NOT NULL, 
	normalized_alias TEXT NOT NULL, 
	language VARCHAR(2) NOT NULL, 
	alias_kind VARCHAR(30) NOT NULL, 
	source_property VARCHAR(50) NOT NULL, 
	source_id INTEGER NOT NULL, 
	verification_status VARCHAR(40) NOT NULL, 
	enabled_for_lookup BOOLEAN NOT NULL, 
	PRIMARY KEY (alias_id), 
	CONSTRAINT uq_ne_country_alias UNIQUE (natural_earth_id, normalized_alias, language), 
	FOREIGN KEY(natural_earth_id) REFERENCES natural_earth_countries (natural_earth_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: occupation_aliases
CREATE TABLE occupation_aliases (
	alias_id INTEGER NOT NULL, 
	occupation_id VARCHAR(300) NOT NULL, 
	alias_text TEXT NOT NULL, 
	normalized_alias TEXT NOT NULL, 
	language VARCHAR(2) NOT NULL, 
	source_id INTEGER NOT NULL, 
	review_status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (alias_id), 
	FOREIGN KEY(occupation_id) REFERENCES occupations (occupation_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: occupation_candidate_refs
CREATE TABLE occupation_candidate_refs (
	candidate_id VARCHAR(160) NOT NULL, 
	occupation_id VARCHAR(300) NOT NULL, 
	PRIMARY KEY (candidate_id), 
	FOREIGN KEY(candidate_id) REFERENCES generalization_candidates (candidate_id), 
	FOREIGN KEY(occupation_id) REFERENCES occupations (occupation_id)
);

-- table: occupation_isco_refs
CREATE TABLE occupation_isco_refs (
	occupation_id VARCHAR(300) NOT NULL, 
	isco_code VARCHAR(4) NOT NULL, 
	source_id INTEGER, 
	PRIMARY KEY (occupation_id), 
	FOREIGN KEY(occupation_id) REFERENCES occupations (occupation_id), 
	FOREIGN KEY(isco_code) REFERENCES isco_groups (isco_code), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: occupations
CREATE TABLE occupations (
	occupation_id VARCHAR(300) NOT NULL, 
	label_ar TEXT, 
	label_en TEXT, 
	isco_code VARCHAR(4), 
	source_id INTEGER NOT NULL, 
	review_status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (occupation_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: organization_aliases
CREATE TABLE organization_aliases (
	alias_id VARCHAR(64) NOT NULL, 
	organization_qid VARCHAR(20) NOT NULL, 
	alias_text TEXT NOT NULL, 
	normalized_alias TEXT NOT NULL, 
	language VARCHAR(2) NOT NULL, 
	enabled_for_lookup BOOLEAN NOT NULL, 
	verification_status VARCHAR(50) NOT NULL, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (alias_id), 
	CONSTRAINT uq_org_alias UNIQUE (normalized_alias, language, organization_qid), 
	FOREIGN KEY(organization_qid) REFERENCES organizations (organization_qid), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: organization_exclusions
CREATE TABLE organization_exclusions (
	exclusion_id VARCHAR(64) NOT NULL, 
	organization_qid VARCHAR(20), 
	name_en TEXT, 
	name_ar TEXT, 
	reason TEXT NOT NULL, 
	import_decision VARCHAR(50) NOT NULL, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (exclusion_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: organization_industries
CREATE TABLE organization_industries (
	link_id VARCHAR(100) NOT NULL, 
	organization_qid VARCHAR(20) NOT NULL, 
	mapping_id VARCHAR(64), 
	industry_qid VARCHAR(40) NOT NULL, 
	sector_code VARCHAR(50), 
	subcategory_code VARCHAR(50), 
	mapping_status VARCHAR(50), 
	import_decision VARCHAR(70) NOT NULL, 
	verification_status VARCHAR(50) NOT NULL, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (link_id), 
	FOREIGN KEY(organization_qid) REFERENCES organizations (organization_qid), 
	FOREIGN KEY(mapping_id) REFERENCES industry_qid_mappings (mapping_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: organization_review_queue
CREATE TABLE organization_review_queue (
	review_id VARCHAR(64) NOT NULL, 
	organization_qid VARCHAR(20), 
	import_status VARCHAR(50), 
	review_flags TEXT, 
	import_decision VARCHAR(70), 
	review_reason TEXT, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (review_id), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- table: organizations
CREATE TABLE organizations (
	organization_qid VARCHAR(20) NOT NULL, 
	name_en TEXT, 
	name_ar TEXT, 
	semantic_kind VARCHAR(30) NOT NULL, 
	identity_verification_status VARCHAR(50) NOT NULL, 
	import_decision VARCHAR(70) NOT NULL, 
	import_status VARCHAR(70), 
	review_flags TEXT, 
	source_id INTEGER NOT NULL, 
	PRIMARY KEY (organization_qid), 
	FOREIGN KEY(source_id) REFERENCES data_sources (source_id)
);

-- index: ix_bank_aliases_bank_id
CREATE INDEX ix_bank_aliases_bank_id ON bank_aliases (bank_id);

-- index: ix_bank_aliases_language
CREATE INDEX ix_bank_aliases_language ON bank_aliases (language);

-- index: ix_bank_aliases_normalized_alias
CREATE INDEX ix_bank_aliases_normalized_alias ON bank_aliases (normalized_alias);

-- index: ix_bank_audit_classifications_bank_id
CREATE INDEX ix_bank_audit_classifications_bank_id ON bank_audit_classifications (bank_id);

-- index: ix_bank_audit_classifications_banking_model
CREATE INDEX ix_bank_audit_classifications_banking_model ON bank_audit_classifications (banking_model);

-- index: ix_bank_audit_classifications_business_scope
CREATE INDEX ix_bank_audit_classifications_business_scope ON bank_audit_classifications (business_scope);

-- index: ix_bank_audit_classifications_confidence
CREATE INDEX ix_bank_audit_classifications_confidence ON bank_audit_classifications (confidence);

-- index: ix_bank_audit_classifications_country_code
CREATE INDEX ix_bank_audit_classifications_country_code ON bank_audit_classifications (country_code);

-- index: ix_bank_audit_classifications_entity_kind
CREATE INDEX ix_bank_audit_classifications_entity_kind ON bank_audit_classifications (entity_kind);

-- index: ix_bank_audit_classifications_license_status
CREATE INDEX ix_bank_audit_classifications_license_status ON bank_audit_classifications (license_status);

-- index: ix_bank_audit_classifications_licensed_count_eligible
CREATE INDEX ix_bank_audit_classifications_licensed_count_eligible ON bank_audit_classifications (licensed_count_eligible);

-- index: ix_bank_audit_classifications_operational_status
CREATE INDEX ix_bank_audit_classifications_operational_status ON bank_audit_classifications (operational_status);

-- index: ix_bank_audit_classifications_raw_status
CREATE INDEX ix_bank_audit_classifications_raw_status ON bank_audit_classifications (raw_status);

-- index: ix_bank_audit_classifications_review_action
CREATE INDEX ix_bank_audit_classifications_review_action ON bank_audit_classifications (review_action);

-- index: ix_bank_audit_classifications_source_record_id
CREATE UNIQUE INDEX ix_bank_audit_classifications_source_record_id ON bank_audit_classifications (source_record_id);

-- index: ix_bank_candidates_bank_id
CREATE INDEX ix_bank_candidates_bank_id ON bank_candidates (bank_id);

-- index: ix_bank_candidates_level_code
CREATE INDEX ix_bank_candidates_level_code ON bank_candidates (level_code);

-- index: ix_bank_evidence_bank_id
CREATE INDEX ix_bank_evidence_bank_id ON bank_evidence (bank_id);

-- index: ix_bank_generalization_cohorts_automatic_grouping
CREATE INDEX ix_bank_generalization_cohorts_automatic_grouping ON bank_generalization_cohorts (automatic_grouping);

-- index: ix_bank_generalization_cohorts_eligible_for_lookup
CREATE INDEX ix_bank_generalization_cohorts_eligible_for_lookup ON bank_generalization_cohorts (eligible_for_lookup);

-- index: ix_bank_generalization_cohorts_family_id
CREATE INDEX ix_bank_generalization_cohorts_family_id ON bank_generalization_cohorts (family_id);

-- index: ix_bank_generalization_cohorts_model
CREATE INDEX ix_bank_generalization_cohorts_model ON bank_generalization_cohorts (model);

-- index: ix_bank_generalization_forms_banking_model
CREATE INDEX ix_bank_generalization_forms_banking_model ON bank_generalization_forms (banking_model);

-- index: ix_bank_generalization_forms_canonical_bank_id
CREATE INDEX ix_bank_generalization_forms_canonical_bank_id ON bank_generalization_forms (canonical_bank_id);

-- index: ix_bank_generalization_forms_enabled_for_lookup
CREATE INDEX ix_bank_generalization_forms_enabled_for_lookup ON bank_generalization_forms (enabled_for_lookup);

-- index: ix_bank_generalization_forms_level_code
CREATE INDEX ix_bank_generalization_forms_level_code ON bank_generalization_forms (level_code);

-- index: ix_bank_generalization_forms_safe_generalization_key
CREATE INDEX ix_bank_generalization_forms_safe_generalization_key ON bank_generalization_forms (safe_generalization_key);

-- index: ix_bank_generalization_forms_source_record_id
CREATE INDEX ix_bank_generalization_forms_source_record_id ON bank_generalization_forms (source_record_id);

-- index: ix_bank_generalization_forms_verification_status
CREATE INDEX ix_bank_generalization_forms_verification_status ON bank_generalization_forms (verification_status);

-- index: ix_bank_identity_model_records_automatic_grouping
CREATE INDEX ix_bank_identity_model_records_automatic_grouping ON bank_identity_model_records (automatic_grouping);

-- index: ix_bank_identity_model_records_bank_identity_id
CREATE INDEX ix_bank_identity_model_records_bank_identity_id ON bank_identity_model_records (bank_identity_id);

-- index: ix_bank_identity_model_records_banking_model_effective
CREATE INDEX ix_bank_identity_model_records_banking_model_effective ON bank_identity_model_records (banking_model_effective);

-- index: ix_bank_identity_model_records_banking_model_from_audit
CREATE INDEX ix_bank_identity_model_records_banking_model_from_audit ON bank_identity_model_records (banking_model_from_audit);

-- index: ix_bank_identity_model_records_canonical_bank_id
CREATE INDEX ix_bank_identity_model_records_canonical_bank_id ON bank_identity_model_records (canonical_bank_id);

-- index: ix_bank_identity_model_records_country_code
CREATE INDEX ix_bank_identity_model_records_country_code ON bank_identity_model_records (country_code);

-- index: ix_bank_identity_model_records_family_id
CREATE INDEX ix_bank_identity_model_records_family_id ON bank_identity_model_records (family_id);

-- index: ix_bank_identity_model_records_generalization_key
CREATE INDEX ix_bank_identity_model_records_generalization_key ON bank_identity_model_records (generalization_key);

-- index: ix_bank_identity_model_records_group_relation_status
CREATE INDEX ix_bank_identity_model_records_group_relation_status ON bank_identity_model_records (group_relation_status);

-- index: ix_bank_identity_model_records_historical_successor_record_id
CREATE INDEX ix_bank_identity_model_records_historical_successor_record_id ON bank_identity_model_records (historical_successor_record_id);

-- index: ix_bank_identity_model_records_import_action
CREATE INDEX ix_bank_identity_model_records_import_action ON bank_identity_model_records (import_action);

-- index: ix_bank_identity_model_records_model_evidence_tier
CREATE INDEX ix_bank_identity_model_records_model_evidence_tier ON bank_identity_model_records (model_evidence_tier);

-- index: ix_bank_identity_model_records_proposed_model_aware_key
CREATE INDEX ix_bank_identity_model_records_proposed_model_aware_key ON bank_identity_model_records (proposed_model_aware_key);

-- index: ix_bank_identity_model_records_record_class
CREATE INDEX ix_bank_identity_model_records_record_class ON bank_identity_model_records (record_class);

-- index: ix_bank_identity_model_records_relationship_to_family
CREATE INDEX ix_bank_identity_model_records_relationship_to_family ON bank_identity_model_records (relationship_to_family);

-- index: ix_bank_identity_model_records_review_required
CREATE INDEX ix_bank_identity_model_records_review_required ON bank_identity_model_records (review_required);

-- index: ix_bank_identity_model_records_safe_generalization_key
CREATE INDEX ix_bank_identity_model_records_safe_generalization_key ON bank_identity_model_records (safe_generalization_key);

-- index: ix_bank_model_aliases_alias_type
CREATE INDEX ix_bank_model_aliases_alias_type ON bank_model_aliases (alias_type);

-- index: ix_bank_model_aliases_automatic_grouping
CREATE INDEX ix_bank_model_aliases_automatic_grouping ON bank_model_aliases (automatic_grouping);

-- index: ix_bank_model_aliases_bank_identity_id
CREATE INDEX ix_bank_model_aliases_bank_identity_id ON bank_model_aliases (bank_identity_id);

-- index: ix_bank_model_aliases_banking_model_effective
CREATE INDEX ix_bank_model_aliases_banking_model_effective ON bank_model_aliases (banking_model_effective);

-- index: ix_bank_model_aliases_canonical_bank_id
CREATE INDEX ix_bank_model_aliases_canonical_bank_id ON bank_model_aliases (canonical_bank_id);

-- index: ix_bank_model_aliases_country_code
CREATE INDEX ix_bank_model_aliases_country_code ON bank_model_aliases (country_code);

-- index: ix_bank_model_aliases_enabled_for_lookup
CREATE INDEX ix_bank_model_aliases_enabled_for_lookup ON bank_model_aliases (enabled_for_lookup);

-- index: ix_bank_model_aliases_family_id
CREATE INDEX ix_bank_model_aliases_family_id ON bank_model_aliases (family_id);

-- index: ix_bank_model_aliases_language
CREATE INDEX ix_bank_model_aliases_language ON bank_model_aliases (language);

-- index: ix_bank_model_aliases_normalized_alias
CREATE INDEX ix_bank_model_aliases_normalized_alias ON bank_model_aliases (normalized_alias);

-- index: ix_bank_model_aliases_record_id
CREATE INDEX ix_bank_model_aliases_record_id ON bank_model_aliases (record_id);

-- index: ix_bank_model_aliases_review_required
CREATE INDEX ix_bank_model_aliases_review_required ON bank_model_aliases (review_required);

-- index: ix_bank_model_aliases_safe_generalization_key
CREATE INDEX ix_bank_model_aliases_safe_generalization_key ON bank_model_aliases (safe_generalization_key);

-- index: ix_bank_model_aliases_status
CREATE INDEX ix_bank_model_aliases_status ON bank_model_aliases (status);

-- index: ix_bank_model_do_not_merge_collision_type
CREATE INDEX ix_bank_model_do_not_merge_collision_type ON bank_model_do_not_merge (collision_type);

-- index: ix_bank_model_do_not_merge_record_a
CREATE INDEX ix_bank_model_do_not_merge_record_a ON bank_model_do_not_merge (record_a);

-- index: ix_bank_model_do_not_merge_record_b
CREATE INDEX ix_bank_model_do_not_merge_record_b ON bank_model_do_not_merge (record_b);

-- index: ix_bank_model_evidence_notes_record_id
CREATE INDEX ix_bank_model_evidence_notes_record_id ON bank_model_evidence_notes (record_id);

-- index: ix_bank_model_evidence_notes_risk
CREATE INDEX ix_bank_model_evidence_notes_risk ON bank_model_evidence_notes (risk);

-- index: ix_bank_model_relationship_evidence_from_record_id
CREATE INDEX ix_bank_model_relationship_evidence_from_record_id ON bank_model_relationship_evidence (from_record_id);

-- index: ix_bank_model_relationship_evidence_relationship_type
CREATE INDEX ix_bank_model_relationship_evidence_relationship_type ON bank_model_relationship_evidence (relationship_type);

-- index: ix_bank_model_relationship_evidence_to_record_id
CREATE INDEX ix_bank_model_relationship_evidence_to_record_id ON bank_model_relationship_evidence (to_record_id);

-- index: ix_bank_model_research_corrections_evidence_tier
CREATE INDEX ix_bank_model_research_corrections_evidence_tier ON bank_model_research_corrections (evidence_tier);

-- index: ix_bank_model_research_corrections_record_id
CREATE INDEX ix_bank_model_research_corrections_record_id ON bank_model_research_corrections (record_id);

-- index: ix_bank_relationships_child_bank_id
CREATE INDEX ix_bank_relationships_child_bank_id ON bank_relationships (child_bank_id);

-- index: ix_bank_relationships_parent_bank_id
CREATE INDEX ix_bank_relationships_parent_bank_id ON bank_relationships (parent_bank_id);

-- index: ix_bank_relationships_relationship_type
CREATE INDEX ix_bank_relationships_relationship_type ON bank_relationships (relationship_type);

-- index: ix_bank_relationships_source_record_id
CREATE INDEX ix_bank_relationships_source_record_id ON bank_relationships (source_record_id);

-- index: ix_bank_relationships_verification_status
CREATE INDEX ix_bank_relationships_verification_status ON bank_relationships (verification_status);

-- index: ix_banks_finance_model
CREATE INDEX ix_banks_finance_model ON banks (finance_model);

-- index: ix_candidate_provenance_candidate_id
CREATE INDEX ix_candidate_provenance_candidate_id ON candidate_provenance (candidate_id);

-- index: ix_corporation_aliases_corporation_id
CREATE INDEX ix_corporation_aliases_corporation_id ON corporation_aliases (corporation_id);

-- index: ix_corporation_aliases_enabled_for_lookup
CREATE INDEX ix_corporation_aliases_enabled_for_lookup ON corporation_aliases (enabled_for_lookup);

-- index: ix_corporation_aliases_language
CREATE INDEX ix_corporation_aliases_language ON corporation_aliases (language);

-- index: ix_corporation_aliases_normalized_alias
CREATE INDEX ix_corporation_aliases_normalized_alias ON corporation_aliases (normalized_alias);

-- index: ix_corporation_aliases_source_entity_id
CREATE INDEX ix_corporation_aliases_source_entity_id ON corporation_aliases (source_entity_id);

-- index: ix_corporation_aliases_source_entity_type
CREATE INDEX ix_corporation_aliases_source_entity_type ON corporation_aliases (source_entity_type);

-- index: ix_corporation_aliases_verification_status
CREATE INDEX ix_corporation_aliases_verification_status ON corporation_aliases (verification_status);

-- index: ix_corporation_entities_source_entity_id
CREATE INDEX ix_corporation_entities_source_entity_id ON corporation_entities (source_entity_id);

-- index: ix_corporation_entities_source_entity_type
CREATE INDEX ix_corporation_entities_source_entity_type ON corporation_entities (source_entity_type);

-- index: ix_corporation_entities_verification_status
CREATE INDEX ix_corporation_entities_verification_status ON corporation_entities (verification_status);

-- index: ix_generalization_candidates_canonical_entity_id
CREATE INDEX ix_generalization_candidates_canonical_entity_id ON generalization_candidates (canonical_entity_id);

-- index: ix_generalization_candidates_level_id
CREATE INDEX ix_generalization_candidates_level_id ON generalization_candidates (level_id);

-- index: ix_generalization_candidates_parent_candidate_id
CREATE INDEX ix_generalization_candidates_parent_candidate_id ON generalization_candidates (parent_candidate_id);

-- index: ix_generalization_candidates_scheme_id
CREATE INDEX ix_generalization_candidates_scheme_id ON generalization_candidates (scheme_id);

-- index: ix_generalization_candidates_taxonomy_code
CREATE INDEX ix_generalization_candidates_taxonomy_code ON generalization_candidates (taxonomy_code);

-- index: ix_generalization_levels_scheme_id
CREATE INDEX ix_generalization_levels_scheme_id ON generalization_levels (scheme_id);

-- index: ix_generalization_schemes_entity_type
CREATE INDEX ix_generalization_schemes_entity_type ON generalization_schemes (entity_type);

-- index: ix_government_aliases_entity_id
CREATE INDEX ix_government_aliases_entity_id ON government_aliases (entity_id);

-- index: ix_government_aliases_language
CREATE INDEX ix_government_aliases_language ON government_aliases (language);

-- index: ix_government_aliases_normalized_alias
CREATE INDEX ix_government_aliases_normalized_alias ON government_aliases (normalized_alias);

-- index: ix_government_candidate_reviews_dimension
CREATE INDEX ix_government_candidate_reviews_dimension ON government_candidate_reviews (dimension);

-- index: ix_government_candidate_reviews_entity_id
CREATE INDEX ix_government_candidate_reviews_entity_id ON government_candidate_reviews (entity_id);

-- index: ix_government_categories_parent_category_code
CREATE INDEX ix_government_categories_parent_category_code ON government_categories (parent_category_code);

-- index: ix_government_entities_country_iso
CREATE INDEX ix_government_entities_country_iso ON government_entities (country_iso);

-- index: ix_government_entities_identity_verification_status
CREATE INDEX ix_government_entities_identity_verification_status ON government_entities (identity_verification_status);

-- index: ix_government_entity_categories_category_code
CREATE INDEX ix_government_entity_categories_category_code ON government_entity_categories (category_code);

-- index: ix_government_entity_categories_entity_id
CREATE INDEX ix_government_entity_categories_entity_id ON government_entity_categories (entity_id);

-- index: ix_government_review_queue_entity_id
CREATE INDEX ix_government_review_queue_entity_id ON government_review_queue (entity_id);

-- index: ix_industry_categories_parent_code
CREATE INDEX ix_industry_categories_parent_code ON industry_categories (parent_code);

-- index: ix_industry_qid_mappings_industry_qid
CREATE INDEX ix_industry_qid_mappings_industry_qid ON industry_qid_mappings (industry_qid);

-- index: ix_industry_qid_mappings_review_status
CREATE INDEX ix_industry_qid_mappings_review_status ON industry_qid_mappings (review_status);

-- index: ix_industry_qid_mappings_sector_code
CREATE INDEX ix_industry_qid_mappings_sector_code ON industry_qid_mappings (sector_code);

-- index: ix_industry_qid_mappings_subcategory_code
CREATE INDEX ix_industry_qid_mappings_subcategory_code ON industry_qid_mappings (subcategory_code);

-- index: ix_isco_groups_parent_code
CREATE INDEX ix_isco_groups_parent_code ON isco_groups (parent_code);

-- index: ix_m49_regions_parent_code
CREATE INDEX ix_m49_regions_parent_code ON m49_regions (parent_code);

-- index: ix_nationality_alias_country_refs_iso2
CREATE INDEX ix_nationality_alias_country_refs_iso2 ON nationality_alias_country_refs (iso2);

-- index: ix_nationality_alias_review_provenance_alias_key
CREATE INDEX ix_nationality_alias_review_provenance_alias_key ON nationality_alias_review_provenance (alias_key);

-- index: ix_nationality_aliases_country_iso2
CREATE INDEX ix_nationality_aliases_country_iso2 ON nationality_aliases (country_iso2);

-- index: ix_nationality_aliases_language
CREATE INDEX ix_nationality_aliases_language ON nationality_aliases (language);

-- index: ix_nationality_aliases_normalized_alias
CREATE INDEX ix_nationality_aliases_normalized_alias ON nationality_aliases (normalized_alias);

-- index: ix_nationality_aliases_v2_country_qid
CREATE INDEX ix_nationality_aliases_v2_country_qid ON nationality_aliases_v2 (country_qid);

-- index: ix_nationality_aliases_v2_iso2
CREATE INDEX ix_nationality_aliases_v2_iso2 ON nationality_aliases_v2 (iso2);

-- index: ix_nationality_aliases_v2_language
CREATE INDEX ix_nationality_aliases_v2_language ON nationality_aliases_v2 (language);

-- index: ix_nationality_aliases_v2_normalized_alias
CREATE INDEX ix_nationality_aliases_v2_normalized_alias ON nationality_aliases_v2 (normalized_alias);

-- index: ix_nationality_candidate_refs_iso2
CREATE INDEX ix_nationality_candidate_refs_iso2 ON nationality_candidate_refs (iso2);

-- index: ix_nationality_countries_iso2
CREATE INDEX ix_nationality_countries_iso2 ON nationality_countries (iso2);

-- index: ix_nationality_deduplications_deduplication_type
CREATE INDEX ix_nationality_deduplications_deduplication_type ON nationality_deduplications (deduplication_type);

-- index: ix_nationality_deduplications_iso2
CREATE INDEX ix_nationality_deduplications_iso2 ON nationality_deduplications (iso2);

-- index: ix_nationality_deduplications_kept_country_qid
CREATE INDEX ix_nationality_deduplications_kept_country_qid ON nationality_deduplications (kept_country_qid);

-- index: ix_nationality_deduplications_kept_key
CREATE INDEX ix_nationality_deduplications_kept_key ON nationality_deduplications (kept_key);

-- index: ix_nationality_deduplications_language
CREATE INDEX ix_nationality_deduplications_language ON nationality_deduplications (language);

-- index: ix_nationality_deduplications_removed_country_qid
CREATE INDEX ix_nationality_deduplications_removed_country_qid ON nationality_deduplications (removed_country_qid);

-- index: ix_nationality_deduplications_removed_key
CREATE INDEX ix_nationality_deduplications_removed_key ON nationality_deduplications (removed_key);

-- index: ix_nationality_geo_joins_iso2
CREATE INDEX ix_nationality_geo_joins_iso2 ON nationality_geo_joins (iso2);

-- index: ix_nationality_geo_joins_join_status
CREATE INDEX ix_nationality_geo_joins_join_status ON nationality_geo_joins (join_status);

-- index: ix_nationality_geo_joins_natural_earth_id
CREATE INDEX ix_nationality_geo_joins_natural_earth_id ON nationality_geo_joins (natural_earth_id);

-- index: ix_natural_earth_countries_iso_a2
CREATE INDEX ix_natural_earth_countries_iso_a2 ON natural_earth_countries (iso_a2);

-- index: ix_natural_earth_countries_wikidata_qid
CREATE INDEX ix_natural_earth_countries_wikidata_qid ON natural_earth_countries (wikidata_qid);

-- index: ix_natural_earth_country_aliases_language
CREATE INDEX ix_natural_earth_country_aliases_language ON natural_earth_country_aliases (language);

-- index: ix_natural_earth_country_aliases_natural_earth_id
CREATE INDEX ix_natural_earth_country_aliases_natural_earth_id ON natural_earth_country_aliases (natural_earth_id);

-- index: ix_natural_earth_country_aliases_normalized_alias
CREATE INDEX ix_natural_earth_country_aliases_normalized_alias ON natural_earth_country_aliases (normalized_alias);

-- index: ix_occupation_aliases_language
CREATE INDEX ix_occupation_aliases_language ON occupation_aliases (language);

-- index: ix_occupation_aliases_normalized_alias
CREATE INDEX ix_occupation_aliases_normalized_alias ON occupation_aliases (normalized_alias);

-- index: ix_occupation_aliases_occupation_id
CREATE INDEX ix_occupation_aliases_occupation_id ON occupation_aliases (occupation_id);

-- index: ix_occupation_candidate_refs_occupation_id
CREATE INDEX ix_occupation_candidate_refs_occupation_id ON occupation_candidate_refs (occupation_id);

-- index: ix_occupation_isco_refs_isco_code
CREATE INDEX ix_occupation_isco_refs_isco_code ON occupation_isco_refs (isco_code);

-- index: ix_occupations_isco_code
CREATE INDEX ix_occupations_isco_code ON occupations (isco_code);

-- index: ix_organization_aliases_language
CREATE INDEX ix_organization_aliases_language ON organization_aliases (language);

-- index: ix_organization_aliases_normalized_alias
CREATE INDEX ix_organization_aliases_normalized_alias ON organization_aliases (normalized_alias);

-- index: ix_organization_aliases_organization_qid
CREATE INDEX ix_organization_aliases_organization_qid ON organization_aliases (organization_qid);

-- index: ix_organization_exclusions_organization_qid
CREATE INDEX ix_organization_exclusions_organization_qid ON organization_exclusions (organization_qid);

-- index: ix_organization_industries_industry_qid
CREATE INDEX ix_organization_industries_industry_qid ON organization_industries (industry_qid);

-- index: ix_organization_industries_mapping_id
CREATE INDEX ix_organization_industries_mapping_id ON organization_industries (mapping_id);

-- index: ix_organization_industries_organization_qid
CREATE INDEX ix_organization_industries_organization_qid ON organization_industries (organization_qid);

-- index: ix_organization_review_queue_organization_qid
CREATE INDEX ix_organization_review_queue_organization_qid ON organization_review_queue (organization_qid);

-- index: ix_organizations_identity_verification_status
CREATE INDEX ix_organizations_identity_verification_status ON organizations (identity_verification_status);

-- index: ix_organizations_import_decision
CREATE INDEX ix_organizations_import_decision ON organizations (import_decision);

-- index: ix_organizations_semantic_kind
CREATE INDEX ix_organizations_semantic_kind ON organizations (semantic_kind);
