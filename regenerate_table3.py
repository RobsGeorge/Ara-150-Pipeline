"""
regenerate_table3.py
====================
Re-computes the Dialectal Markedness Accuracy (DMA) numbers reported in
Paper 2's Table 3, using the CORRECTED Arabic G2P engine.

Usage:
    python regenerate_table3.py --test-csv path/to/test_split.csv \
                                --output table3_regenerated.csv

The test CSV must contain at minimum these columns:
    - Transcript     : Arabic text input
    - Main Dialect   : one of {Egyptian, Khaliji, Levantine, MSA}
    - (optional) gold_phoneme : reference IPA for accuracy computation

If gold_phoneme is absent, the script reports MARKER-shift rates only
(how often each dialect-specific rule fires), not full-string accuracy.

The markers reported correspond to Table 3's rows:
    Jeem→/g/    : Egyptian dialect marker
    Qaf→/g/     : Khaliji dialect marker
    Tha→/t/     : Egyptian/Levantine dialect marker
    Thal→/d/    : Egyptian/Levantine dialect marker
    Zha→/zˤ/    : Egyptian/Levantine dialect marker
    Sun-Letter assimilation (e.g. الليل→/ll/)  : all dialects
"""
import argparse, sys, csv, re
from collections import defaultdict
# expects arabic_g2p_rules.py on PYTHONPATH or alongside this script
from arabic_g2p_rules import transcribe_protected, SUN_LETTERS

DIALECT_NORM = {
    'Egyptian': 'Egyptian',
    'EGY': 'Egyptian',
    'Levantine': 'Levantine Arabic',
    'LEV': 'Levantine Arabic',
    'Khaliji': 'Khaliji Arabic',
    'Gulf':    'Khaliji Arabic',
    'GLF':     'Khaliji Arabic',
    'KHA':     'Khaliji Arabic',
    'MSA':     'Modern Standard Arabic (MSA)',
}

# Expected markers per dialect (which letter -> which surface phoneme)
MARKERS = {
    'Egyptian':         {'ج': 'ɡ', 'ث': 't', 'ذ': 'd', 'ظ': 'zˤ', 'ق': 'ʔ'},
    'Levantine Arabic': {'ج': 'ʒ', 'ث': 't', 'ذ': 'd', 'ظ': 'zˤ', 'ق': 'ʔ'},
    'Khaliji Arabic':   {'ج': 'dʒ', 'ث': 'θ', 'ذ': 'ð', 'ظ': 'ðˤ', 'ق': 'g'},
    'Modern Standard Arabic (MSA)': {'ج': 'dʒ', 'ث': 'θ', 'ذ': 'ð', 'ظ': 'ðˤ', 'ق': 'q'},
}

def applies(txt, marker_letter, expected_phoneme, dialect_full):
    """Return (fired, expected_fired) for one marker on one sentence."""
    expected_fired = marker_letter in txt
    if not expected_fired:
        return False, False
    ipa = transcribe_protected(txt, dialect_full)
    return (expected_phoneme in ipa), True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--test-csv', required=True)
    ap.add_argument('--output', default='table3_regenerated.csv')
    ap.add_argument('--text-col', default='Transcript')
    ap.add_argument('--dialect-col', default='Main Dialect')
    args = ap.parse_args()

    counts = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # dialect -> marker -> [fired, total]
    sun_assim = defaultdict(lambda: [0, 0])
    total_by_dialect = defaultdict(int)

    with open(args.test_csv, encoding='utf-8') as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            text = (row.get(args.text_col) or '').strip()
            raw_d = (row.get(args.dialect_col) or '').strip()
            d = DIALECT_NORM.get(raw_d)
            if not text or not d: continue
            total_by_dialect[d] += 1
            for letter, expected_ph in MARKERS[d].items():
                fired, tot = applies(text, letter, expected_ph, d)
                if tot:
                    counts[d][letter][1] += 1
                    if fired: counts[d][letter][0] += 1
            # Sun-letter assimilation
            for word in text.split():
                if len(word) >= 3 and word[0] == 'ا' and word[1] == 'ل' and word[2] in SUN_LETTERS:
                    sun_assim[d][1] += 1
                    ipa = transcribe_protected(word, d)
                    expected_ch = MARKERS[d].get(word[2], None)
                    geminate_ch = expected_ch if expected_ch else None
                    if geminate_ch and (geminate_ch + geminate_ch) in ipa:
                        sun_assim[d][0] += 1
                    elif geminate_ch is None and word[2]*2 in ipa:
                        sun_assim[d][0] += 1

    # Write CSV
    with open(args.output, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Dialect', 'Marker', 'Fired', 'Applicable', 'DMA (%)'])
        for d, total in total_by_dialect.items():
            for letter, (fired, total_app) in counts[d].items():
                rate = 100 * fired / total_app if total_app else float('nan')
                w.writerow([d, f"{letter} -> {MARKERS[d][letter]}", fired, total_app, f"{rate:.2f}"])
            sa = sun_assim[d]
            if sa[1]:
                rate = 100 * sa[0] / sa[1]
                w.writerow([d, "Sun-Letter assimilation", sa[0], sa[1], f"{rate:.2f}"])

    print(f"\nDMA report written to: {args.output}")
    print(f"Test corpus: {sum(total_by_dialect.values())} sentences across {len(total_by_dialect)} dialects.")
    for d, n in total_by_dialect.items(): print(f"  {d}: {n}")
    print("\nPaste the CSV contents into Paper 2's Table 3 cells.")

if __name__ == '__main__':
    main()
