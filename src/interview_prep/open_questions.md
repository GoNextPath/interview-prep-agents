# Open questions from the evaluator seed data

Unresolved. Nothing in this note is a decision. The seed bank is `data/questions.json` and `data/answers.json`, loaded by `JsonSeedStore`. Shared types stay in `models.py`.

The seed set is eight behavioural questions and sixteen synthetic answers (one strong and one weak per question). Hand labels use `0.0`, `0.5`, and `1.0`. `overall_score` is the mean of the criterion scores, rounded to two decimals when the mean is `1/3` (`0.33`). A few answer texts assume a community-marketplace backend role ("guests and hosts", "profile and community") even though the question records have no company or role field.

## Should the evaluation be flexible depending on varied roles and hiring companies?

`Question` carries `topic`, `difficulty`, `prompt`, and `expected_points`. It has no role, level, or hiring company. The same rubric strings ("situation", "task", "action", "result", "what the team builds") are what the evaluator scores, and what feedback and metrics later read.

The seed already mixes a generic prompt with company-shaped answer text. A score can mean "covered the behavioural point" or "sounded right for this company," and those are different judgments.

Agreement still needed:

- Whether one rubric applies to every role, or rubrics vary by role family, level, or company.
- If they vary, whether that context lives in `expected_points` and `prompt` only, or in new shared fields. New fields on `models.py` need a reviewer from each affected team.
- Whether a company name dropped into an answer should change the score. The current labels do not reward naming a company by itself (`a-motivation-why-role-weak` scores `0.0`).

## How can the language in the answer be quantized reliably? What agreement to make?

The contract allows any float from `0.0` to `1.0`. This seed uses three levels only:

| Score | How this seed uses it |
| --- | --- |
| `0.0` | The point is missing. |
| `0.5` | The point is hinted at, without the specific detail the rationale names. |
| `1.0` | The point is present with a concrete detail. |

`0.5` is already load-bearing. Feedback treats `>= 0.5` as a strength and `< 0.5` as an improvement. Metrics sends `overall_score < 0.5` back to the question generator. A partial criterion can count as a strength while the round still counts as weak (`a-teamwork-cross-functional-weak` is `0.25` overall, with two criteria at `0.5`).

The keyword stub scores `1.0` when the criterion string appears in the answer and `0.0` otherwise. On the strong STAR answers, the words "situation", "task", "action", and "result" appear as labels, so the stub can score them perfectly without reading the story. On the background and motivation items, the criterion strings do not appear, so the stub scores them `0.0` against labels of `1.0`. On the weak STAR items, the stub scores `0.0` against labels of `0.25`, because partial credit has no keyword.

Agreement still needed:

- The scale the evaluator must emit: the three levels above, or any float in range.
- A written meaning for each level, shared by whoever labels data and whoever implements scoring, so two people giving the same answer land within the PRD band (80% of labels within ±0.1).
- Whether `0.5` on one criterion should keep counting as a strength once scores are no longer only `0` and `1`.
- That labels stay out of `Answer.text`. The loader already returns them separately. Putting the rubric or the expected score into the answer would leak the key to the scorer.

## Semantic model and analysis needed?

Reliable quantization of the language in these answers needs a judgment of meaning, not a substring check. The labels give credit for "names the current backend role and the traffic it serves" when the answer never contains the criterion string "current role and scope". Partial scores depend on missing specificity ("talked to some other teams" versus a described action).

Whether that judgment is a semantic model is unresolved, and it depends on the scale agreed above. The model provider is still an open decision in `docs/decisions.md`.

If a model is introduced, the seed set is the first hand-labelled check, not a harness. `evals/` does not run it yet. Any implementation still has to keep answer text separate from the rubric, refuse to let answer text raise its own score, validate model output into `Evaluation` before other agents see it, and mock the call in unit tests.
