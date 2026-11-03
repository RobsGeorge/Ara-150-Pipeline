"""Merge the six annotator workbooks into the adjudication workbook.

Usage: python merge_annotations.py <G2P_human_evaluation_150.xlsx> <dir with annotator_*.xlsx> <output.xlsx>

For every item, copies annotator A's and B's judgment into columns G and J and their error
details and notes into H and K. Where both said Not OK, the error columns O-R are pre-filled
from annotator A for the adjudicators to confirm. Invalid or missing judgments are reported.
"""
import sys
from pathlib import Path

from openpyxl import load_workbook

master, src, out = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
OK = {"ok": "OK", "not ok": "Not OK"}
wb = load_workbook(master); ws = wb["Annotation"]
row_of = {ws[f"B{r}"].value: r for r in range(2, ws.max_row + 1) if ws[f"B{r}"].value}
problems = []
for tag in ("EGY", "LEV", "GLF"):
    for slot, (jc, nc) in (("A", ("G", "H")), ("B", ("J", "K"))):
        f = src / f"annotator_{tag}-{slot}.xlsx"
        if not f.exists():
            problems.append(f"missing file {f.name}"); continue
        a = load_workbook(f)["Annotation"]
        for r in range(2, a.max_row + 1):
            item = a[f"B{r}"].value
            if not item:
                continue
            if item not in row_of:
                problems.append(f"{f.name} row {r}: unknown item {item}"); continue
            m = row_of[item]
            val = lambda c: (" ".join(str(a[f"{c}{r}"].value).split()) if a[f"{c}{r}"].value not in (None, "") else "")
            j = OK.get(val("E").lower())
            if not j:
                problems.append(f"{f.name} row {r} ({item}): judgment {val('E')!r}")
            ws[f"{jc}{m}"] = j
            details = " | ".join(x for x in (val("F") and f"type: {val('F')}", val("G") and f"word: {val('G')}",
                                             val("H") and f"engine: {val('H')}", val("I") and f"correct: {val('I')}",
                                             val("J")) if x)
            ws[f"{nc}{m}"] = details or None
            if slot == "A":
                ws[f"O{m}"], ws[f"P{m}"], ws[f"Q{m}"], ws[f"R{m}"] = (val("F") or None, val("G") or None,
                                                                      val("H") or None, val("I") or None)
# keep the pre-filled error details only where both annotators said Not OK
for m in row_of.values():
    if not (ws[f"G{m}"].value == "Not OK" and ws[f"J{m}"].value == "Not OK"):
        for c in "OPQR":
            ws[f"{c}{m}"] = None
wb.save(out)
print(f"saved {out}; {len(problems)} problem(s)")
for p in problems:
    print("  ", p)
