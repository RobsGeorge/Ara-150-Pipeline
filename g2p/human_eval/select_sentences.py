"""Select the human-evaluation sample and produce the engine output the annotators judge.

Sample: 50 sentences per dialect (Egyptian, Levantine, Gulf) drawn uniformly at random,
with a fixed seed, from the development split, among sentences with 3-25 words and no
Latin-script content. The development split played no part in designing the rules or the
lexicons (the annotation guide was piloted on a separate sample from the test split). Each sentence is transcribed by the engine with the sentence's
dialect rule set, on the undiacritized transcript (diacritization stage disabled), so that
annotators judge the engine itself: consonants, the definite article, and written long
vowels.

Item is a unique key (corpus IDs repeat across recording sessions).

Usage: python human_eval/select_sentences.py data/dev_split.csv human_eval/sentences.csv data/test_split.csv
(the optional third argument excludes development sentences whose text also occurs in the test split)
"""
import csv
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arabic_g2p_rules import arabic_words, strip_diacritics, transcribe_protected  # noqa: E402

SEED, PER_DIALECT, MIN_WORDS, MAX_WORDS = 2026, 50, 3, 25
DIALECTS = {"Egyptian": ("EGY", "Egyptian"), "Levantine": ("LEV", "Levantine Arabic"),
            "Khaliji": ("GLF", "Khaliji Arabic")}
LATIN = re.compile(r"[A-Za-z]")


def eligible(text):
    return text and not LATIN.search(text) and MIN_WORDS <= len(list(arabic_words(text))) <= MAX_WORDS


def key(text):
    """Normalized text (Arabic words without diacritics) used to detect duplicates."""
    return " ".join(strip_diacritics(w) for w in arabic_words(text))


def main(test_csv, out_csv, exclude_csv=None):
    rows = list(csv.DictReader(open(test_csv, encoding="utf-8")))
    if exclude_csv:                      # sentences whose text also occurs in the test split are excluded
        seen = {key(r["Transcript"] or "") for r in csv.DictReader(open(exclude_csv, encoding="utf-8"))}
        n0 = len(rows); rows = [r for r in rows if key(r["Transcript"] or "") not in seen]
        print(f"{n0 - len(rows)} development rows excluded (text also in {exclude_csv})")
    rng = random.Random(SEED)
    out = []
    for raw, (tag, rule_set) in DIALECTS.items():
        pool = sorted((r for r in rows if r["Main Dialect"] == raw and eligible((r["Transcript"] or "").strip())),
                      key=lambda r: int(r["ID"]) if r["ID"].isdigit() else r["ID"])
        for k, r in enumerate(rng.sample(pool, PER_DIALECT), 1):
            text = r["Transcript"].strip()
            out.append({"Item": f"{tag}-{k:03d}", "ID": r["ID"], "Dialect": tag, "Transcript": text,
                        "IPA": transcribe_protected(text, rule_set)})
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)
    print(f"{len(out)} sentences written to {out_csv}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
