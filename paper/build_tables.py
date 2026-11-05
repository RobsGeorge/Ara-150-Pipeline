"""Generate every data-bearing table row and every number quoted in the text of the
G2P paper directly from the engine, the evaluation CSV and the test split, so that
nothing is typed by hand.

Usage: python build_tables.py <path-to-Ara-150-Pipeline/g2p> [engine commit]
The engine commit named in the paper defaults to the checked-out commit; if one is given, the
engine (arabic_g2p_rules.py) and the data splits must be identical to it.
Writes generated/*.tex (table rows) and generated/numbers.tex (\\newcommand macros).
"""
import csv
import math
import subprocess
import sys
from pathlib import Path

G2P = Path(sys.argv[1]).resolve()
ENGINE_COMMIT = sys.argv[2] if len(sys.argv) > 2 else "HEAD"
# SHA-256 of the engine and data splits used in the paper (engine commit c9fd7c0); checked also
# where no git history is available (e.g. a Zenodo archive), and against the working tree.
import hashlib  # noqa: E402
PAPER_SHA256 = {"arabic_g2p_rules.py": "02ca9761b703c4cad2420251ab4b088cdf2981a653f8be53a303ddf7ae7cac4e", "data/test_split.csv": "50c97a0cf5d235cd9ffa42c907b15107036fffdaf6afe0be393d77a5372b1d16", "data/dev_split.csv": "5de50370085c578b102ad995601c7c1fbef0f541476850ab3a8b36e0b4a91b34"}
for rel, digest in PAPER_SHA256.items():
    if hashlib.sha256((G2P / rel).read_bytes()).hexdigest() != digest:
        sys.exit(f"{rel} differs from the version used in the paper")
if (G2P.parent / ".git").exists() and subprocess.run(
        ["git", "diff", "--quiet", ENGINE_COMMIT, "--", "arabic_g2p_rules.py", "data"], cwd=G2P).returncode:
    sys.exit(f"engine or data differ from {ENGINE_COMMIT}")
sys.path.insert(0, str(G2P))
from arabic_g2p_rules import (IPA_RULES, arabic_words, is_article,  # noqa: E402
                              transcribe_protected as T, LEARNED, TANWIN_ADV, NOT_ARTICLE, H_ROOT)
from make_table3_rows import ROWS  # noqa: E402

OUT = Path(__file__).parent / "generated"
OUT.mkdir(exist_ok=True)
D = {"EGY": "Egyptian", "LEV": "Levantine Arabic", "GLF": "Khaliji Arabic",
     "MSA": "Modern Standard Arabic (MSA)"}
ORDER = ["EGY", "LEV", "GLF", "MSA"]
NAME = {"EGY": "Egyptian", "LEV": "Levantine", "GLF": "Gulf", "MSA": "MSA"}
CSV_DIALECT = {"Egyptian": "EGY", "Levantine": "LEV", "Khaliji": "GLF", "MSA": "MSA"}
fmt = lambda n: f"{int(n):,}"
pct1 = lambda x: f"{float(x):.1f}"            # one decimal, as in the rest of the paper
macros = {}

# ---------------------------------------------------------------- evaluation CSV
rows = list(csv.DictReader(open(G2P / "results" / "table2_regenerated.csv", encoding="utf-8")))
def get(d, measure, item=None):
    return next(r for r in rows if r["Dialect"] == d and r["Measure"].startswith(measure)
                and (item is None or r["Item"] == item))

# ---------------------------------------------------------------- test split
split = list(csv.DictReader(open(G2P / "data" / "test_split.csv", encoding="utf-8")))
sents = {d: 0 for d in ORDER}
nonempty = {d: 0 for d in ORDER}
art = {"article": 0, "proclitic": 0, "lil": 0}
RELPRON = {"الذي", "التي", "الذين", "اللذان", "اللتان", "اللذين", "اللتين", "اللاتي", "اللائي", "اللواتي"}
relpron = 0
base_tok = {d: [0, 0] for d in ORDER}
base_sent = {d: [0, 0] for d in ORDER}
for r in split:
    d = CSV_DIALECT[r["Main Dialect"]]
    sents[d] += 1
    text = (r["Transcript"] or "").strip()
    if not text:
        continue
    nonempty[d] += 1
    for w in arabic_words(text):
        relpron += w in RELPRON
        if is_article(w):
            art["article"] += 1
        elif len(w) >= 4 and w[0] in "وفبك" and is_article(w[1:]):
            art["proclitic"] += 1
        elif len(w) >= 3 and w.startswith("لل"):
            art["lil"] += 1
    if d != "MSA":                       # MSA rule set applied to dialectal text
        a, b = [x for x in T(text, D[d]).split() if x.startswith("/")], [x for x in T(text, D["MSA"]).split() if x.startswith("/")]
        k = sum(x != y for x, y in zip(a, b))
        base_tok[d][0] += k; base_tok[d][1] += len(a)
        base_sent[d][0] += k > 0; base_sent[d][1] += 1

# ---------------------------------------------------------------- Table 3 (summary)
tot = {"mk": [0, 0], "sun": [0, 0], "moon": [0, 0], "oos": 0, "proc": 0, "lil": 0, "lrn": 0, "lrn_art": 0}
with open(OUT / "table2_rows.tex", "w", encoding="utf-8") as f:
    for d in ORDER:
        mk, sun, moon = get(d, "DMA", "all markers"), get(d, "Sun-letter"), get(d, "Moon-letter")
        proc = int(get(d, "Article environments", "proclitic + ال")["Applicable"])
        lil = int(get(d, "Article environments", "لل")["Applicable"])
        tot["proc"] += proc; tot["lil"] += lil
        tot["lrn"] += int(get(d, "Learned words")["Applicable"])
        oos = proc + lil
        for k, r in (("mk", mk), ("sun", sun), ("moon", moon)):
            tot[k][0] += int(r["Correct"]); tot[k][1] += int(r["Applicable"])
        tot["oos"] += oos
        f.write(f"{NAME[d]} & {fmt(nonempty[d])} & {fmt(mk['Correct'])}/{fmt(mk['Applicable'])} & {pct1(mk['Accuracy (%)'])} & "
                f"{fmt(sun['Correct'])}/{fmt(sun['Applicable'])} & {pct1(sun['Accuracy (%)'])} & "
                f"{fmt(moon['Correct'])}/{fmt(moon['Applicable'])} & {pct1(moon['Accuracy (%)'])} & {fmt(oos)} \\\\\n")

# ---------------------------------------------------------------- Table A3 (per marker)
LNAME = {"ج": "Jīm", "ث": "Thāʾ", "ذ": "Dhāl", "ظ": "Ẓāʾ", "ق": "Qāf"}
with open(OUT / "tableA3_rows.tex", "w", encoding="utf-8") as f:
    for d in ORDER:
        mrows = [r for r in rows if r["Dialect"] == d and r["Measure"].startswith("DMA") and r["Item"] != "all markers"]
        for k, r in enumerate(mrows):
            g, ph = r["Item"].split(" -> ")
            lead = f"\\multirow{{{len(mrows)}}}{{*}}{{{NAME[d]}}}" if k == 0 else ""
            f.write(f"{lead} & {LNAME[g]} (\\AR{{{g}}}) & \\ipa{{{ph}}} & {fmt(r['Correct'])} & {fmt(r['Applicable'])} & {pct1(r['Accuracy (%)'])} \\\\\n")
        f.write("\\midrule\n" if d != ORDER[-1] else "")

# ---------------------------------------------------------------- Table 4 (qualitative)
with open(OUT / "table3_rows.tex", "w", encoding="utf-8") as f:
    prev = None
    for tag, d, txt, gloss in ROWS:
        msa, dia = T(txt, D["MSA"]), T(txt, d)
        assert msa != dia, txt
        if prev and prev != tag:
            f.write("\\midrule\n")
        f.write(f"{tag} & \\AR{{{txt}}} & ``{gloss}'' & \\ipa{{{msa}}} & \\ipa{{{dia}}} \\\\\n"); prev = tag

# ---------------------------------------------------------------- Table A1 (lexicon)
L = {k: IPA_RULES["dialects"][v]["letters"] for k, v in D.items()}
NAMES = [("ء", "Hamza", None), ("أ", "Alif with hamza above", None), ("إ", "Alif with hamza below", None),
         ("آ", "Alif madda", None), ("ئ", "Yāʾ hamza carrier", "a"), ("ؤ", "Wāw hamza carrier", "a"),
         ("ب", "Bāʾ", None), ("ت", "Tāʾ", None), ("ث", "Thāʾ", None), ("ج", "Jīm", None), ("ح", "Ḥāʾ", None),
         ("خ", "Khāʾ", None), ("د", "Dāl", None), ("ذ", "Dhāl", None), ("ر", "Rāʾ", None), ("ز", "Zāy", None),
         ("س", "Sīn", None), ("ش", "Shīn", None), ("ص", "Ṣād", None), ("ض", "Ḍād", None), ("ط", "Ṭāʾ", None),
         ("ظ", "Ẓāʾ", None), ("ع", "ʿAyn", None), ("غ", "Ghayn", None), ("ف", "Fāʾ", None), ("ق", "Qāf", None),
         ("ك", "Kāf", None), ("ل", "Lām", None), ("م", "Mīm", None), ("ن", "Nūn", None), ("ه", "Hāʾ", None),
         ("و", "Wāw", "b"), ("ي", "Yāʾ", "b"), ("ة", "Tāʾ Marbūṭa", "c"),
         ("ڤ", "Vāʾ (loanwords)", None), ("چ", "Chāʾ (loanwords)", None), ("گ", "Gāf (loanwords)", None),
         ("ڨ", "Gāf, Maghrebi form (loanwords)", None), ("پ", "Pāʾ (loanwords)", None)]
prim = lambda d, g: L[d][g]["phoneme"].split(" or ")[0]
with open(OUT / "tableA1_rows.tex", "w", encoding="utf-8") as f:
    for g, n, note in NAMES:
        sup = f"\\textsuperscript{{{note}}}" if note else ""
        f.write(f"{n} (\\AR{{{g}}}){sup} & " + " & ".join(f"\\ipa{{{prim(d, g)}}}" for d in ORDER) + " \\\\\n")
    f.write("Alif, bare (\\AR{ا})\\textsuperscript{d} & " + " & ".join(["\\ipa{/ʔ/}, \\ipa{/aː/}"] * 4) + " \\\\\n")
    f.write("Alif maqṣūra (\\AR{ى}) & " + " & ".join([f"\\ipa{{{T('على', D[d])[-3:-1].join('//')}}}" for d in ORDER]) + " \\\\\n")

# ---------------------------------------------------------------- Table A2 (article)
with open(OUT / "tableA2_rows.tex", "w", encoding="utf-8") as f:
    pr = lambda d, k: IPA_RULES["dialects"][D[d]]["phonological_rules"][k]["ipa"]
    lil = lambda d: IPA_RULES["dialects"][D[d]]["lil_prefix"]
    f.write("Moon (\\AR{القمرية}) & article kept distinct & " + " & ".join(f"\\ipa{{{pr(d, 'al_prefix_moon')}}}" for d in ORDER) + " \\\\\n")
    f.write("Sun (\\AR{الشمسية}) & assimilated, consonant geminated & " + " & ".join(f"\\ipa{{{pr(d, 'al_prefix_sun')}}} + CC" for d in ORDER) + " \\\\\n")
    f.write("\\AR{لل} (\\emph{li-} + article) & like the article & " + " & ".join(f"\\ipa{{{lil(d)}}}" for d in ORDER) + " \\\\\n")
    pv = lambda d: IPA_RULES["dialects"][D[d]]["proclitic_vowel"]["و"]
    f.write("Proclitic + article & vowel on proclitic & " + " & ".join(f"\\ipa{{/{pv(d)}l-/}}" for d in ORDER) + " \\\\\n\\midrule\n")
    for word, gloss, mode in (("القمر", "the moon", "undiacritized"), ("الشمس", "the sun", "undiacritized"),
                              ("الشَّمْس", "the sun", "diacritized"), ("والشمس", "and the sun", "undiacritized"),
                              ("للشمس", "for the sun", "undiacritized")):
        f.write(f"\\AR{{{word}}} ``{gloss}'' & {mode} & " + " & ".join(f"\\ipa{{{T(word, D[d])}}}" for d in ORDER) + " \\\\\n")

# ---------------------------------------------------------------- numbers quoted in the text
def wilson(k, n, z=1.96):
    p = k / n; c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return 100 * (c - h), 100 * (c + h)

art_total = sum(art.values())
macros.update({
    "NTestSentences": fmt(sum(sents.values())),
    "NScored": fmt(sum(nonempty.values())),
    "NEmpty": fmt(sum(sents.values()) - sum(nonempty.values())),
    "NMarkers": fmt(tot["mk"][1]), "NMarkersCorrect": fmt(tot["mk"][0]),
    "NSun": fmt(tot["sun"][1]), "NSunCorrect": fmt(tot["sun"][0]),
    "NMoon": fmt(tot["moon"][1]), "NMoonCorrect": fmt(tot["moon"][0]),
    "NProcArt": fmt(tot["proc"]), "NLilArt": fmt(tot["lil"]),
    "NLearnedOcc": fmt(tot["lrn"]),
    "NLearnedLex": fmt(len(LEARNED)), "NHRoot": fmt(len(H_ROOT)),
    "NLexEntries": fmt(len(IPA_RULES["dialects"]["Egyptian"]["letters"]) + 1),   # + Alif maqṣūra
    "NNonArt": fmt(sum(int(r["Applicable"]) for r in rows if r["Measure"] == "Non-article control")),
    "EngineCommit": subprocess.run(["git", "rev-parse", "--short", ENGINE_COMMIT], cwd=G2P, capture_output=True,
                                   text=True).stdout.strip() or ENGINE_COMMIT,
    "NNonArtCorrect": fmt(sum(int(r["Correct"]) for r in rows if r["Measure"] == "Non-article control")),
    "EnginePRs": "5", "NTanwinLex": fmt(len(TANWIN_ADV)), "NNotArticle": fmt(len(NOT_ARTICLE)),
    "NRelPron": fmt(relpron),
})
for d in ORDER:
    macros[f"NSent{d}"] = fmt(sents[d])
for d in ("EGY", "LEV", "GLF"):
    macros[f"BaseTok{d}"] = f"{100 * base_tok[d][0] / base_tok[d][1]:.1f}"
    macros[f"BaseSent{d}"] = f"{100 * base_sent[d][0] / base_sent[d][1]:.1f}"
# test-suite size and self-test checks, read from the scripts' own output
tests = subprocess.run([sys.executable, "-I", "test_arabic_g2p.py"], cwd=G2P, capture_output=True, text=True).stdout
macros["NTests"] = tests.strip().splitlines()[-1].split()[1].split("/")[1]
st = subprocess.run([sys.executable, "-I", "regenerate_table3.py", "--self-test"], cwd=G2P, capture_output=True, text=True).stdout
macros["NSelfTest"] = str(sum(1 for l in st.splitlines() if l.strip().startswith("[PASS]")))
assert "PASSED" in st, "self-test failed"

with open(OUT / "numbers.tex", "w", encoding="utf-8") as f:
    f.write("% generated by build_tables.py -- do not edit\n")
    for k, v in macros.items():
        f.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
for k, v in macros.items():
    print(f"{k:16} {v}")
