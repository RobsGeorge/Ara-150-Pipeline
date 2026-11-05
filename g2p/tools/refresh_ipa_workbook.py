"""Regenerate the engine-output columns of IPA_Phonemes.xlsx from the engine.

Usage: python tools/refresh_ipa_workbook.py [IPA_Phonemes.xlsx]

Updates, in place:
  - Diacritized_Examples, Dialectal_Contrasts, Sun_Moon_Examples, Edge_Cases: the EGY, KHA,
    LEV and MSA columns are the engine's output for the Arabic input of each row;
  - Engine_Validation: engine output and PASS/FAIL against the expected substring;
  - every IPA string (between slashes): ASCII g is written as IPA ɡ (U+0261);
  - Contents: a note on which sheets are engine output and which are descriptive.
"""
import os
import re
import sys

from openpyxl import load_workbook

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from arabic_g2p_rules import transcribe_protected  # noqa: E402

PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                         "IPA_Phonemes.xlsx")
DIALECT = {"EGY": "Egyptian", "KHA": "Khaliji Arabic", "LEV": "Levantine Arabic", "MSA": "Modern Standard Arabic (MSA)"}
INPUT = {"Diacritized_Examples": "Diacritized Arabic Word", "Dialectal_Contrasts": "Arabic Word",
         "Sun_Moon_Examples": "Arabic", "Edge_Cases": "Arabic"}
IPA = re.compile(r"/[^/\s][^/]*/")

wb = load_workbook(PATH)
changed = 0
for name, inp in INPUT.items():
    ws = wb[name]
    hdr = [str(c.value or "").strip() for c in ws[1]]
    src = hdr.index(inp) + 1
    cols = {tag: i + 1 for i, h in enumerate(hdr) for tag in DIALECT if h in (tag, f"{tag} IPA")}
    for r in range(2, ws.max_row + 1):
        word = ws.cell(r, src).value
        if not word:
            continue
        for tag, c in cols.items():
            new = transcribe_protected(str(word).strip(), DIALECT[tag])
            if ws.cell(r, c).value != new:
                ws.cell(r, c).value = new
                changed += 1

ws = wb["Engine_Validation"]
hdr = [str(c.value or "").strip() for c in ws[1]]
ci, cd, ce, co, cs = (hdr.index(h) + 1 for h in ("Arabic Input", "Dialect", "Expected (must contain)", "Engine Output", "Status"))
for r in range(2, ws.max_row + 1):
    word, dialect = ws.cell(r, ci).value, ws.cell(r, cd).value
    if not word:
        continue
    exp = str(ws.cell(r, ce).value or "")
    exp = exp if "<" in exp else exp.replace("g", "ɡ")          # IPA substring; tags such as <eng> unchanged
    out = transcribe_protected(str(word), dialect)
    for c, v in ((ce, exp), (co, out), (cs, "PASS" if exp in out else "FAIL")):
        if ws.cell(r, c).value != v:
            ws.cell(r, c).value = v
            changed += 1

for sheet in wb.worksheets:                                   # ASCII g inside IPA strings
    for row in sheet.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and "g" in cell.value:
                new = IPA.sub(lambda m: m.group(0).replace("g", "ɡ"), cell.value)
                if new != cell.value:
                    cell.value = new
                    changed += 1

ws = wb["Contents"]
NOTE = ("Engine output: the dialect columns of Diacritized_Examples, Dialectal_Contrasts, Sun_Moon_Examples, "
        "Edge_Cases and Engine_Validation are regenerated from the engine by tools/refresh_ipa_workbook.py. "
        "The word transcriptions of the IPA sheet are descriptive (with vowels and stress), not engine output.")
if not any(c.value == NOTE for row in ws.iter_rows() for c in row):
    ws.cell(ws.max_row + 2, 1).value = NOTE
    changed += 1
ev = wb["Engine_Validation"]
fails = sum(1 for r in range(2, ev.max_row + 1) if ev.cell(r, cs).value == "FAIL")
for r in range(2, ev.max_row + 1):                            # summary row
    if ev.cell(r, 1).value == "TOTAL":
        ev.cell(r, cs).value = "ALL PASS" if not fails else f"{fails} FAIL"
wb.save(PATH)
print(f"{changed} cells updated; Engine_Validation failures: {fails}")
