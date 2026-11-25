from __future__ import annotations


PROFILES = {
    "CORPORATION": {
        "family": "Employer and corporate analysis",
        "semi_anchor": "JOB_TITLE",
        "negative_anchor": "GOVERNMENT_ENTITY",
        "support": "Employer identity adds organizational context to the professional profile.",
        "relevant": {
            "en": "Identify the applicant's employer company and return only the corporation name.",
            "ar_msa": "حدّد الشركة التي يعمل لديها مقدم الطلب، وأعد اسم المؤسسة فقط.",
            "ar_egy": "هات اسم الشركة اللي العميل شغال فيها، من غير تفاصيل تانية.",
            "ar_en_mixed": "Extract اسم الـ employer company فقط من بيانات الطلب.",
        },
        "semi": {
            "en": "Summarize the applicant's professional background. Focus on the current position; include the employer company only when it adds useful career context.",
            "ar_msa": "لخّص الخلفية المهنية للمتقدم مع التركيز على منصبه الحالي، ويمكن ذكر جهة العمل إذا أضافت سياقاً مهنياً مفيداً.",
            "ar_egy": "لخّص خبرة العميل وركّز على المسمى الوظيفي، وممكن تذكر الشركة لو هتوضح مساره المهني.",
            "ar_en_mixed": "اعمل professional summary يركز على job title، والـ employer optional لو هيضيف career context.",
        },
        "irrelevant": {
            "en": "Identify the government regulator handling the case, not the company being regulated.",
            "ar_msa": "حدّد الجهة الحكومية الرقابية المسؤولة عن الحالة، ولا تذكر الشركة الخاضعة للرقابة.",
            "ar_egy": "طلع اسم الجهة الرقابية الحكومية بس، مش اسم الشركة اللي عليها المراجعة.",
            "ar_en_mixed": "Identify الـ government regulator فقط، not the regulated company.",
        },
    },
    "BANK": {
        "family": "Banking relationship analysis",
        "semi_anchor": "MONETARY_AMOUNT",
        "negative_anchor": "MONETARY_AMOUNT",
        "support": "Bank identity can contextualize which institution holds the reported financial figure.",
        "relevant": {
            "en": "Which bank does the customer use? Return the financial institution's name only.",
            "ar_msa": "ما البنك الذي يتعامل معه العميل؟ أعد اسم المؤسسة المالية فقط.",
            "ar_egy": "العميل بيتعامل مع بنك إيه؟ اكتب اسم البنك بس.",
            "ar_en_mixed": "What is اسم البنك اللي العميل بيستخدمه؟ Return the bank only.",
        },
        "semi": {
            "en": "Summarize the reported account balance. The bank name may be included only to clarify where that balance is held.",
            "ar_msa": "لخّص رصيد الحساب المبلّغ عنه، ويمكن ذكر اسم البنك فقط لتوضيح مكان الاحتفاظ بالرصيد.",
            "ar_egy": "لخّص رصيد الحساب، وممكن تقول اسم البنك بس لو هيوضح الرصيد موجود فين.",
            "ar_en_mixed": "Summarize رصيد الحساب؛ bank name optional بس لتوضيح where the balance is held.",
        },
        "irrelevant": {
            "en": "Extract the account balance only; do not identify the bank or any institution.",
            "ar_msa": "استخرج رصيد الحساب فقط، ولا تحدد البنك أو أي مؤسسة مالية.",
            "ar_egy": "هات رصيد الحساب بس، وماتقولش اسم البنك.",
            "ar_en_mixed": "Extract الـ account balance only، من غير bank name.",
        },
    },
    "GOVERNMENT_ENTITY": {
        "family": "Regulatory and authority review",
        "semi_anchor": "DATE",
        "negative_anchor": "CORPORATION",
        "support": "The authority name can orient a regulatory timeline without being required for chronology.",
        "relevant": {
            "en": "Identify the government authority that issued the licence decision.",
            "ar_msa": "حدّد الجهة الحكومية التي أصدرت قرار الترخيص.",
            "ar_egy": "قول اسم الجهة الحكومية اللي طلّعت قرار الترخيص.",
            "ar_en_mixed": "Identify الجهة الحكومية that issued the licence decision.",
        },
        "semi": {
            "en": "Build a chronology of the regulatory correspondence. Dates are required; include the authority name only when it helps orient an event.",
            "ar_msa": "أنشئ تسلسلاً زمنياً للمراسلات التنظيمية؛ التواريخ مطلوبة، ويمكن ذكر الجهة الرقابية لتوضيح سياق الحدث.",
            "ar_egy": "رتّب المكاتبات الرقابية بالوقت؛ التواريخ أساسية، وممكن تضيف اسم الجهة عشان توضح الحدث.",
            "ar_en_mixed": "Build a regulatory timeline؛ dates required والـ authority name optional for event context.",
        },
        "irrelevant": {
            "en": "Identify the corporation applying for the licence, not the government authority reviewing it.",
            "ar_msa": "حدّد الشركة المتقدمة للترخيص، وليس الجهة الحكومية التي تراجع الطلب.",
            "ar_egy": "هات اسم الشركة اللي مقدمة على الترخيص، مش الجهة الحكومية اللي بتراجع.",
            "ar_en_mixed": "Identify the applicant corporation، not الجهة الحكومية المراجِعة.",
        },
    },
    "DATE": {
        "family": "Timeline and date analysis",
        "semi_anchor": "GOVERNMENT_ENTITY",
        "negative_anchor": "AGE",
        "support": "A decision date can add timing context to authority identification without being required.",
        "relevant": {
            "en": "Determine when the loan was approved and report the approval date.",
            "ar_msa": "حدّد متى تمت الموافقة على القرض، وأعد تاريخ الموافقة.",
            "ar_egy": "شوف القرض اتوافق عليه إمتى واكتب تاريخ الموافقة.",
            "ar_en_mixed": "Find تاريخ الـ loan approval and return the date.",
        },
        "semi": {
            "en": "Identify the authority responsible for the decision. You may include the decision date as useful timing context.",
            "ar_msa": "حدّد الجهة المسؤولة عن القرار، ويمكن إضافة تاريخ القرار كسياق زمني مفيد.",
            "ar_egy": "حدد الجهة اللي خدت القرار، وممكن تضيف التاريخ عشان يوضح التوقيت.",
            "ar_en_mixed": "Identify الجهة المسؤولة؛ decision date optional as timing context.",
        },
        "irrelevant": {
            "en": "Check whether the applicant meets the minimum age; do not report any calendar dates.",
            "ar_msa": "تحقق من استيفاء مقدم الطلب للحد الأدنى للعمر، ولا تذكر أي تواريخ تقويمية.",
            "ar_egy": "شوف العميل عدى السن المطلوب ولا لأ، من غير ما تكتب أي تواريخ.",
            "ar_en_mixed": "Check minimum age eligibility، من غير reporting any dates.",
        },
    },
    "OCCUPATION": {
        "family": "Occupational classification",
        "semi_anchor": "JOB_TITLE",
        "negative_anchor": "JOB_TITLE",
        "support": "The broader profession can contextualize a specific current position.",
        "relevant": {
            "en": "Classify the applicant's broad occupation without naming the current job title.",
            "ar_msa": "صنّف المهنة العامة لمقدم الطلب دون ذكر المسمى الوظيفي الحالي.",
            "ar_egy": "صنّف مجال شغل العميل بشكل عام من غير المسمى الوظيفي الحالي.",
            "ar_en_mixed": "Classify مجال الـ occupation العام، not the current job title.",
        },
        "semi": {
            "en": "Extract the current job title. You may add the broader occupation only when it clarifies the professional field.",
            "ar_msa": "استخرج المسمى الوظيفي الحالي، ويمكن إضافة المهنة العامة إذا أوضحت المجال المهني.",
            "ar_egy": "طلع المسمى الوظيفي، وممكن تضيف المهنة العامة لو هتوضح المجال.",
            "ar_en_mixed": "Extract الـ current job title؛ occupation optional to clarify the field.",
        },
        "irrelevant": {
            "en": "Return the exact current job title only, not the person's general profession.",
            "ar_msa": "أعد المسمى الوظيفي الحالي بدقة فقط، وليس المهنة العامة للشخص.",
            "ar_egy": "هات المسمى الوظيفي الحالي بس، مش مجال المهنة العام.",
            "ar_en_mixed": "Return exact job title only، not the broad occupation.",
        },
    },
    "JOB_TITLE": {
        "family": "Employment detail extraction",
        "semi_anchor": "OCCUPATION",
        "negative_anchor": "OCCUPATION",
        "support": "A current title can enrich a broad occupational classification with seniority context.",
        "relevant": {
            "en": "Extract the applicant's exact current job title, including seniority.",
            "ar_msa": "استخرج المسمى الوظيفي الحالي بدقة، بما في ذلك الدرجة الوظيفية.",
            "ar_egy": "هات المسمى الوظيفي الحالي بالظبط ومعاه درجة الأقدمية.",
            "ar_en_mixed": "Extract الـ exact current job title including seniority.",
        },
        "semi": {
            "en": "Classify the applicant's occupation. The current job title may be included to clarify seniority within that profession.",
            "ar_msa": "صنّف مهنة مقدم الطلب، ويمكن ذكر المسمى الحالي لتوضيح مستوى الأقدمية داخل المهنة.",
            "ar_egy": "صنّف مهنة العميل، وممكن تضيف المسمى الحالي لو هيوضح مستوى الخبرة.",
            "ar_en_mixed": "Classify the occupation؛ current job title optional to show seniority.",
        },
        "irrelevant": {
            "en": "Classify the general occupation only; exclude the current position and rank.",
            "ar_msa": "صنّف المهنة العامة فقط، واستبعد المنصب الحالي والدرجة الوظيفية.",
            "ar_egy": "صنّف مجال الشغل بس، وسيبك من المنصب والدرجة الحالية.",
            "ar_en_mixed": "Classify broad occupation only؛ exclude current position and rank.",
        },
    },
    "NATIONALITY": {
        "family": "Citizenship and nationality checks",
        "semi_anchor": "COUNTRY",
        "negative_anchor": "COUNTRY",
        "support": "Citizenship can add cross-border context to a residence profile when explicitly permitted.",
        "relevant": {
            "en": "Verify the applicant's citizenship for the stated nationality eligibility rule.",
            "ar_msa": "تحقق من جنسية مقدم الطلب وفق شرط الأهلية المتعلق بالجنسية.",
            "ar_egy": "اتأكد من جنسية العميل عشان شرط الأهلية الخاص بالجنسية.",
            "ar_en_mixed": "Verify جنسية العميل for the nationality eligibility rule.",
        },
        "semi": {
            "en": "Prepare a residence profile for cross-border servicing. Country of residence is required; citizenship may be included as optional international context.",
            "ar_msa": "أعد ملفاً عن الإقامة لخدمة عابرة للحدود؛ بلد الإقامة مطلوب، ويمكن ذكر الجنسية كسياق دولي اختياري.",
            "ar_egy": "اعمل ملخص عن الإقامة للخدمة الدولية؛ بلد الإقامة أساسي والجنسية ممكن تتذكر كسياق إضافي.",
            "ar_en_mixed": "Prepare a cross-border residence profile؛ country required والجنسية optional context.",
        },
        "irrelevant": {
            "en": "Verify the country of residence only, not the applicant's citizenship or nationality.",
            "ar_msa": "تحقق من بلد الإقامة فقط، وليس جنسية مقدم الطلب.",
            "ar_egy": "اتأكد من بلد الإقامة بس، مش جنسية العميل.",
            "ar_en_mixed": "Verify country of residence only، not الجنسية.",
        },
    },
    "AGE": {
        "family": "Age eligibility",
        "semi_anchor": "OCCUPATION",
        "negative_anchor": "DATE",
        "support": "Age band can provide permitted demographic context to an occupational profile.",
        "relevant": {
            "en": "Determine whether the applicant is at least 21 years old.",
            "ar_msa": "حدّد ما إذا كان عمر مقدم الطلب لا يقل عن ٢١ عاماً.",
            "ar_egy": "شوف العميل عنده 21 سنة أو أكتر ولا لأ.",
            "ar_en_mixed": "Check if العميل meets the minimum age of 21.",
        },
        "semi": {
            "en": "Prepare an occupational profile. The profession is required; an age band may be added only as permitted demographic context.",
            "ar_msa": "أعد ملفاً مهنياً؛ المهنة مطلوبة، ويمكن إضافة الفئة العمرية كسياق ديموغرافي مسموح.",
            "ar_egy": "اعمل ملخص مهني؛ المهنة أساسية وممكن تضيف الفئة العمرية كسياق ديموغرافي مسموح.",
            "ar_en_mixed": "Prepare an occupation profile؛ profession required وage band optional demographic context.",
        },
        "irrelevant": {
            "en": "Report the loan approval date, not the applicant's age or date of birth.",
            "ar_msa": "أعد تاريخ الموافقة على القرض، وليس عمر مقدم الطلب أو تاريخ ميلاده.",
            "ar_egy": "هات تاريخ موافقة القرض، مش سن العميل ولا تاريخ ميلاده.",
            "ar_en_mixed": "Report loan approval date، not age or date of birth.",
        },
    },
    "MONETARY_AMOUNT": {
        "family": "Financial amount analysis",
        "semi_anchor": "BANK",
        "negative_anchor": "BANK",
        "support": "A financial figure can add scale context to a banking-relationship summary when permitted.",
        "relevant": {
            "en": "Extract the applicant's monthly income and compare it with the stated affordability threshold.",
            "ar_msa": "استخرج الدخل الشهري لمقدم الطلب وقارنه بحد القدرة المالية المحدد.",
            "ar_egy": "هات دخل العميل الشهري وقارنه بحد القدرة على السداد.",
            "ar_en_mixed": "Extract الدخل الشهري and compare it with the affordability threshold.",
        },
        "semi": {
            "en": "Summarize the customer's banking relationship. The bank identity is required; a balance range may be included as optional context about the relationship's scale.",
            "ar_msa": "لخّص العلاقة المصرفية للعميل؛ هوية البنك مطلوبة، ويمكن ذكر نطاق الرصيد كسياق اختياري عن حجم العلاقة.",
            "ar_egy": "لخّص علاقة العميل بالبنك؛ اسم البنك أساسي وممكن تضيف نطاق الرصيد كسياق عن حجم العلاقة.",
            "ar_en_mixed": "Summarize the banking relationship؛ bank required وbalance range optional for scale.",
        },
        "irrelevant": {
            "en": "Identify the customer's bank only; exclude balances, salary, loan value, and every other monetary figure.",
            "ar_msa": "حدّد بنك العميل فقط، واستبعد الأرصدة والراتب وقيمة القرض وأي مبلغ مالي آخر.",
            "ar_egy": "هات اسم بنك العميل بس، من غير رصيد أو مرتب أو مبلغ قرض.",
            "ar_en_mixed": "Identify the bank only؛ exclude balance, salary, loan amount, and all monetary figures.",
        },
    },
    "COUNTRY": {
        "family": "Country and jurisdiction checks",
        "semi_anchor": "CORPORATION",
        "negative_anchor": "NATIONALITY",
        "support": "Jurisdiction of incorporation can contextualize corporate due diligence.",
        "relevant": {
            "en": "Verify the customer's country of residence for the cross-border service rule.",
            "ar_msa": "تحقق من بلد إقامة العميل وفق قاعدة الخدمة العابرة للحدود.",
            "ar_egy": "اتأكد من بلد إقامة العميل عشان قاعدة الخدمة الدولية.",
            "ar_en_mixed": "Verify بلد الإقامة for the cross-border service rule.",
        },
        "semi": {
            "en": "Perform corporate due diligence focused on company identity. The country of incorporation may be included as optional jurisdictional context.",
            "ar_msa": "نفّذ فحصاً نافياً للجهالة يركز على هوية الشركة، ويمكن ذكر بلد التأسيس كسياق قضائي اختياري.",
            "ar_egy": "اعمل corporate due diligence يركز على هوية الشركة، وممكن تضيف بلد التأسيس كسياق قانوني.",
            "ar_en_mixed": "Perform corporate due diligence focused on company identity؛ incorporation country optional jurisdiction context.",
        },
        "irrelevant": {
            "en": "Verify the applicant's nationality only; do not infer or report any country of residence.",
            "ar_msa": "تحقق من جنسية مقدم الطلب فقط، ولا تستنتج أو تذكر بلد الإقامة.",
            "ar_egy": "اتأكد من جنسية العميل بس، وماتستنتجش بلد الإقامة.",
            "ar_en_mixed": "Verify الجنسية only؛ do not infer country of residence.",
        },
    },
}


LANGUAGE_META = {
    "en": ("English", "international", "professional banking English"),
    "ar_msa": ("Arabic", "Modern Standard Arabic", "formal administrative Arabic"),
    "ar_egy": ("Arabic", "Egyptian Arabic", "colloquial operational Egyptian"),
    "ar_en_mixed": ("Mixed Arabic-English", "Egyptian/English code-switch", "bilingual banking operations"),
}

