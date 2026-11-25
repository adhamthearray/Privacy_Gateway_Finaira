from __future__ import annotations

from common import ROOT, write_json


FAMILIES = [
    "Customer identity summaries", "General customer profiling", "Financial profile summaries",
    "Income assessment", "Loan applications", "Mortgage eligibility", "Minimum-age eligibility",
    "Occupation-based eligibility", "Nationality-based eligibility", "Country-based eligibility",
    "Employment verification", "Employment-history summaries", "Job-title extraction",
    "Occupational classification", "Employer verification", "Corporate industry classification",
    "Corporate due diligence", "Banking relationship analysis", "Bank identity extraction",
    "Approved-bank checks", "Account-balance extraction", "Income threshold checks",
    "Debt-to-income calculations", "Loan-to-value calculations", "Loan amount extraction",
    "Monthly installment review", "Affordability assessment", "Cross-border transactions",
    "Country of residence verification", "Tax jurisdiction checks", "Citizenship verification",
    "KYC document review", "AML case summaries", "Transaction monitoring",
    "Suspicious activity explanations", "Fraud review", "Application timeline analysis",
    "Transaction chronology", "Date extraction", "Deadline calculations",
    "Employment tenure calculations", "Government authority identification",
    "Licensing and registration", "Regulator correspondence", "Complaint processing",
    "Customer-support responses", "Credit application drafting", "Audit report drafting",
    "Financial summarization", "Customer segmentation", "Risk-assessment documentation",
    "Contract review", "Financial comparison tasks", "Multi-step financial calculations",
    "Multi-condition eligibility", "Task-specific extraction", "General document summarization",
    "Exclusion-based summaries", "Out-of-scope tasks", "Broad or ambiguous requests",
    "Beneficiary-bank verification", "Corporate ownership review", "Payment due-date analysis",
    "Professional seniority assessment", "Regulatory jurisdiction routing",
]


def main() -> None:
    taxonomy = {
        "family_count": len(FAMILIES),
        "families": [
            {
                "id": f"TF_{index:03d}",
                "name": name,
                "subfamilies": [f"{name} — extraction", f"{name} — verification", f"{name} — explanation"],
            }
            for index, name in enumerate(FAMILIES, 1)
        ],
    }
    write_json(ROOT / "task_taxonomy.json", taxonomy)
    print(f"Wrote {len(FAMILIES)} task families")


if __name__ == "__main__":
    main()

