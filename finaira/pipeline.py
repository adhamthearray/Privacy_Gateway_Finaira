from .generalization import generalize
from .jev_selector import DB_ENTITY_TYPES, JEVSelector
from .llm import MockLLM
from .mapping import MappingVault
from .models import Entity, PipelineRequest, PipelineResult
from .policy import Action, get_action
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
        self.jev_selector = jev_selector or JEVSelector()
        self.last_vault_cleared = False

    def run(self, request: PipelineRequest) -> PipelineResult:
        vault = MappingVault(); self.last_vault_cleared = False
        trace = getattr(self.logger, "event", None)
        summary = getattr(self.logger, "pipeline_summary", None)
        protected = None
        llm_request = None
        response = None
        try:
            entities = [Entity.from_any(e) for e in request.entities]
            if trace:
                trace("request_received", document=request.document, entities=[e.__dict__ for e in entities], task=request.task)
            replacements = []
            for index, entity in enumerate(entities):
                if not entity.original_value: raise ValueError("EMPTY_ENTITY")
                identity = entity.entity_id or f"{entity.type}:{entity.occurrence_index if entity.occurrence_index is not None else index}"
                action = get_action(entity.type)
                if action == Action.PSEUDONYMIZE:
                    value = vault.token_for(entity, identity, action.value)
                elif action == Action.GENERALIZE:
                    if identity in vault.by_identity: value = vault.by_identity[identity].sanitized
                    else:
                        if entity.type in DB_ENTITY_TYPES and (entity.language or "en").lower() == "en":
                            selection = self.jev_selector.select_candidate(
                                entity.type,
                                entity.original_value,
                                request.document,
                            )
                            value = selection["replacement"]
                        else:
                            value = generalize(entity, identity, request.scope, entity.language, self.date_level)
                        # Avoid duplicating a unit already present immediately after the span.
                        following = request.document[entity.end:] if entity.end is not None else ""
                        if entity.type == "AGE" and entity.language == "ar" and following.lstrip().startswith("سنة"):
                            value = value.removesuffix(" سنة")
                        vault.record_generalization(entity, identity, value)
                else: value = entity.original_value
                replacements.append((entity, value))
                if trace:
                    trace("entity_processed", identity=identity, entity_type=entity.type,
                          original=entity.original_value, sanitized=value, action=action.value)
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
