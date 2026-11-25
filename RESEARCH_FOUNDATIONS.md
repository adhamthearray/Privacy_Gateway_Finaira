# Research foundations

The sources below inform construction methods; none supplies the project's three labels, and no external utterance is copied into the pilot. All pilot text is project-authored and remains pending human review.

## NLU++

[NLU++](https://aclanthology.org/2022.findings-naacl.154/) builds fine-grained banking and hotel ontologies with reusable generic and domain-specific intents, multi-intent utterances, and rich slots. Experts collected, filtered, and annotated examples, and the benchmark emphasizes low-data generalization. We borrow ontology-first task design, compositional requirements, and expert review. We do not equate its intents/slots with relevance labels. Its banking/hotel scope and English-centric source data do not establish Egyptian Arabic quality. The official [PolyAI dataset repository](https://github.com/PolyAI-LDN/task-specific-datasets) is CC BY 4.0; this project uses it only as methodological inspiration.

## MASSIVE

[MASSIVE](https://aclanthology.org/2023.acl-long.235/) provides roughly one million localized task-oriented utterances across 51 languages, aligned to a shared intent/slot schema. Its construction highlights localization rather than literal translation and consistent cross-language schemas. We borrow shared semantic specifications, language-aware rendering, and aligned multilingual evaluation. MASSIVE's domains and Arabic varieties do not guarantee Egyptian financial phrasing, and intent labels are not relevance judgments. The official [MASSIVE notice](https://github.com/alexa/massive/blob/main/NOTICE.md) states CC BY 4.0; no MASSIVE examples are reused.

## ArBanking77

[ArBanking77](https://aclanthology.org/2023.arabicnlp-1.22/) arabized and localized Banking77 through multiple annotator phases, producing MSA and Palestinian-dialect banking queries and adding noisy variants such as colloquial spelling. It retains 77 intent classes rather than this project's three relevance classes. We borrow staged localization, dialect-aware review, and robustness checks for spelling/noise. Palestinian coverage cannot substitute for Egyptian annotation. The paper reports that its source Banking77 data is CC BY 4.0; the current ArBanking77 distribution must be checked at acquisition time for its own applicable terms. This project copies no records.

## BANKING77

[BANKING77](https://arxiv.org/abs/2003.04807) is a fine-grained single-domain dataset of online banking queries assigned to 77 intents. It demonstrates the value of narrow, confusable financial categories and realistic customer wording. We borrow confusion-focused task families and banking hard negatives, not its class system or utterances. It is English, mostly short-form, and does not model optional relevance. The official [dataset repository](https://github.com/PolyAI-LDN/task-specific-datasets) identifies CC BY 4.0.

## CLINC150

[CLINC150/OOS](https://github.com/clinc/oos-eval) contains 150 in-scope intents plus out-of-scope examples and multiple data regimes. We borrow explicit out-of-scope task construction and challenge subsets. Its broad assistant domains do not provide financial entity-relevance annotation, multilingual Arabic coverage, or a middle relevance class. The repository states CC BY 3.0. No examples are imported.

## Self-Instruct

[Self-Instruct](https://aclanthology.org/2023.acl-long.754/) bootstraps instruction data from model-generated instructions, inputs, and outputs, then filters malformed and overly similar generations and evaluates on a separately authored expert set. We borrow generation/filter/review separation, similarity filtering, and provenance. We explicitly reject automatic promotion of synthetic labels to gold. Synthetic fluency is not semantic correctness, especially for dialect and exclusions.

## Evol-Instruct / WizardLM

[WizardLM/Evol-Instruct](https://arxiv.org/abs/2304.12244) iteratively increases instruction complexity through controlled evolution strategies. We borrow controlled transformations—conditions, exclusions, compound requests, and role framing—only when a semantic specification can verify that the label vector is preserved or intentionally flipped. Unconstrained evolution can drift requirements, so evolved records remain pending human review.

## ERASER

[ERASER](https://aclanthology.org/2020.acl-main.408/) standardizes rationale-annotated benchmarks and evaluates rationale plausibility and faithfulness. We borrow reviewer rationales, disagreement inspection, and eventual ablation/downstream tests. Rationales are research metadata, never model-state features, preventing direct gold leakage. A plausible reason is not proof that a model used the right evidence.

## Laya

The official [Laya repository](https://github.com/NandhaKishorM/laya) and [fine-tuning guide](https://github.com/NandhaKishorM/laya/blob/main/docs/finetune.md) document one-case-per-line JSONL with textual `state`, `questions`, and hard-label `expected`; `gold` is reserved for teacher probability distributions. They also document the `multilingual` base, option shuffling, loss selection, validation data, and `laya-train --dry-run`. We therefore export a deterministic textual state containing only task, explicit rules, target type, and a neutral definition. Proposed reasons and research metadata are excluded. We prepare, but do not start, fine-tuning. Calibration must be fit independently because choice-model probabilities can be overconfident. Laya's repository is Apache-2.0 at the time of this audit; package/model terms must be rechecked before distribution.

## What is original here

The exact ten-type ontology, three relevance definitions, 30 semantic task flips, 120 prompt renderings, complete ten-type matrices, and annotation workflow are original project artifacts. External licenses are recorded for provenance, but the current pilot does not rely on permission to redistribute any source dataset because it reuses no source examples.

