# Ara-150: Multi-Dialect Arabic TTS Corpus — AraForge Pipeline

<div align="center">

[![License: MIT](https://img.shields.io/badge/Code-MIT-green.svg)](LICENSE)
[![Dataset License](https://img.shields.io/badge/Corpus-CC--BY--NC--SA%204.0-blue.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![HuggingFace](https://img.shields.io/badge/🤗%20Dataset-Ara--150-orange)](https://huggingface.co/datasets/robsgeorge/Ara_150_Multi_Dialect_TTS)
[![Tests](https://img.shields.io/badge/G2P%20tests-34%2F34%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)]()

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
- **Phonemes:** rule-based G2P engine · 100% Dialectal Marker Accuracy on test split
- **Speakers:** pseudonymous (SPK_NNN) · age, gender, dialect, emotion per clip
- **License:** corpus CC-BY-NC-SA 4.0 · code MIT

---

## Repository structure

```
Ara-150-Pipeline/
│
├── notebooks/
│   ├── 01_ingestion_and_processing.ipynb     # Whisper + VAD + segmentation
│   ├── 02_metadata_and_phonemization.ipynb   # G2P + ECAPA-TDNN speaker clustering
│   └── 03_dataset_consolidation.ipynb        # Final merge + quality filtering
│
├── g2p/
│   ├── arabic_g2p_rules.py      # Core G2P engine (4 dialects, 34-test suite)
│   ├── test_arabic_g2p.py       # Validation: run `python test_arabic_g2p.py`
│   ├── diacritize_then_g2p.py   # Full-IPA pipeline (CAMeL Tools / Mishkal)
│   ├── regenerate_table3.py     # Recompute DMA from any test CSV
│   ├── fleiss_kappa.py          # Inter-annotator agreement computation
│   └── IPA_Phonemes.xlsx        # Machine-readable IPA mapping lexicon (10 sheets)
│
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
# → /e-lljl/ /welnahaːɾ/

print(transcribe_protected("قال المدرس", "Khaliji Arabic"))
# → /gaːl/ /ɪl-mdrsk/

# With diacritization (requires: pip install camel-tools)
from g2p.diacritize_then_g2p import main
# or: python g2p/diacritize_then_g2p.py --text "مَدْرَسَة" --dialect MSA --backend camel
# → /madrasa/
```

Supported dialects: `"Egyptian"` · `"Khaliji Arabic"` · `"Levantine Arabic"` · `"Modern Standard Arabic (MSA)"`

---

## Run the validation tests

```bash
pip install -r requirements.txt
python g2p/test_arabic_g2p.py
# ==== 34/34 tests passed ====
```

---

## Run the full AraForge pipeline

Open the notebooks in Google Colab (recommended) or JupyterLab in order:

| Step | Notebook | Input | Output |
|------|----------|-------|--------|
| 1 | `01_ingestion_and_processing.ipynb` | Raw audio files | Segmented WAV clips |
| 2 | `02_metadata_and_phonemization.ipynb` | Clips + transcripts | `metadata_with_phonemes.csv` |
| 3 | `03_dataset_consolidation.ipynb` | Per-speaker CSVs | `master_metadata.csv` |

Set `GOOGLE_DRIVE_PATH` at the top of each notebook to your Drive folder.

---

## Regenerate Table 3 (DMA) from your test split

```bash
python g2p/regenerate_table3.py \
    --test-csv path/to/test_split.csv \
    --output table3_results.csv
```

---

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
                       filename="metadata.csv", repo_type="dataset")
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
  doi       = {10.5281/zenodo.20452226},
  url       = {https://doi.org/10.5281/zenodo.20452226}
  note      = {In submission. Dataset: https://huggingface.co/datasets/robsgeorge/Ara_150_Multi_Dialect_TTS}
}

@article{basily2026phonemization,
  author    = {Robeir Basily and Cherif Salama and Mahmoud Khalil},
  title     = {A Rule-Based Framework for Multi-Dialect {A}rabic
               Grapheme-to-Phoneme Conversion},
  journal   = {Arabian Journal for Science and Engineering},
  year      = {2026},
  doi       = {10.5281/zenodo.20452142},
  url       = {https://doi.org/10.5281/zenodo.20452142}
  note      = {In submission}
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

- All speaker identities have been anonymized (SPK_NNN pseudonyms derived from
  ECAPA-TDNN clustering). Real-world identities are not recoverable from the
  released artifacts.
- The corpus is derived from publicly broadcast Arabic-language content
  (podcasts, lectures, talk shows, sermons).
- No IRB review was required; annotators participated voluntarily with no
  personal data collected.

---

*Ain Shams University, Cairo, Egypt · robeir.samir@eng.asu.edu.eg*
