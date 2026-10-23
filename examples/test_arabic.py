import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finaira import Entity, PipelineRequest, PrivacyPipeline
from finaira.debug_logger import DebugLogger
from finaira.llm import GeminiLLM, OpenAIResponsesLLM
from finaira.env import load_project_env
import os

load_project_env()

document = "العميل أحمد عمره ٢٣ سنة ورقم حسابه 123456"
entities = [
    Entity("PERSON_NAME", "أحمد", document.index("أحمد"), document.index("أحمد") + len("أحمد"), "person-1", "ar"),
    Entity("AGE", "٢٣", document.index("٢٣"), document.index("٢٣") + len("٢٣"), "age-1", "ar"),
    Entity("BANK_ACCOUNT_NUMBER", "123456", document.index("123456"), document.index("123456") + len("123456"), "account-1", "ar"),
]

if os.getenv("GEMINI_API_KEY"):
    llm = GeminiLLM()
elif os.getenv("OPENAI_API_KEY"):
    llm = OpenAIResponsesLLM()
else:
    llm = None
result = PrivacyPipeline(
    llm=llm,
    logger=DebugLogger("logs/arabic-debug.log", print_console=True)
).run(PipelineRequest(document, entities, "لخص المستند باللغة العربية"))

print("STATUS:", result.status)
print("PROTECTED:", result.protected_document)
print("OUTPUT:", result.output)
print("ERROR:", result.error_code)
