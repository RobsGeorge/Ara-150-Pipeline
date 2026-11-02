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
results.append(t("قال","Khaliji Arabic", must_equal="/ɡaːl/"))           # medial -> long aː
results.append(t("قال","Levantine Arabic", must_equal="/ʔaːl/"))
results.append(t("باب","Modern Standard Arabic (MSA)", must_contain="aː"))

print("\n== 6. Dialect consonant shifts ==")
results.append(t("جميل","Egyptian", must_contain="ɡ"))                   # ج -> g
results.append(t("جميل","Levantine Arabic", must_contain="ʒ"))           # ج -> ʒ
results.append(t("جميل","Khaliji Arabic", must_contain="dʒ"))            # ج -> dʒ
results.append(t("قلب","Khaliji Arabic", must_contain="ɡ"))              # ق -> g
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

print("\n== 11. IPA symbol hygiene: voiced velar plosive is U+0261 everywhere ==")
for w,d in [("قال","Khaliji Arabic"),("قلب","Khaliji Arabic"),("جميل","Egyptian")]:
    results.append(t(w,d, must_contain="\u0261", must_not_contain="g"))

print("\n== 12. Written shadda on an assimilated sun letter is absorbed (no triple / duplicated prefix) ==")
results.append(t("الشَّمْسُ","Modern Standard Arabic (MSA)", must_equal="/a-ʃʃamsu/"))
results.append(t("السّرية","Egyptian", must_equal="/e-ssɾja/"))
results.append(t("اللَّيْلُ","Egyptian", must_contain="e-ll", must_not_contain="lll"))

print("\n== 13. Provenance alignment: each unit traces to its source grapheme ==")
from arabic_g2p_rules import transcribe_word_aligned, ARTICLE
al = transcribe_word_aligned("الشمس","Egyptian")
ok = al[0]==("e-",ARTICLE) and al[1:3]==[("ʃ",2),("ʃ",2)] and "".join(u for u,_ in al)=="e-ʃʃms"
results.append(ok); print(f"  [{'PASS' if ok else 'FAIL'}] الشمس aligned -> {al}")
al = transcribe_word_aligned("الظلام","Khaliji Arabic")
ok = [u for u,s in al if s==2]==["ðˤ","ðˤ"]
results.append(ok); print(f"  [{'PASS' if ok else 'FAIL'}] الظلام: ظ realized only as /ðˤ/ -> {al}")

print("\n== 14. v1.3: normalization, Alif maqṣūra, tanwīn, Tāʾ Marbūṭa, long vowels ==")
M, E, L = "Modern Standard Arabic (MSA)", "Egyptian", "Levantine Arabic"
results.append(t("على", M, must_equal="/ʕlaː/"))                        # Alif maqṣūra -> /aː/
results.append(t("الى", E, must_equal="/ʔlaː/"))                        # unhamzated preposition is not an article
results.append(t("الارض", E, must_equal="/el-ʔɾdˤ/"))                   # Alif after the article -> glottal onset
results.append(t('"الصين"،', E, must_equal="/e-sˤsˤjn/"))               # boundary punctuation stripped before the article rule
results.append(t("الـشمس", E, must_equal="/e-ʃʃms/"))                    # Tatweel removed
results.append(t("جدًا", E, must_equal="/ɡdan/"))                       # tanwīn before Alif: Alif silent
results.append(t("جداً", E, must_equal="/ɡdan/"))                       # tanwīn on Alif
results.append(t("مَدْرَسَةٌ", M, must_equal="/madrasatun/"))            # vocalized Tāʾ Marbūṭa -> /t/
results.append(t("مَدْرَسَةٌ", E, must_equal="/madɾasa/"))              # dialects: case marks on Tāʾ Marbūṭa ignored
results.append(t("طَبَقَةِ", L, must_equal="/tˤabaqa/".replace("q","ʔ")))   # Levantine, kasra ignored
results.append(t("جَمِيل", M, must_equal="/dʒamiːl/"))                  # kasra + Yāʾ -> /iː/
results.append(t("يَقُولُ", M, must_equal="/jaquːlu/"))                 # ḍamma + Wāw -> /uː/
results.append(t("يَوْم", M, must_equal="/jawm/"))                      # fatḥa + Wāw stays a glide
results.append(t("إِلَى", M, must_equal="/ʔilaː/"))                     # explicit kasra on hamza-below not doubled
results.append(t("للقمر", M, must_contain="lil-"))                      # MSA li-l- prefix
results.append(t("للشمس", M, must_equal="/li-ʃʃms/"))                    # li-l + sun letter assimilates
results.append(t("الرجل", E, must_contain="e-rr"))                      # geminate tap is a trill
results.append(t("وأكيد eventually", L, must_contain="<eng>eventually</eng>"))  # Latin runs shielded

print("\n== 15. v1.5: Gulf Ḍād, numerals, unwritten long ā ==")
G = "Khaliji Arabic"
results.append(t("أرض", G, must_equal="/ʔrðˤ/"))                       # Gulf Ḍād merges with Ẓāʾ as /ðˤ/
results.append(t("أرض", E, must_equal="/ʔɾdˤ/"))                       # other varieties keep /dˤ/
results.append(t("عمره 15 سنة", E, must_contain="<num>15</num>"))       # numerals shielded, not deleted
results.append(t("هذا", M, must_equal="/haːðaː/"))                     # unwritten long ā restored
results.append(t("ذلك", M, must_equal="/ðaːlk/"))
results.append(t("ذٰلِكَ", M, must_equal="/ðaːlika/"))                  # superscript alif in diacritized input
results.append(t("الله", E, must_equal="/allaːh/"))                    # name of God: lexical, not the article rule
results.append(t("والله", L, must_equal="/wallaːh/"))

print("\n== 16. v1.6: proclitic article, tanwīn, plural Alif, Hāʾ suffix, construct state, learned words ==")
G = "Khaliji Arabic"
results.append(t("والحلقة", E, must_equal="/wel-ħlʔa/"))                 # proclitic + moon article
results.append(t("بالساطور", E, must_equal="/be-ssaːtˤwɾ/"))             # proclitic + sun article
results.append(t("والشمس", M, must_equal="/wa-ʃʃms/"))
results.append(t("وبالتالي", L, must_equal="/wbɪ-ttaːlj/"))              # و + ب + article
results.append(t("للثورة", L, must_equal="/li-sswra/"))                  # li-l + sun, learned Thāʾ
results.append(t("والد", E, must_equal="/waːld/"))                       # not an article (father)
results.append(t("بالك", E, must_equal="/baːlk/"))                       # not an article (your mind)
results.append(t("والدي", E, must_equal="/waːldj/"))                     # NOT_ARTICLE lexicon
results.append(t("جدا", E, must_equal="/ɡdan/"))                         # unmarked tanwīn adverb
results.append(t("وطبعا", L, must_equal="/wtˤbʕan/"))
results.append(t("اشتركوا", E, must_equal="/ʔʃtɾkuː/"))                  # plural ـوا: silent Alif
results.append(t("الهوا", E, must_equal="/el-hwaː/"))                    # definite noun: no plural ending
results.append(t("عنده", E, must_equal="/ʕndu/"))                        # 3rd-person suffix, Egyptian
results.append(t("لأنه", L, must_equal="/lʔno/"))                        # 3rd-person suffix, Levantine
results.append(t("عنده", G, must_equal="/ʕndh/"))                        # Gulf keeps /h/
results.append(t("كده", E, must_equal="/kda/"))                          # demonstrative: ه spells /a/
results.append(t("شبه", E, must_equal="/ʃbh/"))                          # root /h/
results.append(t("معاه", E, must_equal="/mʕaːh/"))                       # after a long vowel: /h/
results.append(t("الكوره", E, must_equal="/el-kwɾa/"))                   # definite: ه spells Tāʾ Marbūṭa
results.append(t("كرة السلة", E, must_equal="/kɾet/ /e-ssla/"))          # construct state
results.append(t("السيارة الجديدة", E, must_equal="/e-ssjaːɾa/ /el-ɡdjda/"))  # definite noun: no construct
results.append(t("قصة، الناس", E, must_equal="/ʔsˤa/ /e-nnaːs/"))       # punctuation blocks construct
results.append(t("إذا", L, must_equal="/ʔizaː/"))                        # learned Dhāl -> /z/
results.append(t("الحادث", E, must_equal="/el-ħaːds/"))                  # learned Thāʾ -> /s/
results.append(t("ثلاثة", E, must_equal="/tlaːta/"))                     # colloquial Thāʾ stays /t/
results.append(t("إذا", G, must_equal="/ʔiðaː/"))                        # Gulf unaffected
results.append(t("الاستثمار", M, must_equal="/al-stθmaːr/"))             # waṣl Alif after the article
results.append(t("الانسان", E, must_equal="/el-ʔnsaːn/"))                # not a waṣl stem
results.append(t("مَدْرَسَةِ البَلَدِ", E, must_equal="/madɾaset/ /el-baladi/"))  # diacritized construct, dialect
results.append(t("لِلوَلَد", E, must_equal="/lel-walad/"))                # vocalized li-l
results.append(t("ولله", L, must_equal="/walillaːh/"))                   # name of God after و + li-
results.append(t("واوا", L, must_equal="/waːwaː/"))                      # not a plural ending (Alif before Wāw)
results.append(t("عِنْدَهُ", E, must_equal="/ʕindahu/"))                  # written vowels: suffix rule not applied
results.append(t("بِاسْمِ", M, must_equal="/bismi/"))                     # waṣl after a vocalized proclitic
results.append(t("بده", L, must_equal="/bdo/"))                          # not the demonstrative ده
results.append(t("والده", E, must_equal="/waːldu/"))                     # his father
results.append(t("وبالشمس", M, must_equal="/wbi-ʃʃms/"))                 # leading و is a consonant in MSA too
results.append(t("عادةً الناس", E, must_equal="/ʕaːda/ /e-nnaːs/"))     # written tanwīn: no construct
results.append(t("قصة اللي", E, must_equal="/ʔsˤa/ /e-llj/"))            # relative pronoun: no construct
results.append(t("الا", E, must_equal="/ʔlaː/"))                         # الا "except" is not an article
results.append(t("الاسماك", E, must_equal="/el-ʔsmaːk/"))                # not the waṣl noun اسم
results.append(t("باسمها", L, must_equal="/bsmhaː/"))                    # waṣl noun with a suffix
results.append(t("باتمان", E, must_equal="/baːtmaːn/"))                  # not a waṣl stem after a proclitic
results.append(t("الحمدلله", E, must_equal="/alħamdulillaːh/"))          # lexical

passed=sum(1 for r in results if r); total=len(results)
print(f"\n==== {passed}/{total} tests passed ====")
import sys; sys.exit(0 if passed==total else 1)
