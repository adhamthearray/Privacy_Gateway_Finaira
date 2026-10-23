import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finaira import Entity, PipelineRequest, PrivacyPipeline
from finaira.debug_logger import DebugLogger
from finaira.env import load_project_env
from finaira.llm import GeminiLLM, OpenAIResponsesLLM

load_project_env()

document = """تقدم العميل أحمد حسن، ويبلغ من العمر ٢٣ سنة، بطلب مراجعة حركة حسابه البنكي.
يستخدم العميل الحساب رقم 123456 لدى بنك النيل، ويعيش في مدينة القاهرة ويحمل الجنسية المصرية.

خلال شهر أكتوبر، ظهرت ثلاث معاملات مالية. كانت المعاملة الأولى بقيمة 12500 جنيه مصري لدفع رسوم دراسية،
وكانت المعاملة الثانية بقيمة 3400 جنيه مصري لشراء مستلزمات منزلية. أما المعاملة الثالثة فكانت تحويلًا
إلى حساب ادخاري بقيمة 7800 جنيه مصري. أوضح العميل أن جميع المعاملات تمت من هاتفه الشخصي، باستثناء
المعاملة الثالثة التي تمت من فرع مدينة نصر بعد التحقق من هويته.

طلب العميل أحمد حسن معرفة سبب ظهور التنبيه الأمني، وتأكيد ما إذا كانت المعاملات الثلاث قد اكتملت بنجاح.
كما طلب إرسال نتيجة المراجعة إلى بريده الإلكتروني بعد انتهاء الفحص."""


def annotated(value, entity_type, entity_id, language=None, start_at=0):
    start = document.index(value, start_at)
    return Entity(entity_type, value, start, start + len(value), entity_id, language)


entities = [
    annotated("أحمد حسن", "PERSON_NAME", "person-1", "ar"),
    annotated("أحمد حسن", "PERSON_NAME", "person-1", "ar", document.index("أحمد حسن") + 1),
    annotated("٢٣", "AGE", "age-1", "ar"),
    annotated("123456", "BANK_ACCOUNT_NUMBER", "account-1"),
    annotated("بنك النيل", "BANK", "bank-1", "ar"),
    annotated("القاهرة", "CITY", "city-1", "ar"),
    annotated("المصرية", "NATIONALITY", "nationality-1", "ar"),
    annotated("12500", "MONETARY_AMOUNT", "amount-1"),
    annotated("3400", "MONETARY_AMOUNT", "amount-2"),
    annotated("7800", "MONETARY_AMOUNT", "amount-3"),
]

if os.getenv("GEMINI_API_KEY"):
    llm = GeminiLLM()
elif os.getenv("OPENAI_API_KEY"):
    llm = OpenAIResponsesLLM()
else:
    llm = None

result = PrivacyPipeline(
    llm=llm,
    logger=DebugLogger("logs/arabic-big-debug.log", print_console=True),
).run(PipelineRequest(
    document,
    entities,
    "لخص المستند باللغة العربية في نقاط واضحة، واذكر عدد المعاملات وقيمها وحالة طلب العميل. لا تعرض المعرّفات البديلة أو القيم الحساسة الأصلية.",
))

print("STATUS:", result.status)
print("PROTECTED:", result.protected_document)
print("OUTPUT:", result.output)
print("ERROR:", result.error_code)
