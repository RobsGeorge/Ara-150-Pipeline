# Scripts behind the AJSE paper

Scripts that produce every number and data-bearing table of *Rule-Based Phonemization for
Arabic Dialects: A Grapheme-to-Phoneme Framework* from the engine and the data in `g2p/`.
They write LaTeX macros and table rows into a `generated/` folder next to themselves.

| Script | What it does |
|---|---|
| `build_tables.py <repo>/g2p [engine commit]` | Tables 1, 3, 4, A1–A3 and the numbers in the text (DMA, article checks, baseline, lexicon sizes, test count). With an engine commit, checks that the engine and data are identical to it. |
| `build_human_eval.py <repo>/g2p/human_eval/annotations/G2P_human_evaluation_150.xlsx` | Tables 5 and 6, the error classes and the human-evaluation numbers (accuracy, Wilson intervals, Cohen's κ). |
| `verify_algorithm1.py <repo>/g2p <csv>` | Algorithms 1–3 of the paper transcribed line by line, sharing only the lexicons with the engine; compares their output with the engine on every sentence of a split (`g2p/data/test_split.csv`, `dev_split.csv`). Expected: 0 mismatches. |
| `tools/baseline_and_ci.py` | Helper for the MSA-rule-set baseline. |

Example, from the repository root:

```bash
python -I paper/verify_algorithm1.py g2p g2p/data/test_split.csv
python paper/build_tables.py g2p
python paper/build_human_eval.py g2p/human_eval/annotations/G2P_human_evaluation_150.xlsx
```
