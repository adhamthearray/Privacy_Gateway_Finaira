from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline

from common import DATA, LABELS, REPORTS, read_jsonl
from import_examples import KEYWORDS


def features(row: dict) -> str:
    return f"{row['target_entity_type']} [SEP] {row['user_prompt']} [SEP] {row['task_requirements']}"


def keyword_predict(row: dict) -> str:
    text = row["user_prompt"].casefold()
    hit = any(term.casefold() in text for term in KEYWORDS[row["target_entity_type"]])
    excluded = any(cue in text for cue in ["do not", "exclude", "not the", "ليس", "دون", "مش", "من غير"])
    return "IRRELEVANT" if excluded and hit else ("RELEVANT" if hit else "IRRELEVANT")


def metrics(gold, predicted, rows):
    per_language = defaultdict(lambda: [[], []])
    per_type = defaultdict(lambda: [[], []])
    for truth, guess, row in zip(gold, predicted, rows):
        per_language[row["language_code"]][0].append(truth)
        per_language[row["language_code"]][1].append(guess)
        per_type[row["target_entity_type"]][0].append(truth)
        per_type[row["target_entity_type"]][1].append(guess)
    return {
        "accuracy": accuracy_score(gold, predicted),
        "macro_f1": f1_score(gold, predicted, labels=LABELS, average="macro", zero_division=0),
        "balanced_accuracy": balanced_accuracy_score(gold, predicted),
        "classification_report": classification_report(gold, predicted, labels=LABELS, output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(gold, predicted, labels=LABELS).tolist(),
        "label_order": LABELS,
        "per_language_accuracy": {key: accuracy_score(*values) for key, values in per_language.items()},
        "per_type_accuracy": {key: accuracy_score(*values) for key, values in per_type.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate baselines on human-approved held-out labels only.")
    parser.add_argument("--split", default="test", choices=["validation", "test"])
    args = parser.parse_args()
    all_rows = [
        row for row in read_jsonl(DATA / "generated" / "entity_decisions.jsonl")
        if row.get("approved_gold_label") and row.get("annotation_status") in {"APPROVED", "ADJUDICATED"}
    ]
    train = [row for row in all_rows if row["split"] == "train"]
    evaluation = [row for row in all_rows if row["split"] == args.split]
    report = {
        "status": "READY" if train and evaluation else "BLOCKED_PENDING_HUMAN_REVIEW",
        "evaluation_split": args.split,
        "approved_train_examples": len(train),
        "approved_evaluation_examples": len(evaluation),
        "models": {},
        "note": "No metric is ever computed from proposed synthetic labels.",
    }
    if train and evaluation:
        gold = [row["approved_gold_label"] for row in evaluation]
        majority = Counter(row["approved_gold_label"] for row in train).most_common(1)[0][0]
        report["models"]["majority"] = metrics(gold, [majority] * len(gold), evaluation)
        report["models"]["keyword"] = metrics(gold, [keyword_predict(row) for row in evaluation], evaluation)
        train_labels = [row["approved_gold_label"] for row in train]
        if len(set(train_labels)) == 3:
            model = Pipeline([
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
                ("classifier", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=20261126)),
            ])
            model.fit([features(row) for row in train], train_labels)
            predictions = model.predict([features(row) for row in evaluation])
            report["models"]["tfidf_logistic_regression"] = metrics(gold, predictions, evaluation)
        else:
            report["models"]["tfidf_logistic_regression"] = {"status": "BLOCKED_MISSING_TRAIN_CLASS"}
    (REPORTS / "baseline_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["status"])


if __name__ == "__main__":
    main()

