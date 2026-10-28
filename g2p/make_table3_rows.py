"""Emit the qualitative-comparison table rows (Table 3) directly from the engine.
Both columns come from the same engine: the MSA ruleset and the dialect ruleset."""
from arabic_g2p_rules import transcribe_protected as T

MSA = "Modern Standard Arabic (MSA)"
ROWS = [
    ("EGY", "Egyptian",         "الجو جميل",      "the weather is nice"),
    ("EGY", "Egyptian",         "قال لي الجار",   "the neighbour told me"),
    ("LEV", "Levantine Arabic", "شو القصة",       "what's the story"),
    ("LEV", "Levantine Arabic", "الجو حلو اليوم", "the weather is nice today"),
    ("GLF", "Khaliji Arabic",   "هذا الثوب",      "this is the garment"),
    ("GLF", "Khaliji Arabic",   "عقلك الباطن",    "your subconscious"),
]

if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "results/table3_rows.tex"
    with open(out, "w", encoding="utf-8") as f:
        for tag, d, txt, gloss in ROWS:
            msa, dia = T(txt, MSA), T(txt, d)
            assert msa != dia, f"row shows no dialectal contrast: {txt}"
            line = f"{tag} & \\AR{{{txt}}} & ``{gloss}'' & \\ipa{{{msa}}} & \\ipa{{{dia}}} \\\\"
            f.write(line + "\n"); print(line)
    print(f"\nWritten: {out}")
