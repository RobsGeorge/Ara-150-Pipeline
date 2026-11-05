"""Turn the completed annotation workbook into the human-evaluation numbers and tables
of the paper. Results are recomputed from the annotators' raw inputs (not from the
workbook's cached formula values).

Usage: python build_human_eval.py G2P_human_evaluation_150.xlsx
Writes generated/human_numbers.tex, generated/table5_rows.tex,
generated/table6_rows.tex and generated/error_classes.tex.
If the workbook is not complete, every number is a red placeholder so that an
unfinished draft cannot be mistaken for the final paper.
"""
import collections
import math
import sys
from pathlib import Path

from openpyxl import load_workbook
import re
ARABIC = re.compile(r"[\u0621-\u064A\u067E\u0686\u06A4\u06A8\u06AF]")

OUT = Path(__file__).parent / "generated"
DIALECTS = ["Egyptian", "Levantine", "Gulf"]
# Items also drawn in a preliminary sample, before the last engine corrections (reported in Section 6.4).
EARLIER_DRAW = {"EGY-028", "LEV-016", "LEV-020", "LEV-029", "LEV-043", "LEV-044", "LEV-048", "GLF-044"}
# English glosses of the words that can be chosen as Table 6 examples
GLOSS = {"بذلته": "I spent it", "التزاماتي": "my commitments", "شخصية": "character", "جراند": "Grant (name)",
         "تنقذه": "she saves him", "التقاء": "meeting", "ولكن": "but", "الڨيديو": "the video"}
ESHORT = {"Dialect consonant": "Cons", "Definite article": "Art", "Long vowel or lexical word": "Long",
          "Foreign name or loanword": "Loan", "Other": "Other"}
TAG = {"Egyptian": "EGY", "Levantine": "LEV", "Gulf": "GLF"}
ERROR_TYPES = ["Dialect consonant", "Definite article", "Long vowel or lexical word",
               "Foreign name or loanword", "Other"]
ERROR_LABEL = {"Dialect consonant": "Dialectal consonants",
               "Definite article": "Definite article",
               "Long vowel or lexical word": "Long vowels and lexical words",
               "Foreign name or loanword": "Foreign names and loanwords",
               "Other": "Other"}
ERROR_GLOSS = {"Dialect consonant": "a consonant realized differently from the dialect",
               "Definite article": "the article's vowel, assimilation, or form, including after a proclitic and in li-l",
               "Long vowel or lexical word": "a written long vowel, a silent letter, tanwīn, Tāʾ Marbūṭa, or the suffix -h realized wrongly, or an irregular frequent word",
               "Foreign name or loanword": "words of non-Arabic origin",
               "Other": "errors outside the classes above, such as abbreviations"}
OK_VALUES = {"ok": "Yes", "not ok": "No"}
YN = {"yes": "Yes", "no": "No"}
ET = {e.lower(): e for e in ERROR_TYPES}


def kappa(pairs):
    """Cohen's kappa for two raters' binary judgments (list of (a, b) with values Yes/No)."""
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    pa = sum(a == "Yes" for a, _ in pairs) / n; pb = sum(b == "Yes" for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else (po - pe) / (1 - pe)


def wilson(k, n, z=1.96):
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return 100 * (c - h), 100 * (c + h)


def esc(x):
    return str(x).replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")


def read(path):
    """Read the adjudication workbook; invalid entries are reported by row and treated as missing."""
    ws = load_workbook(path)["Annotation"]
    rows, bad = [], []
    def val(col, r):
        x = ws[f"{col}{r}"].value
        return " ".join(x.split()) if isinstance(x, str) else x
    def norm(col, r, table):
        x = val(col, r)
        if x in (None, ""):
            return None
        if str(x).lower() not in table:
            bad.append(f"row {r}, column {col}: {x!r}")
            return None
        return table[str(x).lower()]
    for r in range(2, ws.max_row + 1):
        if not val("B", r):
            continue
        a, b = norm("G", r, OK_VALUES), norm("J", r, OK_VALUES)
        adj = norm("M", r, YN)
        final = adj if adj else (a if (a and a == b) else None)
        rows.append(dict(item=val("B", r), annotators={x for x in (val("F", r), val("I", r)) if x}, dialect=val("C", r),
                         a=a, b=b, final=final, etype=norm("O", r, ET),
                         words=[t for t in str(val("D", r) or "").split() if ARABIC.search(t)],
                         word=val("P", r) or "", wrong=val("Q", r) or "", right=val("R", r) or ""))
    for x in bad:
        print("  INVALID", x)
    return rows


def main(path):
    rows = read(path)
    complete = len(rows) == 150 and all(r["final"] in ("Yes", "No") for r in rows) \
        and all(r["etype"] for r in rows if r["final"] == "No")
    PH = "\\textcolor{red}{\\textbf{XX}}"
    m, t5, t6, ec = {}, [], [], []
    if complete:
        tot_k = tot_n = 0
        for d in DIALECTS:
            sub = [r for r in rows if r["dialect"] == d]
            k, n = sum(r["final"] == "Yes" for r in sub), len(sub)
            tot_k += k; tot_n += n
            lo, hi = wilson(k, n)
            m[f"HumanCorrect{TAG[d]}"] = str(k); m[f"HumanAcc{TAG[d]}"] = f"{100 * k / n:.1f}"
            m[f"HumanErrors{TAG[d]}"] = str(n - k)
            for e, short in ESHORT.items():
                m[f"HumanErr{TAG[d]}{short}"] = str(sum(r["final"] == "No" and r["etype"] == e for r in sub))
            m[f"HumanCI{TAG[d]}"] = f"{lo:.1f}--{hi:.1f}"
            t5.append(f"{d} ({TAG[d]}) & {n} & {k} & {100 * k / n:.1f} & {lo:.1f}--{hi:.1f} \\\\")
            kd = kappa([(r["a"], r["b"]) for r in sub])
            m[f"HumanKappa{TAG[d]}"] = f"{kd:.2f}" if kd is not None else "n/a"
        lo, hi = wilson(tot_k, tot_n)
        dis = sum(r["a"] != r["b"] for r in rows)
        errs = [r for r in rows if r["final"] == "No"]
        m["HumanAnnotators"] = str(len(set().union(*(r["annotators"] for r in rows))) or "") if any(r["annotators"] for r in rows) else PH
        kt = kappa([(r["a"], r["b"]) for r in rows])
        m["HumanKappa"] = f"{kt:.2f}" if kt is not None else "n/a"
        strict = sum(r["a"] == r["b"] == "Yes" for r in rows)
        lenient = sum("Yes" in (r["a"], r["b"]) for r in rows)
        m.update(HumanStrictN=str(strict), HumanStrictAcc=f"{100 * strict / len(rows):.1f}",
                 HumanLenientN=str(lenient), HumanLenientAcc=f"{100 * lenient / len(rows):.1f}",
                 HumanDisagreeYes=str(sum(r["a"] != r["b"] and r["final"] == "Yes" for r in rows)))
        rest = [r for r in rows if r["item"] not in EARLIER_DRAW]
        m.update(HumanEarlierN=str(len(rows) - len(rest)), HumanRestN=str(len(rest)),
                 HumanRestCorrect=str(sum(r["final"] == "Yes" for r in rest)),
                 HumanRestAcc=f"{100 * sum(r['final'] == 'Yes' for r in rest) / len(rest):.1f}")
        m.update(HumanN=str(tot_n), HumanCorrect=str(tot_k), HumanAcc=f"{100 * tot_k / tot_n:.1f}",
                 HumanCI=f"{lo:.1f}--{hi:.1f}", HumanDisagree=str(dis),
                 HumanAgree=f"{100 * (tot_n - dis) / tot_n:.1f}", HumanAgreeN=str(tot_n - dis), HumanErrors=str(len(errs)))
        nw = sum(len(r["words"]) for r in rows)
        m.update(HumanWords=f"{nw:,}" if nw >= 10000 else str(nw), HumanWordsCorrect=str(nw - len(errs)),
                 HumanWordAcc=f"{100 * (nw - len(errs)) / nw:.1f}")
        t5 += ["\\midrule", f"Overall & {tot_n} & {tot_k} & {100 * tot_k / tot_n:.1f} & {lo:.1f}--{hi:.1f} \\\\"]
        counts = collections.Counter(r["etype"] for r in errs)
        items = []
        for e in ERROR_TYPES:
            if counts[e]:
                items.append(f"  \\item \\textbf{{{ERROR_LABEL[e]}}} ({counts[e]} of {len(errs)} incorrect sentences, "
                             f"{100 * counts[e] / len(errs):.0f}\\%): {ERROR_GLOSS[e]}.")
                # example from the dialect with most errors of this class (ties: GLF, LEV, EGY), first in item order
                cand = [r for r in errs if r["etype"] == e and r["word"] and r["wrong"] and r["right"]
                        and not re.search(r"[0-9]", r["word"]) and r["word"] not in ("الذي", "التي", "الذين", "والتي", "قحلاء")]   # relative pronouns, digits and a rare classical adjective are not chosen as examples
                order = {"Gulf": 0, "Levantine": 1, "Egyptian": 2}
                best = max(DIALECTS, key=lambda d: (sum(r["dialect"] == d for r in cand), -order[d])) if cand else None
                ex = next((r for r in cand if r["dialect"] == best), None)
                if ex:
                    gloss = f" ``{GLOSS[ex['word']]}''" if ex["word"] in GLOSS else ""
                    t6.append(f"{ERROR_LABEL[e]} & {TAG[ex['dialect']]} & \\AR{{{ex['word']}}}{gloss} & \\ipa{{{esc(ex['wrong'])}}} & \\ipa{{{esc(ex['right'])}}} \\\\")
        ec = ["\\begin{itemize}"] + items + ["\\end{itemize}"] if items else ["No errors were found."]
    else:
        for d in DIALECTS:
            m[f"HumanCorrect{TAG[d]}"] = PH; m[f"HumanAcc{TAG[d]}"] = PH; m[f"HumanCI{TAG[d]}"] = PH
            t5.append(f"{d} ({TAG[d]}) & 50 & {PH} & {PH} & {PH} \\\\")
            m[f"HumanKappa{TAG[d]}"] = PH
        m.update(HumanAnnotators=PH, HumanN="150", HumanCorrect=PH, HumanAcc=PH, HumanCI=PH, HumanDisagree=PH,
                 HumanAgree=PH, HumanAgreeN=PH, HumanWords=PH, HumanWordsCorrect=PH, HumanWordAcc=PH, HumanErrors=PH, HumanKappa=PH)
        t5 += ["\\midrule", f"Overall & 150 & {PH} & {PH} & {PH} \\\\"]
        t6 = [f"{PH} & & & & \\\\"]
        m.update(HumanEarlierN=PH, HumanRestN=PH, HumanRestCorrect=PH, HumanRestAcc=PH, HumanStrictN=PH,
                 HumanStrictAcc=PH, HumanLenientN=PH, HumanLenientAcc=PH, HumanDisagreeYes=PH)
        for d in DIALECTS:
            m[f"HumanErrors{TAG[d]}"] = PH
            for short in ESHORT.values():
                m[f"HumanErr{TAG[d]}{short}"] = PH
        ec = [f"{PH}: error classes and counts are generated from the completed annotation workbook."]
    m["HumanComplete"] = "1" if complete else "0"
    OUT.mkdir(exist_ok=True)
    (OUT / "human_numbers.tex").write_text("% generated by build_human_eval.py -- do not edit\n" +
                                           "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in m.items()), encoding="utf-8")
    (OUT / "table5_rows.tex").write_text("\n".join(t5) + "\n", encoding="utf-8")
    (OUT / "table6_rows.tex").write_text("\n".join(t6) + "\n", encoding="utf-8")
    (OUT / "error_classes.tex").write_text("\n".join(ec) + "\n", encoding="utf-8")
    print("complete" if complete else f"INCOMPLETE ({sum(r['final'] in ('Yes','No') for r in rows)}/150 final decisions): placeholders written")
    for k, v in m.items():
        print(f"  {k:18} {v}")


if __name__ == "__main__":
    main(sys.argv[1])
