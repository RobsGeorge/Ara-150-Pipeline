"""Select the human-evaluation sample and produce the engine output the annotators judge.

Sample: 50 sentences per dialect (Egyptian, Levantine, Gulf) drawn uniformly at random,
with a fixed seed, from the held-out test split, among sentences with 3-25 words and no
Latin-script content. Each sentence is diacritized with the CAMeL Tools MLE disambiguator
and transcribed by the engine with the sentence's dialect rule set.

Requires: pip install camel-tools && camel_data -i disambig-mle-calima-msa-r13
Usage:    python human_eval/select_sentences.py data/test_split.csv human_eval/sentences.csv
"""
import csv
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arabic_g2p_rules import arabic_words, transcribe_protected  # noqa: E402

SEED, PER_DIALECT, MIN_WORDS, MAX_WORDS = 2026, 50, 3, 25
DIALECTS = {"Egyptian": ("EGY", "Egyptian"), "Levantine": ("LEV", "Levantine Arabic"),
            "Khaliji": ("GLF", "Khaliji Arabic")}
LATIN = re.compile(r"[A-Za-z]")


def eligible(text):
    return text and not LATIN.search(text) and MIN_WORDS <= len(list(arabic_words(text))) <= MAX_WORDS


def main(test_csv, out_csv):
    from camel_tools.disambig.mle import MLEDisambiguator
    mle = MLEDisambiguator.pretrained()

    def diacritize(text):
        return " ".join((d.analyses[0].analysis.get("diac") if d.analyses else None) or d.word
                        for d in mle.disambiguate(text.split()))

    rows = list(csv.DictReader(open(test_csv, encoding="utf-8")))
    rng = random.Random(SEED)
    out = []
    for raw, (tag, rule_set) in DIALECTS.items():
        pool = sorted((r for r in rows if r["Main Dialect"] == raw and eligible((r["Transcript"] or "").strip())),
                      key=lambda r: int(r["ID"]) if r["ID"].isdigit() else r["ID"])
        for r in rng.sample(pool, PER_DIALECT):
            text = r["Transcript"].strip()
            diac = diacritize(text)
            out.append({"ID": r["ID"], "Dialect": tag, "Transcript": text, "Diacritized": diac,
                        "IPA": transcribe_protected(diac, rule_set)})
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)
    print(f"{len(out)} sentences written to {out_csv}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
