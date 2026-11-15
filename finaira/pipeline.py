from .generalization import generalize
from .jev_selector import JEVSelector
from .llm import MockLLM
from .mapping import MappingVault
from .models import Entity, PipelineRequest, PipelineResult
from .policy import Action, canonical_entity_type, get_action
from .prompt import ARABIC_SYSTEM_PROMPT
from .restorer import restore
from .transformer import transform_document
from .validator import validate_response
from .audit import AuditLogger


class PrivacyPipeline:
    def __init__(self, llm=None, date_level: str = "QUARTER", logger=None, jev_selector=None):
        self.llm = llm or MockLLM()
        self.date_level = date_level
        self.logger = logger or AuditLogger()
        self._custom_jev_selector = jev_selector is not None
        self.jev_selector = jev_selector or JEVSelector()
        self.last_vault_cleared = False

    @staticmethod
    def _canonicalize_entity(entity: Entity) -> Entity:
        canonical = canonical_entity_type(entity.type)
        if canonical == entity.type:
            return entity
        return Entity(
            type=canonical,
            original_value=entity.original_value,
            start=entity.start,
            end=entity.end,
            entity_id=entity.entity_id,
            language=entity.language,
            occurrence_index=entity.occurrence_index,
        )

    def _broadest_database_candidate(self, entity: Entity):
        """Return the broadest safe verified candidate, or ``None``."""
        database = getattr(self.jev_selector, "db", None)
        if database is None:
            return None
        language = (entity.language or "en").lower()
        result = database.get_candidates(
            entity.type,
            entity.original_value,
            output_language=language,
            context={},
            include_review_candidates=False,
        )
        if result.get("resolution_status") not in {"MATCHED", "VERIFIED"}:
            return None
        eligible = []
        for candidate in result.get("candidates", []):
            metadata = candidate.get("metadata") or {}
            provenance = candidate.get("provenance") or metadata.get("provenance") or {}
            if candidate.get("is_suppression", metadata.get("is_suppression", False)):
                continue
            # Generalization must not return the original entity label. If a
            # broader label is unavailable in the requested language, use the
            # pseudonym fallback instead of leaking the exact value.
            if candidate.get("is_exact", metadata.get("is_exact", False)):
                continue
            if metadata.get("review_only") or provenance.get("requires_policy_approval"):
                continue
            if metadata.get("disclosure_approved") is False:
                continue
            if not candidate.get("available", True) or not candidate.get("representation"):
                continue
            eligible.append(candidate)
        if not eligible:
            return None
        return max(
            eligible,
            key=lambda row: (row.get("specificity_rank", 0), row.get("candidate_id", "")),
        )

    def _generalize_or_pseudonymize(self, entity, identity, request, vault):
        """Use the broadest verified DB representation, else a pseudonym."""
        database_types = {
            "BANK", "COUNTRY", "NATIONALITY", "CORPORATION",
            "GOVERNMENT_ENTITY", "JOB_TITLE", "OCCUPATION",
        }
        if entity.type in database_types and not self._custom_jev_selector:
            candidate = self._broadest_database_candidate(entity)
            if candidate is not None:
                return candidate["representation"], Action.GENERALIZE.value
            return vault.token_for(entity, identity, Action.PSEUDONYMIZE.value), Action.PSEUDONYMIZE.value

        # Preserve the injectable selector contract used by existing callers
        # and tests. A failed, suppressed, or unavailable selection becomes a
        # request-scoped pseudonym rather than an unsafe generic value.
        if entity.type in database_types and self._custom_jev_selector:
            try:
                selection = self.jev_selector.select_candidate(
                    entity.type, entity.original_value, request.document
                )
                selected = selection.get("selected_candidate") or {}
                if (
                    selection.get("replacement")
                    and not selected.get("is_suppression", False)
                    and selection.get("fallback_reason") is None
                ):
                    return selection["replacement"], Action.GENERALIZE.value
            except Exception:
                pass
            return vault.token_for(entity, identity, Action.PSEUDONYMIZE.value), Action.PSEUDONYMIZE.value

        try:
            return generalize(
                entity, identity, request.scope, entity.language, self.date_level
            ), Action.GENERALIZE.value
        except (ValueError, TypeError):
            return vault.token_for(entity, identity, Action.PSEUDONYMIZE.value), Action.PSEUDONYMIZE.value

    def run(self, request: PipelineRequest) -> PipelineResult:
        vault = MappingVault(); self.last_vault_cleared = False
        trace = getattr(self.logger, "event", None)
        summary = getattr(self.logger, "pipeline_summary", None)
        protected = None
        llm_request = None
        response = None
        try:
            entities = [self._canonicalize_entity(Entity.from_any(e)) for e in request.entities]
            if trace:
                trace("request_received", document=request.document, entities=[e.__dict__ for e in entities], task=request.task)
            replacements = []
            for index, entity in enumerate(entities):
                if not entity.original_value: raise ValueError("EMPTY_ENTITY")
                identity = entity.entity_id or f"{entity.type}:{entity.occurrence_index if entity.occurrence_index is not None else index}"
                action = get_action(entity.type)
                effective_action = action.value
                if action == Action.PSEUDONYMIZE:
                    value = vault.token_for(entity, identity, action.value)
                elif action == Action.GENERALIZE:
                    if identity in vault.by_identity: value = vault.by_identity[identity].sanitized
                    else:
                        value, effective_action = self._generalize_or_pseudonymize(
                            entity, identity, request, vault
                        )
                        # Avoid duplicating a unit already present immediately after the span.
                        following = request.document[entity.end:] if entity.end is not None else ""
                        if entity.type == "AGE" and entity.language == "ar" and following.lstrip().startswith("سنة"):
                            value = value.removesuffix(" سنة")
                        if effective_action == Action.GENERALIZE.value:
                            vault.record_generalization(entity, identity, value)
                else: value = entity.original_value
                replacements.append((entity, value))
                if trace:
                    trace("entity_processed", identity=identity, entity_type=entity.type,
                          original=entity.original_value, sanitized=value, action=effective_action)
            if trace:
                trace("mapping_created", mapping=vault.snapshot())
            protected = transform_document(request.document, replacements)
            if trace:
                trace("document_sanitized", sanitized_document=protected)
            llm_request = {"system": ARABIC_SYSTEM_PROMPT, "task": request.task, "document": protected}
            if trace:
                trace("llm_request_sent", request=llm_request)
            response = self.llm.complete(**{"system_prompt": llm_request["system"], "task": request.task, "protected_document": protected})
            if trace:
                trace("sanitized_response_received", sanitized_response=response)
            validation = validate_response(response, vault)
            if trace:
                trace("response_validated", status=validation.status, error_code=validation.error_code)
            if validation.status != "PASS":
                result = PipelineResult("FAIL", error_code=validation.error_code, protected_document=protected, sanitized_response=response, llm_request=llm_request)
                if summary:
                    summary(original_document=request.document, sanitized_document=protected,
                            sanitized_response=response, reversed_response=None,
                            status=result.status, error_code=result.error_code)
                self.logger.record(result)
                return result
            result = PipelineResult("PASS", output=restore(response, vault), protected_document=protected, sanitized_response=response, llm_request=llm_request)
            if trace:
                trace("response_restored", output=result.output)
            if summary:
                summary(original_document=request.document, sanitized_document=protected,
                        sanitized_response=response, reversed_response=result.output,
                        status=result.status, error_code=result.error_code)
            self.logger.record(result)
            return result
        except ValueError as exc:
            result = PipelineResult("FAIL", error_code=str(exc))
            if summary:
                summary(original_document=request.document, sanitized_document=protected,
                        sanitized_response=response, reversed_response=None,
                        status=result.status, error_code=result.error_code)
            self.logger.record(result)
            return result
        except Exception:
            # Do not expose provider details or sensitive values in the result.
            error = __import__("sys").exc_info()[1]
            if trace and error:
                trace("pipeline_exception", exception_type=type(error).__name__, exception_message=str(error))
            result = PipelineResult("FAIL", error_code="PIPELINE_ERROR", protected_document=protected, llm_request=llm_request)
            if summary:
                summary(original_document=request.document, sanitized_document=protected,
                        sanitized_response=response, reversed_response=None,
                        status=result.status, error_code=result.error_code)
            self.logger.record(result)
            return result
        finally:
            if trace:
                trace("cleanup", mapping_before_clear=vault.snapshot())
            vault.clear(); self.last_vault_cleared = True
