import pytest
from finaira import Entity, PipelineRequest, PrivacyPipeline
from finaira.llm import MockLLM
from finaira.policy import POLICY, Action
from finaira.transformer import transform_document
from finaira.audit import AuditLogger


def ent(text, typ, start, entity_id=None, language=None):
    return Entity(typ, text, start, start + len(text), entity_id, language)


def test_all_30_policies_and_only_three_actions():
    assert len(POLICY) == 30
    assert set(POLICY.values()) == set(Action)


def test_repeated_identity_reuses_token_and_restores():
    doc = "Adham paid Adham using 123456."
    entities = [ent("Adham", "PERSON_NAME", 0, "person-17"), ent("Adham", "PERSON_NAME", 11, "person-17"), ent("123456", "BANK_ACCOUNT_NUMBER", 23, "acct-42")]
    result = PrivacyPipeline().run(PipelineRequest(doc, entities))
    assert result.status == "PASS"
    assert result.output == doc
    assert result.protected_document.count("__FN_PERSON_0001__") == 2
    assert "__FN_BANK_ACCOUNT_0001__" in result.protected_document


def test_identical_text_different_entities_stay_distinct():
    doc = "Adham met Adham."
    entities = [ent("Adham", "PERSON_NAME", 0, "a"), ent("Adham", "PERSON_NAME", 10, "b")]
    result = PrivacyPipeline().run(PipelineRequest(doc, entities))
    assert result.protected_document == "__FN_PERSON_0001__ met __FN_PERSON_0002__."


def test_spans_prevent_substring_corruption():
    assert transform_document("1234", [(ent("123", "CUSTOMER_ID", 0), "X")]) == "X4"
    with pytest.raises(ValueError, match="OVERLAPPING_SPANS"):
        transform_document("1234", [(ent("123", "CUSTOMER_ID", 0), "X"), (ent("34", "CUSTOMER_ID", 2), "Y")])


def test_generalization_is_not_restored_and_cleanup_runs():
    doc = "Egyptian customer age 23 on 2026-10-23."
    entities = [ent("Egyptian", "NATIONALITY", 0, "n1"), ent("23", "AGE", doc.index("23"), "age1"), ent("2026-10-23", "DATE", doc.index("2026-10-23"), "date1")]
    result = PrivacyPipeline().run(PipelineRequest(doc, entities))
    assert result.status == "PASS"
    assert "Egyptian" not in result.output
    assert "years" in result.output
    assert "Q4 2026" in result.output


def test_database_backed_entity_uses_jev_selector(tmp_path):
    class FakeJEVSelector:
        def __init__(self):
            self.call = None

        def select_candidate(self, entity_type, value, sentence):
            self.call = (entity_type, value, sentence)
            return {"replacement": "Creative professional"}

    text = "She works as a technical director. Another sentence follows."
    start = text.index("technical director")
    selector = FakeJEVSelector()
    pipeline = PrivacyPipeline(
        jev_selector=selector,
        logger=AuditLogger(tmp_path / "pipeline.log", include_output=False),
    )

    result = pipeline.run(
        PipelineRequest(text, [ent("technical director", "OCCUPATION", start)])
    )

    assert result.status == "PASS"
    assert result.protected_document == "She works as a Creative professional. Another sentence follows."
    assert selector.call == (
        "OCCUPATION", "technical director", text
    )


def test_unknown_or_invented_placeholder_fails_before_restoration():
    result = PrivacyPipeline(MockLLM("invent")).run(PipelineRequest("Alice", [ent("Alice", "PERSON_NAME", 0, "p")]))
    assert result.status == "FAIL"
    assert result.error_code == "UNKNOWN_OR_INVENTED_PLACEHOLDER"
    assert result.output is None


def test_arabic_age_and_unicode():
    doc = "العمر ٢٣ سنة"
    start = doc.index("٢٣")
    result = PrivacyPipeline().run(PipelineRequest(doc, [Entity("AGE", "٢٣", start, start + 2, "a", "ar")]))
    assert result.status == "PASS"
    assert "18–24 سنة" in result.output


def test_missing_spans_fail_safely():
    result = PrivacyPipeline().run(PipelineRequest("Alice", [Entity("PERSON_NAME", "Alice")]))
    assert result.status == "FAIL" and result.error_code == "MISSING_SPAN"


def test_llm_exception_is_structured_and_cleans_up():
    class BrokenLLM:
        def complete(self, **kwargs):
            raise RuntimeError("provider failed")
    pipeline = PrivacyPipeline(BrokenLLM())
    result = pipeline.run(PipelineRequest("Alice", [ent("Alice", "PERSON_NAME", 0, "p")]))
    assert result.status == "FAIL" and result.error_code == "PIPELINE_ERROR"
    assert pipeline.last_vault_cleared is True


def test_audit_log_records_status_and_output(tmp_path):
    from finaira.audit import AuditLogger
    log_path = tmp_path / "pipeline.log"
    result = PrivacyPipeline(logger=AuditLogger(log_path)).run(
        PipelineRequest("Alice", [ent("Alice", "PERSON_NAME", 0, "p")])
    )
    line = log_path.read_text(encoding="utf-8").strip()
    assert result.status == "PASS"
    assert '"status": "PASS"' in line
    assert '"output": "Alice"' in line
