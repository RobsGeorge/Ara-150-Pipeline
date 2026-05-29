"""
diacritize_then_g2p.py
======================
End-to-end diacritize-then-G2P pipeline for Arabic.

Architecture (resolves the short-vowel limitation of pure orthographic G2P):

    raw text  ->  diacritizer  ->  G2P engine  ->  fully-vocalized IPA
                  (CAMeL/Mishkal)   (rule-based, our engine)

Install:
    # Option A: CAMeL Tools (recommended; MSA-strong)
    pip install camel-tools
    camel_data -i disambig-mle-calima-msa-r13

    # Option B: Mishkal (lightweight)
    pip install mishkal

Usage:
    python diacritize_then_g2p.py --text "كتب المدرس على السبورة" --dialect MSA
    python diacritize_then_g2p.py --input-csv transcripts.csv --output-csv ipa.csv \\
                                   --backend camel   # or mishkal | none
"""
import argparse, sys, csv
from arabic_g2p_rules import transcribe_protected

def get_camel_diacritizer():
    """Returns a callable(text) -> diacritized_text using CAMeL Tools."""
    from camel_tools.disambig.mle import MLEDisambiguator
    mle = MLEDisambiguator.pretrained()
    def diacritize(text):
        if not text or not text.strip(): return text
        toks = text.split()
        out = []
        for d in mle.disambiguate(toks):
            diac = d.analyses[0].analysis.get('diac') if d.analyses else None
            out.append(diac or d.word)
        return " ".join(out)
    return diacritize

def get_mishkal_diacritizer():
    from mishkal.tashkeel import TashkeelClass
    tc = TashkeelClass()
    def diacritize(text):
        if not text or not text.strip(): return text
        return tc.tashkeel(text)
    return diacritize

DIALECT_MAP = {
    'EGY': 'Egyptian', 'Egyptian': 'Egyptian',
    'LEV': 'Levantine Arabic', 'Levantine': 'Levantine Arabic',
    'KHA': 'Khaliji Arabic', 'Gulf': 'Khaliji Arabic', 'GLF': 'Khaliji Arabic',
    'MSA': 'Modern Standard Arabic (MSA)',
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--text', help='Single Arabic sentence to phonemize')
    ap.add_argument('--input-csv', help='Batch mode: CSV with Transcript + Dialect columns')
    ap.add_argument('--output-csv', default='diacritized_ipa.csv')
    ap.add_argument('--dialect', default='MSA')
    ap.add_argument('--text-col', default='Transcript')
    ap.add_argument('--dialect-col', default='Main Dialect')
    ap.add_argument('--backend', choices=['camel', 'mishkal', 'none'], default='camel',
                    help='Diacritizer to use. "none" = pass through (skeleton output).')
    args = ap.parse_args()

    if args.backend == 'camel':
        try: diac = get_camel_diacritizer()
        except Exception as e:
            print(f"ERROR: CAMeL Tools unavailable ({e}). Install with: pip install camel-tools "
                  "&& camel_data -i disambig-mle-calima-msa-r13", file=sys.stderr); sys.exit(1)
    elif args.backend == 'mishkal':
        try: diac = get_mishkal_diacritizer()
        except Exception as e:
            print(f"ERROR: Mishkal unavailable ({e}). Install with: pip install mishkal",
                  file=sys.stderr); sys.exit(1)
    else:
        diac = lambda t: t  # identity

    if args.text:
        d = DIALECT_MAP.get(args.dialect, args.dialect)
        diacritized = diac(args.text)
        ipa = transcribe_protected(diacritized, d)
        print(f"Input       : {args.text}")
        print(f"Diacritized : {diacritized}")
        print(f"Dialect     : {d}")
        print(f"IPA         : {ipa}")
        return

    if not args.input_csv:
        ap.error("Provide --text OR --input-csv")
    with open(args.input_csv, encoding='utf-8') as f, \
         open(args.output_csv, 'w', encoding='utf-8', newline='') as g:
        rdr = csv.DictReader(f); rows = list(rdr)
        fns = rdr.fieldnames + ['Diacritized', 'Phoneme_diacritized']
        wtr = csv.DictWriter(g, fieldnames=fns); wtr.writeheader()
        for i, row in enumerate(rows, 1):
            txt = (row.get(args.text_col) or '').strip()
            raw_d = (row.get(args.dialect_col) or 'MSA').strip()
            d = DIALECT_MAP.get(raw_d, 'Modern Standard Arabic (MSA)')
            if txt:
                diacritized = diac(txt)
                ipa = transcribe_protected(diacritized, d)
            else: diacritized, ipa = '', ''
            row['Diacritized'] = diacritized; row['Phoneme_diacritized'] = ipa
            wtr.writerow(row)
            if i % 500 == 0: print(f"  processed {i}/{len(rows)}", file=sys.stderr)
        print(f"Wrote {len(rows)} rows -> {args.output_csv}", file=sys.stderr)

if __name__ == '__main__':
    main()
