"""Run several documents and print every important privacy-pipeline stage."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finaira import Entity, PipelineRequest, PrivacyPipeline
from finaira.debug_logger import DebugLogger
from finaira.env import load_project_env
from finaira.llm import GeminiLLM

load_project_env()


def entity(document, value, kind, identity, language=None, start_at=0):
    start = document.index(value, start_at)
    return Entity(kind, value, start, start + len(value), identity, language)


def run_document(number, title, document, entities, task):
    llm = GeminiLLM() if os.getenv("GEMINI_API_KEY") else None
    result = PrivacyPipeline(llm=llm, logger=DebugLogger("logs/multiple-documents.log", print_console=False)).run(
        PipelineRequest(document, entities, task, scope=f"document-{number}")
    )
    print("\n" + "=" * 70)
    print(f"DOCUMENT {number}: {title}\n" + "=" * 70)
    print("ORIGINAL DOCUMENT:\n" + document)
    print("\nSANITIZED DOCUMENT:\n" + str(result.protected_document))
    print("\nGEMINI RESPONSE (SANITIZED):\n" + str(result.sanitized_response))
    print("\nREVERSED RESPONSE:\n" + str(result.output))
    print(f"\nSTATUS: {result.status} | ERROR: {result.error_code}")


documents = []
doc = "Alice paid 12500 USD from account 123456."
documents.append(("English payment", doc, [entity(doc, "Alice", "PERSON_NAME", "p1"), entity(doc, "12500", "MONETARY_AMOUNT", "m1"), entity(doc, "123456", "BANK_ACCOUNT_NUMBER", "a1")], "Summarize the payment in one sentence."))
doc = "العميل أحمد عمره ٢٣ سنة ورقم حسابه 123456."
documents.append(("Arabic account review", doc, [entity(doc, "أحمد", "PERSON_NAME", "p2", "ar"), entity(doc, "٢٣", "AGE", "age2", "ar"), entity(doc, "123456", "BANK_ACCOUNT_NUMBER", "a2")], "لخص المستند باللغة العربية في نقطتين."))
doc = "The Egyptian customer عمره ٣١ سنة used account 654321."
documents.append(("Mixed-language customer", doc, [entity(doc, "Egyptian", "NATIONALITY", "n3"), entity(doc, "٣١", "AGE", "age3", "ar"), entity(doc, "654321", "BANK_ACCOUNT_NUMBER", "a3")], "Summarize the document briefly."))

for index, (title, document, entities, task) in enumerate(documents, 1):
    run_document(index, title, document, entities, task)

print("\nDetailed debug log: logs/multiple-documents.log")
