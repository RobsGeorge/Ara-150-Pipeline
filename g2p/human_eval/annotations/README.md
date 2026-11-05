# Human evaluation: released judgments

150 sentences of the development split (50 Egyptian, 50 Levantine, 50 Gulf), transcribed by
engine commit `c9fd7c0` and each judged independently by two native speakers of its dialect
(annotator codes EGY-A/B, LEV-A/B, GLF-A/B). Sentences on which the two annotators disagreed
were resolved by adjudication between them. The sample and its selection script are in the
parent folder (`sentences.csv`, `select_sentences.py`).

| File | Content |
|---|---|
| `judgments_150.csv`, `judgments_150.xlsx` | One row per sentence: both annotators' judgments, the initial disagreement, the final (adjudicated) judgment, and, for sentences judged incorrect, the error class, the wrong word, the engine's IPA of it and the correct IPA. |
| `annotator_*.xlsx` | The six annotation workbooks, including the annotation guide (Instructions sheet). |
| `G2P_human_evaluation_150.xlsx` | The adjudication workbook. |

Judgments and error details are as returned by the annotators. Their free-text notes are not
released: the note columns are empty, and file properties (author, editor, dates) were cleared.
The files are produced from the completed workbooks by `../publish_annotations.py`.

Results (from `build_human_eval.py`, supplementary material of the paper): 122 of 150 sentences
judged correct (81.3%, 95% Wilson interval 74.3–86.8); initial agreement 140/150, Cohen's
κ = 0.79 (Egyptian 0.76, Levantine 0.80, Gulf 0.79).

Released under the repository's MIT License, under the anonymous annotator codes the annotators
consented to.
