# Annotation guidelines

Judge whether the target **information type** contributes to the user's requested task. Do not imagine a customer document or a particular entity occurrence.

- `RELEVANT`: explicitly requested or materially necessary for a correct result.
- `SEMI_RELEVANT`: concrete, task-appropriate supporting context that the prompt authorizes, while the task remains correctly completable without it.
- `IRRELEVANT`: no meaningful contribution, or expressly excluded.
- `AMBIGUOUS_PENDING_REVIEW`: metadata only when requirements are insufficient or contradictory. It is not a model label.

Never use `SEMI_RELEVANT` merely because something “might help.” Record the primary task, why the type is optional, its concrete contribution, and where the prompt permits that context.

Review related types independently: corporation versus bank; government entity versus corporation; occupation versus job title; nationality versus country; date versus age; and monetary amount versus bank/currency. A keyword does not settle the label. “Bank balance” can require a monetary amount while excluding bank identity. “Country of residence” does not imply nationality.

For Arabic, correct unnatural wording without silently changing the task contract. Flag semantic drift if an edit changes required, optional, or excluded information. Review code-switching for plausible workplace usage rather than literal translation.

Each reviewer must use a stable reviewer ID. Independent reviews are append-only. Reviewers should not coordinate labels before initial submission. Disagreements require adjudication, and the adjudicator must provide a reason. Rejected prompts remain in history.

No generated or imported suggestion is approved by default. Only approved/adjudicated, non-ambiguous rows may enter official train, validation, or test exports.

