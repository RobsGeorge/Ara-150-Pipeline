# Ara-150: Multi-Dialect Arabic TTS Corpus — AraForge Pipeline

<div align="center">

[![License: MIT](https://img.shields.io/badge/Code-MIT-green.svg)](LICENSE)
[![Dataset License](https://img.shields.io/badge/Corpus-CC--BY--NC--SA%204.0-blue.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![HuggingFace](https://img.shields.io/badge/🤗%20Dataset-Ara--150-orange)](https://huggingface.co/datasets/robsgeorge/Ara_150_Multi_Dialect_TTS)
[![Tests](https://img.shields.io/badge/G2P%20tests-118%2F118%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/tested%20with-Python%203.13-blue)]()

**Ara-150** is a ~152-hour multi-dialect Arabic speech corpus designed for
Text-to-Speech (TTS) research, accompanied by an automated processing pipeline
(AraForge) and a rule-based G2P phonemization engine.

</div>

---

## Key numbers

| Dialect | Hours | Clips | Speakers |
|---------|------:|------:|------:|
| Egyptian (EGY) | 78.0 | 109,014 | 4 |
| Khaliji / Gulf (KHA) | 25.7 | 36,569 | 3 |
| Levantine (LEV) | 24.8 | 30,308 | 19 |
| Modern Standard Arabic (MSA) | 23.4 | 26,442 | 1 |
| **Total** | **151.9** | **202,333** | **27** |

- **Audio:** 22.05 kHz, stereo, 16-bit WAV — TTS-suitable quality
- **Transcription:** Whisper large-v3 · CER 7.02% (pre-human verification)
- **Phonemes:** rule-based G2P engine (rule application verified on the test split: 100% Dialect Marker Accuracy and article-rule consistency)
- **Speakers:** pseudonymous (SPK_NNN) · age, gender, dialect, emotion per clip
- **License:** corpus CC-BY-NC-SA 4.0 · code MIT

---

## Repository structure

```
Ara-150-Pipeline/
│
├── pipeline_notebooks/
│   ├── 01_ingestion_and_processing.ipynb     # Whisper + VAD + segmentation
│   ├── 02_metadata_and_phonemization.ipynb   # G2P + ECAPA-TDNN speaker clustering
│   ├── 03_dataset_consolidation.ipynb        # Final merge + quality filtering
│   └── Phonemization_demo.ipynb              # G2P demo
│
├── g2p/
│   ├── arabic_g2p_rules.py      # Core G2P engine (4 dialects)
│   ├── test_arabic_g2p.py       # 118 tests: run `python g2p/test_arabic_g2p.py`
│   ├── diacritize_then_g2p.py   # Full-IPA pipeline (CAMeL Tools / Mishkal)
│   ├── regenerate_table3.py     # Occurrence-level scorer (DMA, article checks, self-test)
│   ├── make_table3_rows.py      # Qualitative examples (Table 4 of the paper)
│   ├── IPA_Phonemes.xlsx        # IPA reference workbook (mapping, rules, worked examples)
│   ├── tools/                   # refresh_ipa_workbook.py
│   ├── data/                    # test and development splits
│   ├── results/                 # scorer and example outputs
│   └── human_eval/              # sample, workbooks, released judgments (annotations/)
│
├── paper/                       # scripts that generate the paper's numbers and tables
├── Phonemization.ipynb          # G2P notebook
├── README.md
├── LICENSE                      # MIT (code)
├── requirements.txt
└── .gitignore
```

---

## Quickstart — G2P engine

```python
from g2p.arabic_g2p_rules import transcribe_protected

# Single sentence
print(transcribe_protected("الليل والنهار", "Egyptian"))
# → /e-lljl/ /we-nnhaːɾ/

print(transcribe_protected("قال المدرس", "Khaliji Arabic"))
# → /ɡaːl/ /ɪl-mdrs/

# Diacritized input: short vowels are realized as written
print(transcribe_protected("مَدْرَسَة", "Modern Standard Arabic (MSA)"))
# → /madrasa/
```

With automatic diacritization (requires `pip install camel-tools` and its MSA model):

```bash
python g2p/diacritize_then_g2p.py --text "مدرسة" --dialect MSA --backend camel
# → /madrasati/   (CAMeL Tools restores the MSA case ending)
```

Supported dialects: `"Egyptian"` · `"Khaliji Arabic"` · `"Levantine Arabic"` · `"Modern Standard Arabic (MSA)"`

---

## Run the validation tests

```bash
pip install -r requirements.txt
python g2p/test_arabic_g2p.py
# ==== 118/118 tests passed ====
```

---

## Run the full AraForge pipeline

Open the notebooks in Google Colab (recommended) or JupyterLab in order:

| Step | Notebook | Input | Output |
|------|----------|-------|--------|
| 1 | `01_ingestion_and_processing.ipynb` | Raw audio files | Segmented WAV clips |
| 2 | `02_metadata_and_phonemization.ipynb` | Clips + transcripts | `metadata_with_phonemes.csv` |
| 3 | `03_dataset_consolidation.ipynb` | Per-speaker CSVs | `master_metadata.csv` |

Each notebook mounts Google Drive; edit the Drive paths in its first cells (e.g. `DB_ROOT`) to point to your own folders.

---

## Regenerate the evaluation tables of the G2P paper

```bash
cd g2p
python test_arabic_g2p.py                        # 118 unit tests
python regenerate_table3.py --self-test          # sabotages each rule; the scorer must report misses
python regenerate_table3.py --test-csv data/test_split.csv --output results/table2_regenerated.csv
python make_table3_rows.py                       # qualitative-comparison rows, emitted from the engine
```

Script names follow the table numbering of the first submission: in the revised
manuscript, `regenerate_table3.py` produces Table 3 and Table A3 (Dialect Marker
Accuracy and definite-article rules), and `make_table3_rows.py` produces Table 4
(qualitative comparison).

`data/test_split.csv` is the held-out test partition (20,606 sentences; ID, dialect,
transcript). In 107 Egyptian rows of the source metadata, later records had been
concatenated into the transcript field by an export error; those transcripts are
truncated to the row's own sentence. Three rows have empty transcripts and are skipped.

The scorer reports, per dialect: Dialect Marker Accuracy per grapheme occurrence
(provenance-aligned, exact unit match), sun-letter assimilation, and a moon-letter
negative control. References are hard-coded in the scorer, not read from the engine.

Article environments include the proclitic forms (و ف ب ك + ال, also after a leading
و/ف, e.g. وبالتالي) and لل; their counts are reported separately. In Egyptian and Levantine,
Thāʾ and Dhāl in learned words (e.g. إذا /iza/, حادث /ħaːdis/) are scored against /s/ and
/z/. Which words are learned, which proclitic + ال words are not articles, and which Alifs
are waṣl Alifs is decided by lists and patterns written into the scorer, independently of
the engine's lexicons; the self-test shows that a wrong lexicon entry is detected.

## Human evaluation sample

`g2p/human_eval/select_sentences.py` draws the human-evaluation sample (50 sentences per
dialect, fixed seed, 3-25 words, no Latin script) from the development split
(`g2p/data/dev_split.csv`, sanitized like the test split), excluding development sentences
whose text also occurs in the test split, and writes the engine's output on the
undiacritized transcript to `g2p/human_eval/sentences.csv` (`Item` is a unique key: corpus
IDs repeat across recording sessions). The development split played no part in designing
the rules or the word lexicons; the annotation guide was piloted on a separate test-split
sample, with AI agents as stand-in annotators, and those pilot judgments are not results.

`g2p/human_eval/workbooks/` holds the annotation material: one blind workbook per
annotator (`annotator_EGY-A.xlsx` ... `annotator_GLF-B.xlsx`, guide in English and Egyptian
Arabic) and the adjudication workbook. `merge_annotations.py` merges the six files into the
adjudication workbook; `build_workbook.py` rebuilds all of them from `sentences.csv`.

`g2p/human_eval/annotations/` holds the completed evaluation: the per-sentence judgments of
both annotators with the adjudicated result and error details (`judgments_150.csv`/`.xlsx`),
and the seven workbooks with the free-text notes removed (see its README). Result: 122 of 150
sentences judged correct (81.3%, 95% Wilson interval 74.3-86.8), Cohen's kappa 0.79.

## Version used in the AJSE paper

The results of *Rule-Based Phonemization for Arabic Dialects: A Grapheme-to-Phoneme Framework* were produced with engine
commit `c9fd7c0`. Release **v1.6.1** (https://doi.org/10.5281/zenodo.23985063) contains this
engine unchanged, together with the human-evaluation judgments and the scripts that regenerate
every number and table of the paper (`paper/`). Later commits on `main` may change the engine's
output.

## Dataset download

The corpus (audio + metadata) is hosted on Hugging Face:

```python
from datasets import load_dataset
ds = load_dataset("robsgeorge/Ara_150_Multi_Dialect_TTS", split="train")
```

Or download metadata only:
```python
from huggingface_hub import hf_hub_download
path = hf_hub_download(repo_id="robsgeorge/Ara_150_Multi_Dialect_TTS",
                       filename="master_metadata.csv", repo_type="dataset")
```

---

## Citation

If you use Ara-150 or AraForge in your research, please cite:

```bibtex
@article{basily2026ara150,
  author    = {Robeir Basily and Cherif Salama and Mahmoud Khalil},
  title     = {{Ara-150}: A Large-Scale Multi-Dialect {A}rabic Speech Corpus
               and Reproducible Processing Pipeline for Text-to-Speech Research},
  journal   = {Language Resources and Evaluation},
  year      = {2026},
  note      = {In submission. Dataset: https://doi.org/10.5281/zenodo.20452142,
               https://huggingface.co/datasets/robsgeorge/Ara_150_Multi_Dialect_TTS}
}

@article{basily2026phonemization,
  author    = {Robeir Basily and Cherif Salama and Mahmoud Khalil},
  title     = {Rule-Based Phonemization for {A}rabic Dialects: A
               Grapheme-to-Phoneme Framework},
  journal   = {Arabian Journal for Science and Engineering},
  year      = {2026},
  note      = {In submission}
}

@misc{basily2026g2p_v161,
  author    = {Robeir Basily and Cherif Salama and Mahmoud Khalil},
  title     = {{Ara-150-Pipeline}: AraForge pipeline and dialect-aware {A}rabic G2P engine},
  version   = {1.6.1},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.23985063},
  url       = {https://doi.org/10.5281/zenodo.23985063}
}

@misc{basily2026ara150data,
  author    = {Robeir Basily and Cherif Salama and Mahmoud Khalil},
  title     = {{Ara-150}: A multi-dialect {A}rabic text-to-speech corpus [Data set]},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.20452142},
  url       = {https://doi.org/10.5281/zenodo.20452142}
}
```

---

## License

| Component | License |
|-----------|---------|
| Code (this repository) | [MIT](LICENSE) |
| Corpus (audio + metadata) | [CC-BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) |

The corpus is for **non-commercial research use only.** Commercial use, voice
cloning aimed at impersonation, and identification of individual speakers are
explicitly prohibited by the corpus license.

Takedown requests: open a GitHub issue or contact the corresponding author.

---

## Ethics

- Speakers are identified in the corpus metadata only by pseudonymous codes
  (SPK_NNN, derived from ECAPA-TDNN clustering).
- The corpus is derived from publicly broadcast Arabic-language content
  (podcasts, lectures, talk shows, sermons).
- Formal ethics-committee review was not sought for the human evaluation;
  annotators participated voluntarily, gave informed consent, and their judgments
  are released under anonymous annotator codes only.

---

*Ain Shams University, Cairo, Egypt · robeir.samir@eng.asu.edu.eg*
