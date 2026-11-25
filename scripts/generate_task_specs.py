from __future__ import annotations

from catalog import PROFILES
from common import DATA, ENTITY_TYPES, ensure_dirs, write_jsonl


def label_vector(target: str, mode: str, anchor: str) -> tuple[dict[str, str], dict[str, str]]:
    labels = {entity: "IRRELEVANT" for entity in ENTITY_TYPES}
    reasons = {
        entity: "The task neither requests nor materially depends on this information type."
        for entity in ENTITY_TYPES
    }
    if mode == "relevant":
        labels[target] = "RELEVANT"
        reasons[target] = "The requested output explicitly requires this information type."
    elif mode == "semi":
        labels[target] = "SEMI_RELEVANT"
        labels[anchor] = "RELEVANT"
        reasons[target] = PROFILES[target]["support"]
        reasons[anchor] = "This is the primary information type required to complete the task."
    else:
        labels[anchor] = "RELEVANT"
        reasons[target] = "The task explicitly excludes this related information type."
        reasons[anchor] = "This related but distinct information type is explicitly requested."
    return labels, reasons


def build_specs() -> list[dict]:
    specs = []
    for target, profile in PROFILES.items():
        for mode in ("relevant", "semi", "irrelevant"):
            anchor = target if mode == "relevant" else profile[
                "semi_anchor" if mode == "semi" else "negative_anchor"
            ]
            labels, reasons = label_vector(target, mode, anchor)
            spec_id = f"SPEC_{target}_{mode.upper()}"
            specs.append(
                {
                    "specification_id": spec_id,
                    "task_family": profile["family"],
                    "task_subfamily": f"{target.lower()}_{mode}",
                    "task_objective": f"Exercise {mode} relevance for {target} against {anchor}.",
                    "expected_output": "A response limited to the information contract stated in the prompt.",
                    "required_information": [anchor],
                    "optional_supporting_information": [target] if mode == "semi" else [],
                    "explicitly_excluded_information": [target] if mode == "irrelevant" else [],
                    "task_requirements": (
                        f"Primary type: {anchor}. "
                        + (f"{target} is optional supporting context." if mode == "semi" else "")
                        + (f"{target} is explicitly excluded." if mode == "irrelevant" else "")
                    ).strip(),
                    "task_conditions": ["Use only the requirements expressed in the user task."],
                    "proposed_labels_for_all_10_types": labels,
                    "proposed_reasons_for_all_10_types": reasons,
                    "ambiguity_flags": [],
                    "provenance": "human-designed semantic seed; synthetic; no customer data",
                    "human_approval_status": "PENDING_REVIEW",
                    "target_entity_type": target,
                    "contrast_mode": mode,
                    "prompts": profile[mode],
                }
            )
    def complete(labels: dict[str, str], relevant_reason: str) -> tuple[dict[str, str], dict[str, str]]:
        vector = {entity: labels.get(entity, "IRRELEVANT") for entity in ENTITY_TYPES}
        reasons = {
            entity: (relevant_reason if vector[entity] == "RELEVANT" else "The output contract does not require this information type.")
            for entity in ENTITY_TYPES
        }
        return vector, reasons

    supplemental = [
        {
            "id": "SPEC_COMPOSITE_LOAN_REVIEW", "family": "Multi-condition eligibility",
            "subfamily": "loan_institution_amount_and_timeline", "required": ["BANK", "MONETARY_AMOUNT", "DATE"],
            "objective": "Review lender, principal, and approval timing as three mandatory fields.",
            "requirements": "Return the bank, loan amount, and approval date; all three fields are mandatory.",
            "prompts": {
                "en": "Prepare the loan review with the lender's bank name, approved principal, and approval date. All three fields are mandatory.",
                "ar_msa": "أعد مراجعة القرض متضمنة اسم البنك المُقرض ومبلغ أصل القرض المعتمد وتاريخ الموافقة؛ الحقول الثلاثة إلزامية.",
                "ar_egy": "اعمل مراجعة للقرض فيها اسم البنك والمبلغ اللي اتوافق عليه وتاريخ الموافقة، والتلاتة لازم يتكتبوا.",
                "ar_en_mixed": "Prepare the loan review with اسم البنك، approved amount، وapproval date؛ all required.",
            },
        },
        {
            "id": "SPEC_OUT_OF_SCOPE_REWRITE", "family": "Out-of-scope tasks",
            "subfamily": "style_only_rewrite", "required": [],
            "objective": "Rewrite supplied prose for style without extracting any entity information.",
            "requirements": "Change tone only; do not extract, classify, verify, or add factual fields.",
            "prompts": {
                "en": "Rewrite the supplied paragraph in a more formal tone without extracting or adding any factual fields.",
                "ar_msa": "أعد صياغة الفقرة المقدمة بأسلوب أكثر رسمية دون استخراج أو إضافة أي حقائق.",
                "ar_egy": "صيّغ الفقرة بشكل أرسَم من غير ما تستخرج أو تزود أي بيانات.",
                "ar_en_mixed": "Rewrite الفقرة in a formal tone بس، without extracting any facts.",
            },
        },
        {
            "id": "SPEC_CONDITIONAL_CROSS_BORDER", "family": "Cross-border transactions",
            "subfamily": "conditional_country_amount_review", "required": ["COUNTRY", "MONETARY_AMOUNT"],
            "objective": "Apply a fictional cross-border rule using destination country and transaction amount.",
            "requirements": "If the transfer is cross-border, report destination country and amount to evaluate the stated fictional threshold.",
            "prompts": {
                "en": "If the transfer is cross-border, report its destination country and amount, then check the fictional 50,000 EGP review threshold.",
                "ar_msa": "إذا كان التحويل عابراً للحدود، فاذكر بلد الوجهة والمبلغ ثم تحقق من حد المراجعة الافتراضي البالغ ٥٠٬٠٠٠ جنيه.",
                "ar_egy": "لو التحويل دولي، هات بلد الوجهة والمبلغ وشوف عدى حد المراجعة الافتراضي 50 ألف جنيه ولا لأ.",
                "ar_en_mixed": "If التحويل cross-border، report destination country والمبلغ against the fictional 50k EGP threshold.",
            },
        },
        {
            "id": "SPEC_DUAL_GEOGRAPHY", "family": "KYC document review",
            "subfamily": "citizenship_and_residence_distinction", "required": ["NATIONALITY", "COUNTRY"],
            "objective": "Return citizenship and residence country as distinct mandatory fields.",
            "requirements": "Do not infer one field from the other; both are required.",
            "prompts": {
                "en": "For KYC, report citizenship and country of residence as separate fields; do not infer one from the other.",
                "ar_msa": "لأغراض اعرف عميلك، أعد الجنسية وبلد الإقامة كحقلين منفصلين، ولا تستنتج أحدهما من الآخر.",
                "ar_egy": "في مراجعة KYC هات الجنسية وبلد الإقامة كل واحد لوحده، وماتستنتجش واحد من التاني.",
                "ar_en_mixed": "For KYC، report الجنسية وcountry of residence separately؛ no inference between them.",
            },
        },
        {
            "id": "SPEC_COMPOUND_EMPLOYMENT", "family": "Employment-history summaries",
            "subfamily": "employer_title_occupation", "required": ["CORPORATION", "JOB_TITLE", "OCCUPATION"],
            "objective": "Summarize employer, exact position, and broad profession without collapsing the concepts.",
            "requirements": "Employer, exact job title, and broad occupation are each mandatory.",
            "prompts": {
                "en": "Summarize employment using three separate fields: employer company, exact job title, and broad occupation.",
                "ar_msa": "لخّص العمل في ثلاثة حقول منفصلة: الشركة صاحبة العمل، والمسمى الوظيفي الدقيق، والمهنة العامة.",
                "ar_egy": "لخّص الشغل في تلات خانات: الشركة، المسمى الوظيفي بالظبط، ومجال المهنة العام.",
                "ar_en_mixed": "Summarize employment in three fields: الشركة، exact job title، وbroad occupation.",
            },
        },
        {
            "id": "SPEC_MULTIPLE_AMOUNTS", "family": "Multi-step financial calculations",
            "subfamily": "income_debt_installment", "required": ["MONETARY_AMOUNT"],
            "objective": "Use several monetary roles in a debt-to-income computation.",
            "requirements": "Monthly income, debt payment, and proposed installment are all monetary inputs; do not treat them as interchangeable.",
            "prompts": {
                "en": "Calculate debt-to-income using monthly salary, existing debt payment, and proposed installment; keep the three monetary roles separate.",
                "ar_msa": "احسب نسبة الدين إلى الدخل باستخدام الراتب الشهري ودفعة الدين الحالية والقسط المقترح، مع فصل الأدوار المالية الثلاثة.",
                "ar_egy": "احسب نسبة الدين للدخل من المرتب الشهري وقسط الدين الحالي والقسط الجديد، وخلي كل مبلغ في دوره.",
                "ar_en_mixed": "Calculate DTI from المرتب الشهري، existing debt payment، وproposed installment؛ keep each amount role separate.",
            },
        },
    ]
    for item in supplemental:
        labels, reasons = complete({entity: "RELEVANT" for entity in item["required"]}, "This information type is an explicit mandatory input or output.")
        specs.append({
            "specification_id": item["id"], "task_family": item["family"], "task_subfamily": item["subfamily"],
            "task_objective": item["objective"], "expected_output": "The fields or transformation stated in the prompt.",
            "required_information": item["required"], "optional_supporting_information": [],
            "explicitly_excluded_information": [], "task_requirements": item["requirements"],
            "task_conditions": [item["requirements"]], "proposed_labels_for_all_10_types": labels,
            "proposed_reasons_for_all_10_types": reasons, "ambiguity_flags": [],
            "provenance": "human-designed composite semantic seed; synthetic; no customer data",
            "human_approval_status": "PENDING_REVIEW", "target_entity_type": item["required"][0] if item["required"] else "COUNTRY",
            "contrast_mode": "composite", "contrast_group_id": f"CG_{item['id']}", "prompts": item["prompts"],
        })
    return specs


def main() -> None:
    ensure_dirs()
    specs = build_specs()
    write_jsonl(DATA / "task_specs" / "pilot_task_specs.jsonl", specs)
    print(f"Wrote {len(specs)} semantic task specifications")


if __name__ == "__main__":
    main()

