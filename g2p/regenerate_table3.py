"""
regenerate_table3.py
====================
Recomputes the marker-evaluation tables of the G2P paper (Tables 3 and A3) from the
released engine.

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
  Learned words -- in Egyptian and Levantine, Thāʾ and Dhāl in learned words are
       scored against /s/ and /z/ instead of Table 1's /t/ and /d/. Which words are learned,
       which words are not articles, and which Alifs are waṣl Alifs is decided by lists and
       patterns written into this scorer, not taken from the engine, so a wrong entry in the
       engine's lexicons shows up as a miss.

Reference realizations (markers, sun letters, article prefixes) are hard-coded
from the paper's tables and do not read the engine's lookup table, so a changed
rule shows up as a miss. Tokens are normalized exactly as the engine does
(Tatweel removed, boundary punctuation stripped, Latin-script runs shielded).
"""
import argparse
import csv
import sys
from collections import defaultdict
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # also under python -I

from arabic_g2p_rules import (ARTICLE, IPA_RULES, MOON_LETTERS, SUN_LETTERS,
                              arabic_words, strip_diacritics, transcribe_word_aligned)

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
LIL_REF = {"Egyptian": ("lel-", "le-"), "Levantine Arabic": ("lɪl-", "lɪ-"),
           "Khaliji Arabic": ("lɪl-", "lɪ-"), "Modern Standard Arabic (MSA)": ("lil-", "li-")}
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
MOON_CLASS = set("ءأإآبجحخعغفقكمهوي") | {"ا"} | set("\u06A4\u0686\u06AF\u067E\u06A8")  # bare Alif, loan letters
assert all(set(v) == SUN_CLASS for v in SUN_REF.values())


# ---- scope and references written into the scorer (independent copies, see docstring)
LEARNED_REF = {
    "هذا", "هذه", "ذلك", "كذلك", "كذا", "هكذا", "ماذا", "لماذا", "إذا", "اذا", "إذن", "اذن", "منذ", "ثم",
    "ذات", "بحث", "أبحاث", "ابحاث", "باحث", "باحثين", "يبحث", "حدث", "أحداث", "احداث", "حادث", "حادثة",
    "حوادث", "حديث", "حديثة", "تحدث", "يتحدث", "حدثت", "أحدث", "ثورة", "ثورات", "ثوري", "ثورية", "ثوار",
    "ثابت", "ثابتة", "ثبت", "أثبت", "اثبت", "أثبتت", "أثر", "اثر", "آثار", "اثار", "أثار", "تأثير",
    "تأثر", "يتأثر", "اتأثر", "مؤثر", "مؤثرة", "يؤثر", "أثرية", "مثلا", "مثال", "أمثلة", "مثالي",
    "مثالية", "تمثيل", "ممثل", "تمثال", "تماثيل", "ثقافة", "ثقافي", "ثقافية", "ثقة", "ذكر", "ذكرى",
    "ذكريات", "ذاكرة", "تذكر", "يذكر", "ذكاء", "ذكي", "غذاء", "غذائي", "غذائية", "تغذية", "أغذية",
    "اغذية", "أستاذ", "استاذ", "كارثة", "كوارث", "تنفيذ", "نفوذ", "إنقاذ", "انقاذ", "ينقذ", "استثمار",
    "مستثمر", "مستثمرين", "استثناء", "استثنائي", "أثناء", "اثناء", "كثافة", "جاذبية", "يجذب",
    "ثانيا", "عذاب", "حذر", "ذهن", "ذهنية", "تلميذ", "تلاميذ", "نموذج", "وراثية", "وثيقة", "وثائق",
}
LEARNED_VALUE = {"ث": "s", "ذ": "z"}
# The name of God and its proclitic forms: lexical, not scored as article environments.
SCOPE_LEXICAL = {"الله", "والله", "بالله", "لله", "فالله", "تالله", "ولله", "فلله", "الحمدلله", "والحمدلله"}
WALID_SUFFIXES = {"", "ي", "ه", "ك", "ها", "هم", "كم", "نا", "ة", "تي", "ته", "تها", "تك", "تهم", "تكم", "تنا",
                  "يه", "يها", "يهم", "يك", "اه", "ان", "اي"}
SCOPE_NOT_ARTICLE = {"والدي", "والده", "والدة", "والدك", "والدهم", "والدتي", "والدته", "والدتها", "والدتك",
                     "والديه", "بالها", "بالهم", "بالكم", "بالنا", "بالغة", "بالغين", "بالغا", "بالغت", "بالون",
                     "كاليفورنيا", "كالوري", "كالوريز", "واللا", "والتر"}
_PRE = [a + b + c for a in ("", "و", "ف") for b in ("", "ب", "ك", "ل") for c in ("", "ال")] + [a + "لل" for a in ("", "و", "ف")]
_SUF = ["ه", "ها", "هم", "هن", "ك", "كم", "نا", "ي", "ة", "ات", "ين", "ون", "ا", "ية", "يات"]
NOT_LEARNED_REF = {"هذاك", "هذيك"}
_DIAC = set("\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652\u0670")


def learned_word(bare):
    if any(bare.startswith(p) and bare[len(p):] in NOT_LEARNED_REF for p in _PRE):
        return False
    for p in _PRE:
        if bare.startswith(p) and len(bare) - len(p) >= 2:
            r = bare[len(p):]
            if r in LEARNED_REF or any(r.endswith(x) and len(r) - len(x) >= 2 and r[:-len(x)] in LEARNED_REF for x in _SUF):
                return True
    return False


def article_env(word):
    """(kind, proclitic, index of the first stem letter) for ال, proclitic + ال, لل; None if no article."""
    pos = [k for k, ch in enumerate(word) if ch not in _DIAC]
    L = [word[k] for k in pos]
    if len(L) >= 3 and L[:2] == ["ا", "ل"] and L[2] not in "ىا" or (len(L) > 3 and L[:3] == ["ا", "ل", "ا"]):
        return "article", "", pos[2]
    b = "".join(L)
    if b in SCOPE_NOT_ARTICLE or (b.startswith("والد") and b[4:] in WALID_SUFFIXES):
        return None
    for lead in ("", "و", "ف"):
        m = len(lead)
        if "".join(L[:m]) != lead:
            continue
        if L[m:m + 2] == ["ل", "ل"] and len(L) >= m + 3:
            return "lil", "", pos[m + 2]
        if len(L) >= m + 5 and L[m] in ("وفبك" if m == 0 else "بك") and L[m + 1:m + 3] == ["ا", "ل"] and L[m + 3] != "ى":
            return "proc", L[m], pos[m + 3]
    return None


def wasl(stem):
    """Hamzat al-waṣl after the article: forms VII, VIII, X verbal nouns; اسم, ابن, اثنين, امرأة."""
    s = "".join(ch for ch in stem if ch not in _DIAC)
    if any(s == n or (s.startswith(n) and s[len(n):] in ("ه", "ها", "هم", "ي", "ك", "نا", "كم"))
           for n in ("اسم", "ابن", "ابنة", "ابنت", "اثنين", "اثنان", "اتنين", "امرأة", "امراة")) or s.startswith(("اسمع", "اسمح")):
        return True
    if s.startswith(("استرال", "اسطوان")):
        return False
    return ((len(s) >= 6 and ((s[4] == "ا" and (s[1] == "ن" or s[2] in "تطد")) or (s.startswith("است") and s[5:6] == "ا")))
            or (len(s) >= 5 and s[1] == "ت" and s[3] == "ا"))


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
    learned = dialect in LEARNED_DIALECTS and learned_word(bare)

    def ref_of(letter, default):
        return LEARNED_VALUE[letter] if learned and letter in LEARNED_VALUE else default

    # (i) per-occurrence marker realization (learned Thāʾ/Dhāl scored against /s/, /z/)
    for letter, ref in MARKERS[dialect].items():
        for k, ch in enumerate(word):
            if ch != letter:
                continue
            r = ref_of(letter, ref)
            got = _from(aligned(), k)
            acc["mrc"][letter][1] += 1
            hit = bool(got) and all(u == r for u in got)
            acc["mrc"][letter][0] += hit
            if learned and letter in LEARNED_VALUE:
                acc["learned"][1] += 1; acc["learned"][0] += hit
            if not hit:
                acc["mrc_fail"][letter].append((word, got))

    # (ii) definite article: ال, proclitic + ال, لل (moon environments include bare Alif).
    # The name of God (الله and its proclitic forms) is a lexical exception, not scored.
    env = article_env(word)
    if env is None and (bare in SCOPE_NOT_ARTICLE or (bare.startswith("والد") and bare[4:] in WALID_SUFFIXES)):
        acc["nonart"][1] += 1                                  # control: listed non-article words get no prefix
        ok = not _from(aligned(), ARTICLE)
        acc["nonart"][0] += ok
        if not ok:
            acc["nonart_fail"].append((word, aligned()))
    if env and bare not in SCOPE_LEXICAL:
        kind, proc, start = env
        c = word[start]
        if kind == "article":
            moon_pre, sun_pre = ARTICLE_REF[dialect]
        elif kind == "proc":
            v = PROC_REF[dialect][proc]
            moon_pre, sun_pre = v + "l-", v + "-"
        else:
            moon_pre, sun_pre = LIL_REF[dialect]
        acc["kind"][kind] += 1
        art = _from(aligned(), ARTICLE)
        got = _from(aligned(), start)
        if c in SUN_CLASS:
            ref = ref_of(c, SUN_REF[dialect][c])
            ok = art == [sun_pre] and got == [ref, ref]
            acc["sun"][1] += 1
            acc["sun"][0] += ok
            if not ok:
                acc["sun_fail"].append((word, aligned()))
        elif c not in MOON_CLASS:                              # letter outside both classes: counted as a miss
            acc["moon"][1] += 1
            acc["moon_fail"].append((word, aligned()))
        elif c in MOON_CLASS:
            if c == "ا":                                       # waṣl Alif silent, otherwise the glottal onset
                ok = art == [moon_pre] and got == ([] if wasl(word[start:]) else ["ʔ"])
            else:
                ok = art == [moon_pre] and len(got) == 1
            acc["moon"][1] += 1
            acc["moon"][0] += ok
            if not ok:
                acc["moon_fail"].append((word, aligned()))


def new_acc():
    return {"mrc": defaultdict(lambda: [0, 0]), "mrc_fail": defaultdict(list),
            "sun": [0, 0], "sun_fail": [], "moon": [0, 0], "moon_fail": [],
            "kind": defaultdict(int), "learned": [0, 0], "nonart": [0, 0], "nonart_fail": [], "sentences": 0}


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
            w.writerow([s, "Learned words", "Thāʾ/Dhāl -> /s/, /z/ (included in DMA)", *a["learned"], pct(*a["learned"])])
            w.writerow([s, "Non-article control", "listed non-article words", *a["nonart"], pct(*a["nonart"])])


def report(accs):
    print(f"{'Dialect':<5}{'sent.':>7}{'DMA':>20}{'Sun':>20}{'Moon (ctrl)':>20}{'proc+ال':>9}{'لل':>6}{'learned':>9}")
    for d in [x for x in ORDER if x in accs]:
        a = accs[d]
        tc = sum(v[0] for v in a["mrc"].values()); tn = sum(v[1] for v in a["mrc"].values())
        f = lambda c, n: f"{c}/{n} {pct(c, n)}%"
        print(f"{SHORT[d]:<5}{a['sentences']:>7}{f(tc, tn):>20}{f(*a['sun']):>20}"
              f"{f(*a['moon']):>20}{a['kind']['proc']:>9}{a['kind']['lil']:>6}{a['learned'][1]:>9}")
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
    # learned vocabulary and waṣl: the engine's lexicons are checked against the scorer's own lists
    eng_l = IPA_RULES["dialects"]["Egyptian"]["learned"]
    original = eng_l["ث"]; eng_l["ث"] = "ʃ"
    broken = evaluate([("حادث", "Egyptian")])["Egyptian"]["mrc"]["ث"]
    eng_l["ث"] = original
    ok = broken == [0, 1]; failures += not ok
    print(f"  [{'PASS' if ok else 'FAIL'}] learned Thāʾ sabotaged (EGY /ʃ/): {broken}")
    eng.LEARNED.add("ثلاثة")
    broken = evaluate([("ثلاثة", "Egyptian")])["Egyptian"]["mrc"]["ث"]
    eng.LEARNED.discard("ثلاثة")
    ok = broken[0] < broken[1]; failures += not ok
    print(f"  [{'PASS' if ok else 'FAIL'}] colloquial word added to the engine's learned lexicon: {broken}")
    saved_w = eng._wasl_stem; eng._wasl_stem = lambda stem, after_article=True: True
    broken = evaluate([("الارض", "Egyptian")])["Egyptian"]["moon"]
    eng._wasl_stem = saved_w
    ok = broken == [0, 1]; failures += not ok
    print(f"  [{'PASS' if ok else 'FAIL'}] every Alif after the article made silent: {broken}")
    eng.NOT_ARTICLE.discard("بالها")
    broken = evaluate([("بالها", "Egyptian")])["Egyptian"]["nonart"]
    eng.NOT_ARTICLE.add("بالها")
    ok = broken == [0, 1]; failures += not ok
    print(f"  [{'PASS' if ok else 'FAIL'}] non-article word removed from the engine's lexicon: {broken}")
    sun_set["letters"] = saved_spec + "ق"
    broken = evaluate([("القمر", "Egyptian")])["Egyptian"]["moon"]
    sun_set["letters"] = saved_spec
    ok = broken == [0, 1]; failures += not ok
    print(f"  [{'PASS' if ok else 'FAIL'}] moon letter Qāf geminated like a sun letter: {broken}")
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
