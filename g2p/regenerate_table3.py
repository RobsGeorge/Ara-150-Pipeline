"""
regenerate_table3.py
====================
Recomputes the marker-evaluation table of the G2P paper (Table 2 in the
manuscript; the script keeps its historical name) from the released engine.

Usage:
    python regenerate_table3.py --test-csv test_split.csv --output table2.csv
    python regenerate_table3.py --self-test        # proves the scorer can fail

Input CSV columns: Transcript, Main Dialect (Egyptian | Levantine | Khaliji | MSA).

Three measures are reported, matching Section 6.2:

  (i)  Dialect Marker Accuracy (DMA) -- per grapheme OCCURRENCE.
       Each occurrence of a marker grapheme is checked against the phoneme
       unit(s) the engine produced *from that occurrence* (provenance-aligned),
       using exact unit equality. A substring test on the joined sentence is
       NOT used: it cannot fail for a context-free lookup and it lets /ð/
       match inside /ðˤ/.
  (ii) Sun-letter assimilation -- word-initial ال + sun letter must yield the
       dialect's sun article prefix followed by exactly two copies of the
       consonant's realization.
       Moon-letter non-assimilation (negative control) -- word-initial ال +
       moon letter (or bare Alif) must yield the dialect's moon prefix and exactly one
       realization of that letter.
  Diagnostics -- sun-letter environments the engine does not treat as
       articles (proclitic و/ف/ب/ك + ال, and لل + sun). Reported separately;
       they are coverage gaps, not part of (ii).

Reference realizations (markers, sun letters, article prefixes) are hard-coded
from the paper's tables and do not read the engine's lookup table, so a changed
rule shows up as a miss. Tokens are normalized exactly as the engine does
(Tatweel removed, boundary punctuation stripped, Latin-script runs shielded).
"""
import argparse
import csv
import sys
from collections import defaultdict

from arabic_g2p_rules import (ARTICLE, IPA_RULES, MOON_LETTERS, SUN_LETTERS,
                              arabic_words, is_article, transcribe_word_aligned)

DIALECT_NORM = {
    "Egyptian": "Egyptian", "EGY": "Egyptian",
    "Levantine": "Levantine Arabic", "LEV": "Levantine Arabic",
    "Khaliji": "Khaliji Arabic", "Gulf": "Khaliji Arabic",
    "GLF": "Khaliji Arabic", "KHA": "Khaliji Arabic",
    "MSA": "Modern Standard Arabic (MSA)",
}
SHORT = {"Egyptian": "EGY", "Levantine Arabic": "LEV",
         "Khaliji Arabic": "GLF", "Modern Standard Arabic (MSA)": "MSA"}

# φ*(g, d): reference realizations from Table 1 (ɡ is U+0261 throughout).
MARKERS = {
    "Egyptian":                     {"ج": "ɡ",  "ث": "t", "ذ": "d", "ظ": "zˤ", "ق": "ʔ"},
    "Levantine Arabic":             {"ج": "ʒ",  "ث": "t", "ذ": "d", "ظ": "zˤ", "ق": "ʔ"},
    "Khaliji Arabic":               {"ج": "dʒ", "ث": "θ", "ذ": "ð", "ظ": "ðˤ", "ق": "ɡ"},
    "Modern Standard Arabic (MSA)": {"ج": "dʒ", "ث": "θ", "ذ": "ð", "ظ": "ðˤ", "ق": "q"},
}
# Table A2 article prefixes: (moon, sun).
ARTICLE_REF = {
    "Egyptian": ("el-", "e-"),
    "Levantine Arabic": ("ɪl-", "ɪ-"),
    "Khaliji Arabic": ("ɪl-", "ɪ-"),
    "Modern Standard Arabic (MSA)": ("al-", "a-"),
}
PROCLITICS = set("وفبك")
ORDER = ["Egyptian", "Khaliji Arabic", "Levantine Arabic", "Modern Standard Arabic (MSA)"]


# Reference realization of each sun letter after assimilation (Table A1), written out
# here rather than read from the engine. Egyptian /ɾ/ geminates as the trill /rr/.
_SUN_COMMON = {"ت": "t", "د": "d", "ر": "r", "ز": "z", "س": "s", "ش": "ʃ", "ص": "sˤ",
               "ض": "dˤ", "ط": "tˤ", "ل": "l", "ن": "n"}
SUN_REF = {
    "Egyptian":                     {**_SUN_COMMON, "ث": "t", "ذ": "d", "ظ": "zˤ"},
    "Levantine Arabic":             {**_SUN_COMMON, "ث": "t", "ذ": "d", "ظ": "zˤ"},
    "Khaliji Arabic":               {**_SUN_COMMON, "ث": "θ", "ذ": "ð", "ظ": "ðˤ"},
    "Modern Standard Arabic (MSA)": {**_SUN_COMMON, "ث": "θ", "ذ": "ð", "ظ": "ðˤ"},
}
# Letter classes, also written out independently of the engine.
SUN_CLASS = set("تثدذرزسشصضطظلن")
MOON_CLASS = set("ءأإآبجحخعغفقكمهوي") | {"ا"}          # bare Alif behaves as a moon environment
assert all(set(v) == SUN_CLASS for v in SUN_REF.values())


def _from(units, idx):
    return [u for u, s in units if s == idx]


def score_word(word, dialect, acc):
    units = None

    def aligned():
        nonlocal units
        if units is None:
            units = transcribe_word_aligned(word, dialect)
        return units

    # (i) per-occurrence marker realization
    for letter, ref in MARKERS[dialect].items():
        for k, ch in enumerate(word):
            if ch != letter:
                continue
            got = _from(aligned(), k)
            acc["mrc"][letter][1] += 1
            if got and all(u == ref for u in got):
                acc["mrc"][letter][0] += 1
            else:
                acc["mrc_fail"][letter].append((word, got))

    # (ii) definite article (word-initial ال; moon environments include bare Alif)
    if is_article(word):
        moon_pre, sun_pre = ARTICLE_REF[dialect]
        art = _from(aligned(), ARTICLE)
        c = word[2]
        if c in SUN_CLASS:
            ref = SUN_REF[dialect][c]
            ok = art == [sun_pre] and _from(aligned(), 2) == [ref, ref]
            acc["sun"][1] += 1
            acc["sun"][0] += ok
            if not ok:
                acc["sun_fail"].append((word, aligned()))
        elif c in MOON_CLASS:
            ok = art == [moon_pre] and len(_from(aligned(), 2)) == 1
            acc["moon"][1] += 1
            acc["moon"][0] += ok
            if not ok:
                acc["moon_fail"].append((word, aligned()))

    # diagnostics: sun environments outside the engine's article rule
    if len(word) >= 4 and word[0] in PROCLITICS and word[1:3] == "ال" and word[3] in SUN_CLASS:
        acc["diag_proclitic"] += 1
    if len(word) >= 3 and word.startswith("لل") and word[2] in SUN_CLASS:
        acc["diag_lil"] += 1


def new_acc():
    return {"mrc": defaultdict(lambda: [0, 0]), "mrc_fail": defaultdict(list),
            "sun": [0, 0], "sun_fail": [], "moon": [0, 0], "moon_fail": [],
            "diag_proclitic": 0, "diag_lil": 0, "sentences": 0}


def evaluate(rows):
    accs = defaultdict(new_acc)
    for text, dialect in rows:
        acc = accs[dialect]
        acc["sentences"] += 1
        for w in arabic_words(text):
            score_word(w, dialect, acc)
    return accs


def pct(c, n):
    return f"{100 * c / n:.2f}" if n else "n/a"


def write_csv(accs, path):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Dialect", "Measure", "Item", "Correct", "Applicable", "Accuracy (%)"])
        for d in [x for x in ORDER if x in accs]:
            a, s = accs[d], SHORT[d]
            for letter, ref in MARKERS[d].items():
                c, n = a["mrc"][letter]
                w.writerow([s, "DMA (per occurrence)", f"{letter} -> /{ref}/", c, n, pct(c, n)])
            tc = sum(v[0] for v in a["mrc"].values()); tn = sum(v[1] for v in a["mrc"].values())
            w.writerow([s, "DMA (per occurrence)", "all markers", tc, tn, pct(tc, tn)])
            w.writerow([s, "Sun-letter assimilation", "ال + sun", *a["sun"], pct(*a["sun"])])
            w.writerow([s, "Moon-letter control", "ال + moon", *a["moon"], pct(*a["moon"])])
            w.writerow([s, "Diagnostic (not scored)", "proclitic + ال + sun", "", a["diag_proclitic"], ""])
            w.writerow([s, "Diagnostic (not scored)", "لل + sun", "", a["diag_lil"], ""])


def report(accs):
    print(f"{'Dialect':<5}{'sent.':>7}{'DMA':>20}{'Sun':>20}{'Moon (ctrl)':>20}{'w+ال+sun':>10}{'لل+sun':>8}")
    for d in [x for x in ORDER if x in accs]:
        a = accs[d]
        tc = sum(v[0] for v in a["mrc"].values()); tn = sum(v[1] for v in a["mrc"].values())
        f = lambda c, n: f"{c}/{n} {pct(c, n)}%"
        print(f"{SHORT[d]:<5}{a['sentences']:>7}{f(tc, tn):>20}{f(*a['sun']):>20}"
              f"{f(*a['moon']):>20}{a['diag_proclitic']:>10}{a['diag_lil']:>8}")
        for label, key in (("DMA", "mrc_fail"), ("sun", "sun_fail"), ("moon", "moon_fail")):
            fails = a[key] if key != "mrc_fail" else [x for v in a[key].values() for x in v]
            for word, got in fails[:3]:
                print(f"      {label} miss: {word} -> {got}")


def self_test():
    """Sabotage each marker rule in turn; the scorer must report a miss."""
    probe = {"ج": "جميل", "ث": "ثلاثة", "ذ": "ذلك", "ظ": "ظلام", "ق": "قال"}
    failures = 0
    for d in ORDER:
        letters = IPA_RULES["dialects"][d]["letters"]
        for g, word in probe.items():
            original = letters[g]
            clean = evaluate([(word, d)])[d]["mrc"][g]
            letters[g] = {"phoneme": "/z/" if MARKERS[d][g] != "z" else "/s/"}
            broken = evaluate([(word, d)])[d]["mrc"][g]
            letters[g] = original
            ok = clean[0] == clean[1] > 0 and broken[0] == 0
            failures += not ok
            print(f"  [{'PASS' if ok else 'FAIL'}] {SHORT[d]} {g}: intact {clean}  sabotaged {broken}")
    # substring trap: /ð/ must not be credited by an adjacent /ðˤ/
    kha = IPA_RULES["dialects"]["Khaliji Arabic"]["letters"]
    original = kha["ذ"]; kha["ذ"] = {"phoneme": "/z/"}
    trap = evaluate([("الظلام ذلك", "Khaliji Arabic")])["Khaliji Arabic"]["mrc"]["ذ"]
    kha["ذ"] = original
    ok = trap == [0, 1]
    failures += not ok
    print(f"  [{'PASS' if ok else 'FAIL'}] substring trap ð-inside-ðˤ: sabotaged {trap}")
    # article rules: a wrong sun prefix and a missing gemination must both be detected
    egy = IPA_RULES["dialects"]["Egyptian"]["phonological_rules"]["al_prefix_sun"]
    original = egy["ipa"]; egy["ipa"] = "/el-/"
    broken = evaluate([("الشمس", "Egyptian")])["Egyptian"]["sun"]
    egy["ipa"] = original
    ok = broken == [0, 1]; failures += not ok
    print(f"  [{'PASS' if ok else 'FAIL'}] sun prefix sabotaged (EGY /el-/): {broken}")
    import arabic_g2p_rules as eng
    saved = eng.SUN_LETTERS.copy(); eng.SUN_LETTERS.discard("ش")
    sun_set = IPA_RULES["dialects"]["Egyptian"]["phonological_rules"]["al_prefix_sun"]
    saved_spec = sun_set["letters"]; sun_set["letters"] = saved_spec.replace("ش", "")
    broken = evaluate([("الشمس", "Egyptian")])["Egyptian"]["sun"]
    sun_set["letters"] = saved_spec; eng.SUN_LETTERS |= saved
    ok = broken == [0, 1]; failures += not ok
    print(f"  [{'PASS' if ok else 'FAIL'}] Shīn removed from the sun class: {broken}")
    print(f"\n==== self-test {'PASSED' if not failures else f'FAILED ({failures})'} ====")
    return failures == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-csv")
    ap.add_argument("--output", default="table2_regenerated.csv")
    ap.add_argument("--text-col", default="Transcript")
    ap.add_argument("--dialect-col", default="Main Dialect")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(0 if self_test() else 1)
    if not args.test_csv:
        ap.error("--test-csv is required unless --self-test is given")

    rows, skipped = [], 0
    with open(args.test_csv, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            text = (r.get(args.text_col) or "").strip()
            d = DIALECT_NORM.get((r.get(args.dialect_col) or "").strip())
            if text and d:
                rows.append((text, d))
            else:
                skipped += 1
    accs = evaluate(rows)
    write_csv(accs, args.output)
    print(f"{len(rows)} sentences scored, {skipped} skipped (empty transcript or unknown dialect)\n")
    report(accs)
    print(f"\nWritten: {args.output}")


if __name__ == "__main__":
    main()
