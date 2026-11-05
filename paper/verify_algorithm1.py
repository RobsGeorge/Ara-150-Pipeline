"""Algorithm 1 of the paper transcribed line by line, independently of the engine's code,
and compared with the engine on every input.
Usage: python -I verify_algorithm1.py <Ara-150-Pipeline/g2p> <test_split.csv>"""
import sys, csv, re, unicodedata
sys.path.insert(0, sys.argv[1])
from arabic_g2p_rules import (transcribe_protected, get_rules, LONG_A, ALLAH,   # engine: comparison + rule/lexicon tables only
                              LEARNED, NOT_ARTICLE, TANWIN_ADV, H_ROOT, H_VOWEL, LAN, SILENT_WAW,
                              NOT_WASL, NOT_PLURAL, NOT_LEARNED)

ALIF, MAQSURA, TAA, HAMZA_BELOW, SHADDA, LAM = "ا", "ى", "ة", "إ", "ّ", "ل"
SHORT = {"َ": "a", "ِ": "i", "ُ": "u", "\u0670": "aː"}       # \u0670 superscript Alif
TANWIN = {"ً": "an", "ٍ": "in", "ٌ": "un"}
DIAC = set(SHORT) | set(TANWIN) | {SHADDA, "ْ"}
SUN = set("تثدذرزسشصضطظلن")
LETTER = re.compile(r"[ء-غف-يپچڤڨگ]")              # Arabic letters and the loan letters
LATIN = re.compile(r"([A-Za-z]+(?:['’-][A-Za-z]+)*)")
NUM = re.compile(r"([0-9\u0660-\u0669\u06F0-\u06F9]+(?:[.,\u066B\u066C][0-9\u0660-\u0669\u06F0-\u06F9]+)*)")

def normalize(text):                                    # Stage 1 (Section 5); "pb" marks punctuation
    for chunk in re.split(r"(<eng>.*?</eng>)", text):
        if chunk.startswith("<eng>") and chunk.endswith("</eng>"):
            yield "en", chunk[5:-6]; continue
        for tok in chunk.split():
            for part in LATIN.split(tok):
                if not part: continue
                if LATIN.fullmatch(part): yield "en", part; continue
                for sub in NUM.split(part):                 # numerals are shielded
                    if not sub: continue
                    if NUM.fullmatch(sub): yield "num", sub; continue
                    raw = sub.replace("ـ", "")
                    sub = "".join(c for c in raw if not unicodedata.category(c).startswith("P"))   # inner punctuation
                    a, b = 0, len(sub)
                    while a < b and not LETTER.match(sub[a]): a += 1
                    while b > a and not (LETTER.match(sub[b-1]) or sub[b-1] in DIAC): b -= 1
                    if b > a:
                        if not LETTER.match(raw[0]): yield "pb", ""
                        yield False, sub[a:b]
                        if not (LETTER.match(raw[-1]) or raw[-1] in DIAC): yield "pb", ""
                    else: yield "pb", ""

def lookup(g, R, learned):                              # function LOOKUP
    if learned and g == "ث": return "s"
    if learned and g == "ذ": return "z"
    return R["letters"][g]["phoneme"].split(" or ")[0].strip("/")

def letters_of(w): return [c for c in w if c not in DIAC]
def bare_of(w): return "".join(letters_of(w))
def article_word(w):
    L = letters_of(w)
    return len(L) >= 3 and L[0] == ALIF and L[1] == LAM and L[2] != MAQSURA and bool(LETTER.match(L[2])) and L != [ALIF, LAM, ALIF]

PRE = [x + y + z for x in ("", "و", "ف") for y in ("", "ب", "ك", "ل") for z in ("", "ال")] + [x + "لل" for x in ("", "و", "ف")]
SUF = ["ه", "ها", "هم", "هن", "ك", "كم", "نا", "ي", "ة", "ات", "ين", "ون", "ا", "ية", "يات"]
def stem_set(b, with_suffix):                           # "stems" of a bare word (Section 4)
    out = set()
    for p in PRE:
        if b.startswith(p) and len(b) - len(p) >= 2:
            r = b[len(p):]; out.add(r)
            if with_suffix:
                for x in SUF:
                    if r.endswith(x) and len(r) - len(x) >= 2: out.add(r[:-len(x)])
    return out

RELPRON = {"اللي", "الذي", "التي", "الذين", "اللذان", "اللتان", "اللذين", "اللتين", "اللاتي", "اللواتي", "اللائي"}
PV = {"Egyptian": "e", "Levantine Arabic": "ɪ", "Khaliji Arabic": "ɪ"}
MSA_PV = {"و": "wa", "ف": "fa", "ب": "bi", "ك": "ka"}
CONSTRUCT = {"Egyptian": "et", "Levantine Arabic": "ɪt", "Khaliji Arabic": "at", "Modern Standard Arabic (MSA)": "at"}
SUFFIX = {"Egyptian": "u", "Levantine Arabic": "o"}
MSA = "Modern Standard Arabic (MSA)"

def article(w, D, R, learned):                          # function ARTICLE -> (lambda, M, Z, s)
    pos = [k for k, c in enumerate(w) if c not in DIAC]; L = [w[k] for k in pos]
    moon = R["phonological_rules"]["al_prefix_moon"]["ipa"].strip("/"); sun = R["phonological_rules"]["al_prefix_sun"]["ipa"].strip("/")
    if article_word(w): return [], moon, sun, pos[2]
    b0 = bare_of(w)
    if b0 in NOT_ARTICLE or (b0.startswith("والد") and b0[4:] in WALID): return [], None, None, -1
    for ell in ("", "و", "ف"):
        m = len(ell)
        if "".join(L[:m]) != ell: continue
        lam = list(ell)                                 # leading conjunction letters, realized by the caller
        if L[m:m+2] == [LAM, LAM] and len(L) >= m + 3 and LETTER.match(L[m+2]):
            lil = R["lil_prefix"].strip("/"); return lam, lil, lil[:-2] + "-", pos[m+2]
        if (len(L) >= m + 5 and L[m] in "وفبك" and (m == 0 or L[m] in "بك") and L[m+1] == ALIF and L[m+2] == LAM
                and L[m+3] != MAQSURA and LETTER.match(L[m+3])):
            v = MSA_PV[L[m]] if D == MSA else L[m].replace("و", "w").replace("ف", "f").replace("ب", "b").replace("ك", "k") + PV[D]
            return lam, v + "l-", v + "-", pos[m+3]
    return [], None, None, -1

def diacritics(w, i, U, absorb):                        # function DIACRITICS (0-based i)
    shadda, vowel = False, None
    while i < len(w) and w[i] in DIAC:
        if w[i] == SHADDA: shadda = True
        elif w[i] in SHORT or w[i] in TANWIN: vowel = SHORT.get(w[i]) or TANWIN[w[i]]
        i += 1
    if shadda and not absorb and U:
        if U[-1][0] == "ɾ": U[-1] = ("r", 0); U.append(("r", 0))
        else: U.append(U[-1])
    if vowel: U.append((vowel, 0))
    return i

WALID = {"", "ي", "ه", "ك", "ها", "هم", "كم", "نا", "ة", "تي", "ته", "تها", "تك", "تهم", "تكم", "تنا", "يه", "يها", "يهم", "يك", "اه", "ان", "اي"}
def wasl(rest):                                         # function WASL
    b = bare_of(rest)
    if not b or b[0] != ALIF: return False
    nouns = ("اسم", "ابن", "ابنة", "ابنت", "اثنين", "اثنان", "اتنين", "امرأة", "امراة")
    if any(b == x or (b.startswith(x) and b[len(x):] in ("ه", "ها", "هم", "ي", "ك", "نا", "كم")) for x in nouns): return True
    if b.startswith(("اسمع", "اسمح")): return True
    if b.startswith(("استرال", "اسطوان")): return False
    return ((len(b) >= 6 and ((b[4] == ALIF and (b[1] == "ن" or b[2] in "تطد")) or (b.startswith("است") and b[5:6] == ALIF)))
            or (len(b) >= 5 and b[1] == "ت" and b[3] == ALIF))

def h_vowel(bare, D):                                   # final-/a/ lexicon, alone or after (و|ف)(ب|ل)
    for p in (x + y for x in ("", "و", "ف") for y in ("", "ب", "ل")):
        if bare.startswith(p) and bare[len(p):] in H_VOWEL:
            return not (bare[len(p):] == "ده" and p and D != "Egyptian")
    return False

def algorithm1(text, D):
    R = get_rules(D); P = []; S = list(normalize(text))
    for t, (shielded, w) in enumerate(S):
        if shielded == "pb": continue
        if shielded:
            tag = "eng" if shielded == "en" else "num"; P.append(f"<{tag}>{w}</{tag}>"); continue
        bare = bare_of(w)
        if bare in ALLAH: P.append("/" + ALLAH[bare] + "/"); continue   # name of God: lexical form
        U, n = [], len(w)                               # units carry a flag: 1 = article prefix
        learned = D in ("Egyptian", "Levantine Arabic") and not (stem_set(bare, False) & NOT_LEARNED) and bool(stem_set(bare, True) & LEARNED)
        lam, M, Z, s = article(w, D, R, learned)
        cons = (bare.endswith(TAA) and not any(m in w for m in TANWIN) and s < 0 and bare != "برة" and t + 1 < len(S)
                and S[t+1][0] is False and article_word(S[t+1][1]) and bare_of(S[t+1][1]) not in RELPRON)
        i = 0
        if s >= 0:
            k = 0
            for c in lam:                                # leading Wāw/Fāʾ with any marks written on it
                while w[k] != c: k += 1
                U.append((lookup(c, R, learned), 0)); k = diacritics(w, k + 1, U, False)
            if w[s] in SUN:
                c = lookup(w[s], R, learned); c = "r" if c == "ɾ" else c
                U += [(Z, 1), (c, 0), (c, 0)]; i = diacritics(w, s + 1, U, True)
            else:
                U.append((M, 1)); i = s
        elif w == ALIF + LAM:
            U.append((R["phonological_rules"]["al_prefix_moon"]["ipa"].strip("/"), 1)); i = n
        while i < n:
            g = w[i]; i += 1; nxt = w[i] if i < n else ""; last = not bare_of(w[i:]); second = len(bare_of(w[:i])) == 2
            if g in (ALIF, MAQSURA):
                follows_art = bool(U) and U[-1][1] == 1
                if g == ALIF and bare not in NOT_WASL and (follows_art or (second and w[0] in "وفبكل")) and wasl(w[i-1:]): pass
                elif g == ALIF and (i == 1 or follows_art or (second and bare in LAN)): U.append(("ʔ", 0))
                elif U and U[-1][0] == "an": pass
                elif nxt in TANWIN:
                    if U and U[-1][0] == "a": U.pop()
                    U.append((TANWIN[nxt], 0)); i += 1
                elif g == ALIF and last and (bare in TANWIN_ADV or (bare[0] in "وف" and bare[1:] in TANWIN_ADV)):
                    if U and U[-1][0] == "a": U.pop()
                    U.append(("an", 0))
                elif (g == ALIF and last and len(bare) >= 4 and bare[-2] == "و" and bare[-3] != ALIF and s < 0
                      and not (bare[0] in "وفبل" and bare[1:] in NOT_PLURAL)):
                    if U and U[-1][0] == "w": U[-1] = ("uː", 0)
                elif U and U[-1][0] == "a": U[-1] = ("aː", 0)
                else: U.append(("aː", 0))
                i = diacritics(w, i, U, False)
            elif g == TAA:
                long_ = bool(U) and U[-1][0] == "aː"
                if not (U and U[-1][0] in ("a", "aː")): U.append(("a", 0))
                if (nxt in SHORT or nxt in TANWIN) and D == MSA:
                    U.append(("t", 0)); i = diacritics(w, i, U, False)
                else:
                    while i < n and w[i] in DIAC: i += 1
                    if cons:
                        if not long_: U[-1] = (CONSTRUCT[D][:-1], 0)
                        U.append(("t", 0))
            elif g in "وي" and U and U[-1][0] == ("u" if g == "و" else "i") and nxt not in SHORT and nxt not in TANWIN and nxt != SHADDA:
                U[-1] = (U[-1][0] + "ː", 0); i = diacritics(w, i, U, False)
            elif g == "ه" and last and i == n and D != MSA and h_vowel(bare, D):
                U.append(("a", 0)); break
            elif (g == "ه" and last and i == n and D in SUFFIX and len(bare) >= 2 and bare[-2] not in "اويى"
                  and not (stem_set(bare, False) & H_ROOT)):
                if U and U[-1][0] in ("a", "i", "u"): U.pop()
                U.append(("a" if s >= 0 else SUFFIX[D], 0)); break
            elif g == "و" and last and bare in SILENT_WAW:
                break
            elif g in R["letters"]:
                p = lookup(g, R, learned)
                if g == HAMZA_BELOW and nxt == "ِ": p = "ʔ"
                k = i - 1
                U.append((p, 0)); i = diacritics(w, i, U, False)
                if k in LONG_A.get(w, ()): U.append(("aː", 0))           # unwritten long ā
        if U: P.append("/" + "".join(u for u, _ in U) + "/")
    return " ".join(P)

N = {"Egyptian": "Egyptian", "Levantine": "Levantine Arabic", "Khaliji": "Khaliji Arabic", "MSA": "Modern Standard Arabic (MSA)"}
rows = [(r["Transcript"], N[r["Main Dialect"]]) for r in csv.DictReader(open(sys.argv[2], encoding="utf-8")) if r["Transcript"]]
extra = ["الشَّمْسُ", "السّرية", "مُدَرِّس", "مَدْرَسَةٌ", "شَجَرَة", "كَتَبَ", "اللَّيْلُ", "للشمس", "سكّر", "كتابٌ", "آمن",
         "إِلَى", "على", "هذا", "ذلك", "لكن", "الله", "والله", "لله", "هٰذا", "ذٰلِكَ", "اللّٰه", "أرض", "عمره 15 سنة", "سنة ٢٠٢٤", "الرحمن", "طَبَقَةٌ", "عَامَّةِ", "مَدْرَسَةٍ", "الى", "الارض", '"الصين"،', "جدًا", "جداً", "جَمِيل", "يَقُولُ", "يَوْم", "قُوَّة", "الـAI", "الرجل", "الـشمس",
         "والحلقة", "بالساطور", "وبالتالي", "للثورة", "والد", "بالك", "والدي", "جدا", "وطبعا", "اشتركوا", "الهوا", "عنده", "لأنه",
         "كده", "وده", "شبه", "معاه", "الكوره", "كرة السلة", "السيارة الجديدة", "قصة، الناس", "إذا", "الحادث", "ثلاثة",
         "الاستثمار", "الانسان", "باستخدام", "واسمها", "الاتجاهات", "لانه", "عمرو", "مَدْرَسَةِ البَلَدِ", "لِلوَلَد",
         "وَالشَّمْسُ", "بِالكِتابِ", "كُرَةِ السَلَّةِ", "رحمة الله", "ولله", "واوا",
         "عِنْدَهُ", "بِاسْمِ", "بده", "والده", "وبالشمس", "عادةً الناس", "قصة اللي", "الا", "حاجة الا", "الاسماك", "باسمها",
         "باتمان", "الحمدلله", "برة البيت", "الاستراليين", "باتجاه", "صلاة", "حياة الناس", "صَلَاةٌ", "الحياة",
         "قالّه", "عِنْدُه", "باتجاه", "كاتدرائية", "وابنتك", "واسمعني", "بكده", "وده", "ذكرياتك", "وَبِالشَّمْسِ", "والدها",
         "الڤيديو", 'ال"يوتيوب', "ال(بوستات", "وسوا", "بدوا", "الاسطوانة", "قصة، الناس"]
rows += [(e, d) for e in extra for d in N.values()]
mism = [(t, d, algorithm1(t, d), transcribe_protected(t, d)) for t, d in rows if algorithm1(t, d) != transcribe_protected(t, d)]
print(f"{len(rows)} inputs compared; {len(mism)} mismatches")
for m in mism[:8]: print(m)
