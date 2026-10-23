"""Run the POC4 test suite and several end-to-end examples with one command."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finaira import Entity, PipelineRequest, PrivacyPipeline
from finaira.debug_logger import DebugLogger
from finaira.env import load_project_env
from finaira.llm import GeminiLLM

load_project_env()


def entity(document, value, kind, identity, language=None, start_at=0):
    start = document.index(value, start_at)
    return Entity(kind, value, start, start + len(value), identity, language)


def run_case(name, document, entities, task, expected="PASS", llm=None):
    result = PrivacyPipeline(
        llm=llm,
        logger=DebugLogger("logs/test-suite.log", print_console=False),
    ).run(PipelineRequest(document, entities, task, scope=name))
    ok = result.status == expected
    print(f"{'PASS' if ok else 'FAIL'} | {name} | status={result.status} | error={result.error_code}")
    if result.output:
        print(f"  output: {result.output[:180].replace(chr(10), ' ')}")
    return ok


def main():
    print("Running unit tests...")
    unit = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT).returncode == 0
    print("\nRunning end-to-end examples...")
    cases = []

    doc = "Alice paid 123456."
    cases.append(run_case("english_pseudonyms", doc, [
        entity(doc, "Alice", "PERSON_NAME", "p1"),
        entity(doc, "123456", "BANK_ACCOUNT_NUMBER", "a1"),
    ], "Summarize the document."))

    doc = "العميل أحمد عمره ٢٣ سنة ورقم حسابه 123456."
    cases.append(run_case("arabic_generalization", doc, [
        entity(doc, "أحمد", "PERSON_NAME", "p2", "ar"),
        entity(doc, "٢٣", "AGE", "age2", "ar"),
        entity(doc, "123456", "BANK_ACCOUNT_NUMBER", "a2"),
    ], "لخص المستند باللغة العربية."))

    doc = "The Egyptian customer عمره ٣١ سنة used account 654321."
    cases.append(run_case("mixed_language", doc, [
        entity(doc, "Egyptian", "NATIONALITY", "n3"),
        entity(doc, "٣١", "AGE", "age3", "ar"),
        entity(doc, "654321", "BANK_ACCOUNT_NUMBER", "a3"),
    ], "Summarize in Arabic."))

    doc = "Alice paid 123456."
    cases.append(run_case("invalid_annotation", doc, [
        Entity("PERSON_NAME", "Alice", None, None, "bad"),
    ], "Summarize.", expected="FAIL"))

    if os.getenv("GEMINI_API_KEY"):
        doc = "العميل أحمد دفع 12500 جنيه مصري."
        cases.append(run_case("real_gemini_arabic", doc, [
            entity(doc, "أحمد", "PERSON_NAME", "p4", "ar"),
            entity(doc, "12500", "MONETARY_AMOUNT", "m4"),
        ], "لخص المستند بالعربية في نقطة واحدة.", llm=GeminiLLM()))
    else:
        print("SKIP | real_gemini_arabic | set GEMINI_API_KEY to enable")

    passed = unit and all(cases)
    print(f"\nOverall: {'PASS' if passed else 'FAIL'}")
    print("Detailed log: logs/test-suite.log")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
