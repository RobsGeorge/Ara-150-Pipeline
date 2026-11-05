"""Write the public release of the human evaluation from the completed workbooks.

Usage: python publish_annotations.py <dir with the 7 completed workbooks> <output dir>

Writes
  judgments_150.csv / .xlsx  one row per sentence: both annotators' judgments, the final
                             (adjudicated) judgment and the error details;
  annotator_*.xlsx, G2P_human_evaluation_150.xlsx
                             the workbooks with the free-text note columns emptied and the
                             file properties (author, last editor, dates) cleared; in the
                             adjudication workbook, the annotators' columns hold only the
                             structured error details, and formula columns hold their values.
Judgments and error details are copied unchanged. Free-text notes are not released.
"""
import csv
import datetime as dt
import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

SRC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
EPOCH = dt.datetime(2026, 11, 5)
OK = {"ok": "OK", "not ok": "Not OK"}


def clean(x):
    return " ".join(x.split()) if isinstance(x, str) else x


def edge(word):
    """Strip punctuation at the edges of a quoted word (قولا. -> قولا)."""
    return word.strip(".,;:!?،؛؟\"'()[]«» ")


def scrub_props(wb):
    p = wb.properties
    p.creator = "Ara-150 G2P study"
    p.lastModifiedBy = None
    p.title = p.subject = p.description = p.keywords = p.category = None
    p.created = p.modified = EPOCH
    p.lastPrinted = None


# 1. individual workbooks: empty the Notes column (J)
details = {}
for tag in ("EGY", "LEV", "GLF"):
    for slot in "AB":
        name = f"annotator_{tag}-{slot}.xlsx"
        wb = load_workbook(SRC / name)
        ws = wb["Annotation"]
        assert ws["J1"].value == "Notes", ws["J1"].value
        for r in range(2, ws.max_row + 1):
            item = ws[f"B{r}"].value
            if item:
                details[(item, slot)] = {c: clean(ws[f"{c}{r}"].value) for c in "EFGHI"}
                ws[f"J{r}"] = None
        scrub_props(wb)
        wb.save(OUT / name)

# 2. adjudication workbook: rebuild H/K from the structured fields only; empty the adjudication note (T)
name = "G2P_human_evaluation_150.xlsx"
wb = load_workbook(SRC / name)
ws = wb["Annotation"]
hdr = {ws.cell(1, c).value: ws.cell(1, c).column_letter for c in range(1, ws.max_column + 1)}
assert hdr["A: Notes"] == "H" and hdr["B: Notes"] == "K" and hdr["Adjudication note"] == "T"
assert hdr["Initial disagreement"] == "L" and hdr["Final: correct"] == "N"
ws["H1"], ws["K1"] = "A: error details", "B: error details"
rows = []
for r in range(2, ws.max_row + 1):
    item = ws[f"B{r}"].value
    if not item:
        continue
    for slot, col, jcol in (("A", "H", "G"), ("B", "K", "J")):
        d = details[(item, slot)]
        assert OK[d["E"].lower()] == ws[f"{jcol}{r}"].value, (item, slot)       # judgments unchanged
        ws[f"{col}{r}"] = " | ".join(f"{k}: {v}" for k, v in (("type", d["F"]), ("word", d["G"]),
                                                               ("engine", d["H"]), ("correct", d["I"])) if v) or None
    ws[f"T{r}"] = None
    a, b, adj = ws[f"G{r}"].value, ws[f"J{r}"].value, clean(ws[f"M{r}"].value)
    final = adj if adj else ("Yes" if a == b == "OK" else "No" if a == b == "Not OK" else None)
    assert final in ("Yes", "No"), item
    ws[f"L{r}"] = "Yes" if a != b else "No"                      # values instead of formulas
    ws[f"N{r}"] = final
    rows.append([item, ws[f"S{r}"].value, ws[f"C{r}"].value, ws[f"D{r}"].value, ws[f"E{r}"].value, a, b,
                 "Yes" if a != b else "No", final] +
                ([edge(clean(ws[f"{c}{r}"].value) or "") if c == "P" else clean(ws[f"{c}{r}"].value) or ""
                  for c in "OPQR"] if final == "No" else ["", "", "", ""]))
scrub_props(wb)
wb.save(OUT / name)

# 3. the sentence-level table
HEAD = ["Item", "Corpus ID", "Dialect", "Sentence", "Engine IPA", "Annotator A", "Annotator B",
        "Initial disagreement", "Final: correct", "Error type", "Wrong word", "Engine IPA of that word", "Correct IPA"]
with open(OUT / "judgments_150.csv", "w", encoding="utf-8-sig", newline="") as f:
    csv.writer(f).writerows([HEAD] + rows)
t = Workbook(); s = t.active; s.title = "Judgments"
s.append(HEAD)
for x in rows:
    s.append(x)
for c in s[1]:
    c.font = Font(bold=True)
s.freeze_panes = "A2"; s.sheet_view.rightToLeft = False
for col, w in zip("ABCDEFGHIJKLM", (9, 10, 10, 60, 60, 11, 11, 11, 10, 24, 14, 18, 18)):
    s.column_dimensions[col].width = w
scrub_props(t)
t.save(OUT / "judgments_150.xlsx")
print(f"{len(rows)} sentences; {sum(r[8] == 'Yes' for r in rows)} correct; files in {OUT}")
