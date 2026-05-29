"""Test suite for the expert-revised Arabic G2P rules. Run: python3 test_rules.py"""
from arabic_g2p_rules import transcribe_protected, transcribe_arabic, get_rules, SUN_LETTERS, MOON_LETTERS

def t(word, dialect, must_contain=None, must_equal=None, must_not_contain=None, diacritize=False):
    out = transcribe_protected(word, dialect, diacritize=diacritize)
    ok = True; reasons=[]
    if must_equal is not None and out != must_equal:
        ok=False; reasons.append(f"!= '{must_equal}'")
    if must_contain is not None and must_contain not in out:
        ok=False; reasons.append(f"missing '{must_contain}'")
    if must_not_contain is not None and must_not_contain in out:
        ok=False; reasons.append(f"contains '{must_not_contain}'")
    print(f"  [{'PASS' if ok else 'FAIL'}] {word:<22} [{dialect[:12]:<12}] -> {out:<26} {';'.join(reasons)}")
    return ok

results=[]
print("== 1. Sun-letter assimilation (lam IS a sun letter) ==")
results.append(t("الشمس","Egyptian", must_contain="ʃʃ"))                 # ش doubles
results.append(t("الليل","Egyptian", must_contain="ll"))                 # ل now geminates
results.append(t("الليل","Modern Standard Arabic (MSA)", must_contain="ll"))
results.append(t("النور","Modern Standard Arabic (MSA)", must_contain="nn"))  # ن doubles
results.append(t("الرحمن","Modern Standard Arabic (MSA)", must_contain="rr"))

print("\n== 2. Moon-letter (no gemination) ==")
results.append(t("القمر","Egyptian", must_contain="el-"))                # moon, EGY prefix
results.append(t("القمر","Modern Standard Arabic (MSA)", must_contain="al-"))
results.append(t("الكتاب","Modern Standard Arabic (MSA)", must_contain="al-"))

print("\n== 3. Dialectal article vowel ==")
results.append(t("الشمس","Khaliji Arabic", must_contain="ɪ-"))
results.append(t("الشمس","Levantine Arabic", must_contain="ɪ-"))
results.append(t("الشمس","Modern Standard Arabic (MSA)", must_contain="a-"))

print("\n== 4. Hamza = glottal stop /ʔ/ (no spurious /æ/) ==")
results.append(t("سماء","Egyptian", must_contain="ʔ", must_not_contain="æ"))
results.append(t("أمر","Egyptian", must_contain="ʔ"))
results.append(t("إيمان","Egyptian", must_contain="ʔi"))                 # إ inherent kasra
results.append(t("آمن","Modern Standard Arabic (MSA)", must_contain="ʔaː"))  # madda

print("\n== 5. Bare alif: word-initial /ʔ/ onset, medial /aː/ ==")
results.append(t("اسم","Egyptian", must_contain="ʔ", must_not_contain="aːsm"))  # initial -> glottal
results.append(t("قال","Khaliji Arabic", must_equal="/gaːl/"))           # medial -> long aː
results.append(t("قال","Levantine Arabic", must_equal="/ʔaːl/"))
results.append(t("باب","Modern Standard Arabic (MSA)", must_contain="aː"))

print("\n== 6. Dialect consonant shifts ==")
results.append(t("جميل","Egyptian", must_contain="ɡ"))                   # ج -> g
results.append(t("جميل","Levantine Arabic", must_contain="ʒ"))           # ج -> ʒ
results.append(t("جميل","Khaliji Arabic", must_contain="dʒ"))            # ج -> dʒ
results.append(t("قلب","Khaliji Arabic", must_contain="g"))              # ق -> g
results.append(t("قلب","Modern Standard Arabic (MSA)", must_contain="q"))# ق -> q
results.append(t("ثوم","Khaliji Arabic", must_contain="θ"))              # ث preserved
results.append(t("ثوم","Egyptian", must_contain="t"))                    # ث -> t

print("\n== 7. Shadda gemination ==")
results.append(t("سكّر","Egyptian", must_contain="kk"))                  # ّ doubles ك

print("\n== 8. Lexical shield (English untouched) ==")
results.append(t("خرج ال<eng>boy</eng>","Egyptian", must_contain="<eng>boy</eng>"))

print("\n== 9. DIACRITIZE-THEN-G2P: short vowels recovered from diacritized input ==")
# When the diacritizer (or pre-diacritized text) supplies harakat, full vowels appear:
results.append(t("كَتَبَ","Egyptian", must_equal="/kataba/"))            # full short vowels
results.append(t("كِتَاب","Modern Standard Arabic (MSA)", must_contain="kitaːb"))
results.append(t("مُدَرِّس","Modern Standard Arabic (MSA)", must_contain="mudarris"))  # shadda+vowels
results.append(t("مَدْرَسَة","Modern Standard Arabic (MSA)", must_equal="/madrasa/", must_not_contain="aa"))  # taa marbuta + fatha merge
results.append(t("شَجَرَة","Modern Standard Arabic (MSA)", must_equal="/ʃadʒara/"))  # ة after fatha doesn't double

print("\n== 10. Sun/Moon partition sanity ==")
canonical_moon=set("ءبجحخعغفقكمهوي"); results.append(("PARTITION", len(SUN_LETTERS)==14 and canonical_moon.issubset(MOON_LETTERS) and not (SUN_LETTERS & MOON_LETTERS)))
print(f"  [{'PASS' if results[-1][1] else 'FAIL'}] 14 sun letters, disjoint from moon (sun={len(SUN_LETTERS)})")
results[-1]=results[-1][1]

passed=sum(1 for r in results if r); total=len(results)
print(f"\n==== {passed}/{total} tests passed ====")
import sys; sys.exit(0 if passed==total else 1)
