# Human evaluation: released judgments

150 sentences of the development split (50 Egyptian, 50 Levantine, 50 Gulf), transcribed by
engine commit `c9fd7c0` and each judged independently by two native speakers of its dialect
(annotator codes EGY-A/B, LEV-A/B, GLF-A/B). Sentences on which the two annotators disagreed
were resolved by discussion between the two annotators of the dialect. The sample and its
selection script are in the repository folder `g2p/human_eval/` (`sentences.csv`,
`select_sentences.py`).

| File | Content |
|---|---|
| `judgments_150.csv`, `judgments_150.xlsx` | One row per sentence: both annotators' judgments, the initial disagreement, the final (adjudicated) judgment, and, for sentences judged incorrect, the error class, the wrong word, the engine's IPA of it and the correct IPA. |
| `annotator_*.xlsx` | The six annotation workbooks, including the annotation guide (Instructions sheet). |
| `G2P_human_evaluation_150.xlsx` | The adjudication workbook: both annotators' judgments and structured error details, the adjudication, and the final judgment. |

The judgments are as returned by the annotators. Before release, the spelling of the workbooks'
text and their formatting were corrected with a generative AI tool (see the paper's statement on
generative AI); the judgments were not changed. The annotators' free-text notes and the
adjudication notes are not released (those columns are empty), and file properties (author,
editor, dates) were cleared. The files are produced from the completed workbooks by
`g2p/human_eval/publish_annotations.py`.

Results (from `paper/build_human_eval.py`): 122 of 150 sentences judged correct (81.3%,
95% Wilson interval 74.3–86.8); initial agreement 140/150, Cohen's κ = 0.79 pooled over the
three annotator pairs (Egyptian 0.76, Levantine 0.80, Gulf 0.79).

Released under the repository's MIT License, under the anonymous annotator codes the annotators
consented to.
