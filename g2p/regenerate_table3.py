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
       Article environments include the proclitic forms (و/ف/ب/ك + ال, also after a
       leading و/ف: وبال) and لل; their counts are reported separately.
  Learned words -- in Egyptian and Levantine, Thāʾ and Dhāl in words of the engine's
       learned-vocabulary lexicon are realized /s/, /z/ by design; these occurrences
       (and article environments whose first stem letter is one of them) are counted
       but not scored, since the reference realization differs from Table 1.

Reference realizations (markers, sun letters, article prefixes) are hard-coded
from the paper's tables and do not read the engine's lookup table, so a changed
rule shows up as a miss. Tokens are normalized exactly as the engine does
(Tatweel removed, boundary punctuation stripped, Latin-script runs shielded).
"""
import argparse
import csv
import sys
from collections import defaultdict

from arabic_g2p_rules import (ALLAH, ARTICLE, IPA_RULES, MOON_LETTERS, SUN_LETTERS, article_parse,
                              arabic_words, is_learned, strip_diacritics, transcribe_word_aligned)

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
# Article prefixes after a proclitic (vowel + l- / vowel + -) and for لل: (moon, sun).
PROC_REF = {
    "Egyptian":                     {"و": "we", "ف": "fe", "ب": "be", "ك": "ke"},
    "Levantine Arabic":             {"و": "wɪ", "ف": "fɪ", "ب": "bɪ", "ك": "kɪ"},
    "Khaliji Arabic":               {"و": "wɪ", "ف": "fɪ", "ب": "bɪ", "ك": "kɪ"},
    "Modern Standard Arabic (MSA)": {"و": "wa", "ف": "fa", "ب": "bi", "ك": "ka"},
}
LIL_REF = {"Egyptian": ("lel-", "le-"), "Levantine Arabic": ("lil-", "li-"),
           "Khaliji Arabic": ("lil-", "li-"), "Modern Standard Arabic (MSA)": ("lil-", "li-")}
LEARNED_DIALECTS = {"Egyptian", "Levantine Arabic"}
ORDER = ["Egyptian", "Khaliji Arabic", "Levantine Arabic", "Modern Standard Arabic (MSA)"]


# Reference realization of each sun letter after assimilation (Table A1), written out
# here rather than read from the engine. Egyptian /ɾ/ geminates as the trill /rr/.
_SUN_COMMON = {"ت": "t", "د": "d", "ر": "r", "ز": "z", "س": "s", "ش": "ʃ", "ص": "sˤ",
               "ض": "dˤ", "ط": "tˤ", "ل": "l", "ن": "n"}
SUN_REF = {
    "Egyptian":                     {**_SUN_COMMON, "ث": "t", "ذ": "d", "ظ": "zˤ"},
    "Levantine Arabic":             {**_SUN_COMMON, "ث": "t", "ذ": "d", "ظ": "zˤ"},
    "Khaliji Arabic":               {**_SUN_COMMON, "ث": "θ", "ذ": "ð", "ظ": "ðˤ", "ض": "ðˤ"},
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

    bare = strip_diacritics(word)
    learned = dialect in LEARNED_DIALECTS and is_learned(bare)

    # (i) per-occurrence marker realization
    for letter, ref in MARKERS[dialect].items():
        for k, ch in enumerate(word):
            if ch != letter:
                continue
            if learned and letter in "ثذ":
                acc["learned"] += 1                            # learned word: /s/, /z/ by design
                continue
            got = _from(aligned(), k)
            acc["mrc"][letter][1] += 1
            if got and all(u == ref for u in got):
                acc["mrc"][letter][0] += 1
            else:
                acc["mrc_fail"][letter].append((word, got))

    # (ii) definite article: ال, proclitic + ال, لل (moon environments include bare Alif).
    # The name of God (الله and its proclitic forms) is a lexical exception, not scored.
    kind, procs, start = article_parse(word)
    if kind and bare not in ALLAH:
        c = word[start]
        if learned and c in "ثذ":
            acc["learned_art"] += 1
            return
        if kind == "article":
            moon_pre, sun_pre = ARTICLE_REF[dialect]
        elif kind == "proc":
            v = PROC_REF[dialect][procs[-1]]
            moon_pre, sun_pre = v + "l-", v + "-"
        else:
            moon_pre, sun_pre = LIL_REF[dialect]
        acc["kind"][kind] += 1
        art = _from(aligned(), ARTICLE)
        if c in SUN_CLASS:
            ref = SUN_REF[dialect][c]
            ok = art == [sun_pre] and _from(aligned(), start) == [ref, ref]
            acc["sun"][1] += 1
            acc["sun"][0] += ok
            if not ok:
                acc["sun_fail"].append((word, aligned()))
        elif c in MOON_CLASS:
            got = _from(aligned(), start)
            # bare Alif may be a silent waṣl Alif; any other moon letter gives exactly one unit
            ok = art == [moon_pre] and (len(got) == 1 or (c == "ا" and len(got) <= 1))
            acc["moon"][1] += 1
            acc["moon"][0] += ok
            if not ok:
                acc["moon_fail"].append((word, aligned()))


def new_acc():
    return {"mrc": defaultdict(lambda: [0, 0]), "mrc_fail": defaultdict(list),
            "sun": [0, 0], "sun_fail": [], "moon": [0, 0], "moon_fail": [],
            "kind": defaultdict(int), "learned": 0, "learned_art": 0, "sentences": 0}


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
            for k, label in (("article", "ال"), ("proc", "proclitic + ال"), ("lil", "لل")):
                w.writerow([s, "Article environments", label, "", a["kind"][k], ""])
            w.writerow([s, "Learned words (not scored)", "Thāʾ/Dhāl occurrences", "", a["learned"], ""])
            w.writerow([s, "Learned words (not scored)", "article environments", "", a["learned_art"], ""])


def report(accs):
    print(f"{'Dialect':<5}{'sent.':>7}{'DMA':>20}{'Sun':>20}{'Moon (ctrl)':>20}{'proc+ال':>9}{'لل':>6}{'learned':>9}")
    for d in [x for x in ORDER if x in accs]:
        a = accs[d]
        tc = sum(v[0] for v in a["mrc"].values()); tn = sum(v[1] for v in a["mrc"].values())
        f = lambda c, n: f"{c}/{n} {pct(c, n)}%"
        print(f"{SHORT[d]:<5}{a['sentences']:>7}{f(tc, tn):>20}{f(*a['sun']):>20}"
              f"{f(*a['moon']):>20}{a['kind']['proc']:>9}{a['kind']['lil']:>6}{a['learned']:>9}")
        for label, key in (("DMA", "mrc_fail"), ("sun", "sun_fail"), ("moon", "moon_fail")):
            fails = a[key] if key != "mrc_fail" else [x for v in a[key].values() for x in v]
            for word, got in fails[:3]:
                print(f"      {label} miss: {word} -> {got}")


def self_test():
    """Sabotage each marker rule in turn; the scorer must report a miss."""
    probe = {"ج": "جميل", "ث": "ثلاثة", "ذ": "ذهب", "ظ": "ظلام", "ق": "قال"}
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
    trap = evaluate([("الظلام ذهب", "Khaliji Arabic")])["Khaliji Arabic"]["mrc"]["ذ"]
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
    # proclitic article: a wrong proclitic vowel and a missing assimilation after a proclitic
    pv = IPA_RULES["dialects"]["Egyptian"]["proclitic_vowel"]
    original = pv["و"]; pv["و"] = "wa"
    broken = evaluate([("والشمس", "Egyptian")])["Egyptian"]["sun"]
    pv["و"] = original
    ok = broken == [0, 1]; failures += not ok
    print(f"  [{'PASS' if ok else 'FAIL'}] proclitic vowel sabotaged (EGY wa-): {broken}")
    saved_spec = sun_set["letters"]; sun_set["letters"] = saved_spec.replace("ش", "")
    broken = evaluate([("بالشمس", "Egyptian")])["Egyptian"]["sun"]
    sun_set["letters"] = saved_spec
    ok = broken == [0, 1]; failures += not ok
    print(f"  [{'PASS' if ok else 'FAIL'}] no assimilation after a proclitic: {broken}")
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
