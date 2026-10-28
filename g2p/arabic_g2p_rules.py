"""
Expert-revised Arabic G2P rules + diacritize-then-G2P architecture.
Grounded in: sun/moon letter assimilation (lam IS a sun letter), hamza = glottal stop,
alif = /aː/ medially & glottal onset word-initially, and the principle that short vowels
require a diacritization stage (CAMeL/Mishkal/Farasa) before G2P.
"""
import re
import warnings

# 14 sun letters (INCLUDING lam, per Sibawayh's coronal-assimilation class)
SUN_LETTERS = set("تثدذرزسشصضطظلن")
MOON_LETTERS = set("ءأإآبجحخعغفقكمهوي")

# Hamza family: glottal stop /ʔ/; inherent orthographic vowels only where the glyph fixes them
HAMZA = {"ء":"/ʔ/","أ":"/ʔ/","إ":"/ʔi/","آ":"/ʔaː/","ؤ":"/ʔ/","ئ":"/ʔ/"}

def build_rules():
    base = {
        "ء":"/ʔ/","أ":"/ʔ/","إ":"/ʔi/","آ":"/ʔaː/","ؤ":"/ʔ/","ئ":"/ʔ/",
        "ب":"/b/","ت":"/t/","ث":"/t/","ج":"/ɡ/","ح":"/ħ/","خ":"/x/","د":"/d/","ذ":"/d/",
        "ر":"/ɾ/","ز":"/z/","س":"/s/","ش":"/ʃ/","ص":"/sˤ/","ض":"/dˤ/","ط":"/tˤ/","ظ":"/zˤ/",
        "ع":"/ʕ/","غ":"/ɣ/","ف":"/f/","ق":"/ʔ/","ك":"/k/","ل":"/l/","م":"/m/","ن":"/n/",
        "ه":"/h/","و":"/w/","ي":"/j/","ة":"/a/ or /et/","ا":"/aː/",
    }
    over = {
        "Egyptian": {},  # base IS Egyptian (Cairene)
        "Levantine Arabic": {"ث":"/t/","ج":"/ʒ/","ذ":"/d/","ق":"/ʔ/","ر":"/r/","ة":"/a/ or /e/"},
        "Khaliji Arabic":  {"ث":"/θ/","ج":"/dʒ/","ذ":"/ð/","ظ":"/ðˤ/","ق":"/ɡ/","ر":"/r/","ة":"/a/ or /at/"},
        "Modern Standard Arabic (MSA)": {"ث":"/θ/","ج":"/dʒ/","ذ":"/ð/","ظ":"/ðˤ/","ق":"/q/","ر":"/r/","ة":"/a/ or /at/"},
    }
    art = {  # (moon prefix, sun prefix) — narrow transcription from the xlsx
        "Egyptian": ("/el-/","/e-/"),
        "Levantine Arabic": ("/ɪl-/","/ɪ-/"),
        "Khaliji Arabic": ("/ɪl-/","/ɪ-/"),
        "Modern Standard Arabic (MSA)": ("/al-/","/a-/"),
    }
    lil = {"Egyptian":"/lel-/","Levantine Arabic":"/lil-/","Khaliji Arabic":"/lil-/","Modern Standard Arabic (MSA)":"/lil-/"}
    short = {"َ":"/a/","ُ":"/u/","ِ":"/i/"}
    tanwin = {"ً":"/an/","ٌ":"/un/","ٍ":"/in/"}
    other = {"ْ":"","ّ":"doubled"}
    R={"dialects":{}}
    for d in over:
        letters={g:{"phoneme":p} for g,p in base.items()}
        for g,p in over[d].items(): letters[g]={"phoneme":p}
        R["dialects"][d]={
            "letters":letters,
            "vowels":{"short":short,"long":{"ا":"/aː/","و":"/uː/","ي":"/iː/"}},
            "diacritics":{**tanwin,**other},
            "phonological_rules":{
                "al_prefix_moon":{"letters":"".join(MOON_LETTERS),"ipa":art[d][0]},
                "al_prefix_sun":{"letters":"".join(SUN_LETTERS),"ipa":art[d][1]},
            },
            "lil_prefix":lil[d],
        }
    return R

IPA_RULES = build_rules()

# ---------- diacritize-then-G2P ----------
_DIACRITIZER = None

def _load_diacritizer():
    """Load the diacritizer once: CAMeL Tools MLE disambiguator, else Mishkal, else none."""
    global _DIACRITIZER
    if _DIACRITIZER is not None:
        return _DIACRITIZER
    try:
        from camel_tools.disambig.mle import MLEDisambiguator
        mle = MLEDisambiguator.pretrained()
        def camel(text):
            out = []
            for d in mle.disambiguate(text.split()):
                diac = d.analyses[0].analysis.get('diac') if d.analyses else None
                out.append(diac or d.word)
            return " ".join(out)
        _DIACRITIZER = ("camel", camel)
    except Exception:
        try:
            from mishkal.tashkeel import TashkeelClass
            _DIACRITIZER = ("mishkal", TashkeelClass().tashkeel)
        except Exception:
            _DIACRITIZER = ("none", None)
    return _DIACRITIZER

def DIACRITIZE_HOOK(text, enable=False):
    """Recover short vowels BEFORE G2P. Off by default so the pipeline runs without heavy deps."""
    if not enable:
        return text
    name, fn = _load_diacritizer()
    if fn is None:
        warnings.warn("No diacritizer available (install camel-tools or mishkal); "
                      "returning undiacritized text.", RuntimeWarning, stacklevel=2)
        return text
    return fn(text)

def get_rules(dialect):
    if not isinstance(dialect,str): return IPA_RULES["dialects"]["Modern Standard Arabic (MSA)"]
    if "Egyptian" in dialect: return IPA_RULES["dialects"]["Egyptian"]
    if "Levantine" in dialect: return IPA_RULES["dialects"]["Levantine Arabic"]
    if "Khaliji" in dialect or "Gulf" in dialect: return IPA_RULES["dialects"]["Khaliji Arabic"]
    return IPA_RULES["dialects"]["Modern Standard Arabic (MSA)"]

# A transcription is built as a list of aligned units: (ipa_unit, source_index).
# source_index is the position of the originating grapheme in the word, or
# ARTICLE (-1) for definite-article / lil- prefix material. Keeping provenance
# lets the evaluator check each grapheme occurrence against its own realization
# instead of searching the joined string (which allows false positives such as
# /ð/ matching inside /ðˤ/).
ARTICLE = -1

TATWEEL, SHADDA = "\u0640", "\u0651"
ALIF, ALIF_MAQSURA, TAA_MARBUTA, HAMZA_BELOW, LAM = "\u0627", "\u0649", "\u0629", "\u0625", "\u0644"
VOWEL_MARKS = {"\u064E": "a", "\u064F": "u", "\u0650": "i"}
TANWIN_MARKS = {"\u064B": "an", "\u064C": "un", "\u064D": "in"}
_ARABIC_LETTER = re.compile(r"[\u0621-\u063A\u0641-\u064A]")
_DIACRITIC = re.compile(r"[\u064B-\u0652]")
_LATIN = re.compile(r"([A-Za-z]+(?:['\u2019-][A-Za-z]+)*)")

# ---------- Stage 1: normalization and lexical shield ----------
def normalize_token(tok):
    """Remove Tatweel and strip non-letter characters (punctuation, digits, symbols)
    from both ends of an Arabic token; diacritics on the last letter are kept."""
    tok = tok.replace(TATWEEL, "")
    a, b = 0, len(tok)
    while a < b and not _ARABIC_LETTER.match(tok[a]):
        a += 1
    while b > a and not (_ARABIC_LETTER.match(tok[b - 1]) or _DIACRITIC.match(tok[b - 1])):
        b -= 1
    return tok[a:b]

def segment(text):
    """Yield ("en", span) for shielded Latin-script material and ("ar", token) for
    normalized Arabic tokens. Explicit <eng>...</eng> tags are honoured, and Latin-script
    runs inside untagged text are shielded automatically."""
    for chunk in re.split(r'(<eng>.*?</eng>)', str(text)):
        if chunk.startswith("<eng>") and chunk.endswith("</eng>"):
            yield ("en", chunk[5:-6])
            continue
        for tok in chunk.split():
            for part in _LATIN.split(tok):
                if not part:
                    continue
                if _LATIN.fullmatch(part):
                    yield ("en", part)
                else:
                    p = normalize_token(part)
                    if p:
                        yield ("ar", p)

def arabic_words(text):
    """The normalized Arabic tokens of text (shielded spans excluded)."""
    for kind, tok in segment(text):
        if kind == "ar":
            yield tok

# ---------- Stage 3: rule-based mapping ----------
def _consume_diacritics(word, j, n, diacritics, units, absorb_shadda=False):
    """Consume a run of diacritics from index j. Shadda doubles the last unit;
    a vowel diacritic is appended. Order-independent (handles consonant+shadda+vowel).
    absorb_shadda: the consonant is already geminated (sun-letter assimilation), so a
    written shadda is orthographic redundancy and must not add a third copy.
    A geminated tap /ɾ/ is realized as the trill /rr/."""
    shadda=False; vowel=None; vpos=None
    while j<n and word[j] in diacritics:
        if word[j]==SHADDA:
            shadda=True
        else:
            v=diacritics[word[j]]
            if v not in ("","doubled"): vowel=v.strip('/'); vpos=j
        j+=1
    if shadda and units and not absorb_shadda:
        u, src = units[-1]
        if u == "ɾ":
            units[-1] = ("r", src); units.append(("r", src))
        else:
            units.append(units[-1])
    if vowel: units.append((vowel, vpos))
    return j

def is_article(word):
    """Word-initial definite article: ال followed by an Arabic letter other than Alif maqṣūra
    (so that the unhamzated preposition الى is not read as an article)."""
    return (len(word) >= 3 and word[0] == ALIF and word[1] == LAM
            and word[2] != ALIF_MAQSURA and bool(_ARABIC_LETTER.match(word[2])))

def transcribe_aligned(word, letters, diacritics, sun_letters, rules):
    """Return the word's realization as a list of (ipa_unit, source_index)."""
    units=[]; i=0; n=len(word)
    if word == ALIF + LAM:                                     # bare article attached to a shielded word (الـAI)
        return [(rules["phonological_rules"]["al_prefix_moon"]["ipa"].strip('/'), ARTICLE)]
    # word-initial للـ
    if n>=2 and word[0]==LAM and word[1]==LAM:
        units.append((rules.get("lil_prefix","/lil-/").strip('/'), ARTICLE)); i=2
    # word-initial definite article الـ
    elif is_article(word):
        if word[2] in sun_letters:
            pre=rules["phonological_rules"]["al_prefix_sun"]["ipa"].strip('/')
            sp=letters.get(word[2],{}).get("phoneme","").split(" or ")[0].strip('/')
            if sp == "ɾ": sp = "r"                              # geminate tap -> trill
            units.append((pre, ARTICLE))
            if sp: units.extend([(sp, 2), (sp, 2)])            # assimilated + geminated
            i=_consume_diacritics(word,3,n,diacritics,units,absorb_shadda=True)
        else:
            units.append((rules["phonological_rules"]["al_prefix_moon"]["ipa"].strip('/'), ARTICLE)); i=2
    while i<n:
        ch=word[i]
        nxt=word[i+1] if i+1<n else ""
        # bare Alif / Alif maqṣūra
        if ch==ALIF or ch==ALIF_MAQSURA:
            if ch==ALIF and (i==0 or (units and units[-1][1]==ARTICLE)):
                units.append(("ʔ", i))                          # glottal onset (also after the article)
            elif units and units[-1][0]=="an":
                pass                                           # ًا : Alif is the silent seat of tanwīn
            elif nxt in TANWIN_MARKS:                          # اً : tanwīn written on the Alif
                if units and units[-1][0]=="a": units.pop()
                units.append((TANWIN_MARKS[nxt], i)); i+=1
            elif units and units[-1][0]=="a":
                units[-1]=("aː", i)                            # fatḥa + Alif -> one long vowel
            else:
                units.append(("aː", i))
            i=_consume_diacritics(word,i+1,n,diacritics,units); continue
        # Tāʾ Marbūṭa: pausal /a/; /t/ surfaces when a vowel or tanwīn is written on it
        if ch == TAA_MARBUTA:
            if not (units and units[-1][0] == "a"):
                units.append(("a", i))
            if nxt in VOWEL_MARKS or nxt in TANWIN_MARKS:
                units.append(("t", i))
                i=_consume_diacritics(word,i+1,n,diacritics,units); continue
            i += 1; continue
        # regular letter
        if ch in letters:
            ph=letters[ch]["phoneme"]
            if " or " in ph: ph=ph.split(" or ")[0]
            ph=ph.strip('/')
            # long vowels: Wāw after ḍamma / Yāʾ after kasra, with no vowel or shadda of their own
            if (ch in "وي" and units and units[-1][0]==("u" if ch=="و" else "i")
                    and nxt not in VOWEL_MARKS and nxt not in TANWIN_MARKS and nxt!=SHADDA):
                units[-1]=(units[-1][0]+"ː", i)
                i=_consume_diacritics(word,i+1,n,diacritics,units); continue
            if ch==HAMZA_BELOW and nxt=="\u0650":
                ph="ʔ"                                         # explicit kasra supplies the /i/
            if ph: units.append((ph, i))
            i=_consume_diacritics(word,i+1,n,diacritics,units); continue
        i+=1                                                   # unmapped character: discarded
    return units

def transcribe_arabic(word, letters, diacritics, sun_letters, rules):
    joined="".join(u for u,_ in transcribe_aligned(word, letters, diacritics, sun_letters, rules))
    return f"/{joined}/" if joined else ""

def _context(dialect):
    rules=get_rules(dialect); letters=rules["letters"]
    diacritics={**rules["vowels"]["short"],**rules["diacritics"]}
    spec=rules["phonological_rules"]["al_prefix_sun"].get("letters")
    sun=set(spec.replace(",","").replace(" ","")) if spec else SUN_LETTERS
    return rules, letters, diacritics, sun

def transcribe_word_aligned(word, dialect):
    """Public helper for evaluation: aligned units for one normalized token under a dialect."""
    rules, letters, diacritics, sun = _context(dialect)
    return transcribe_aligned(word, letters, diacritics, sun, rules)

def transcribe_protected(text, dialect, diacritize=False):
    if text is None or text=="": return ""
    text = DIACRITIZE_HOOK(str(text), enable=diacritize)
    rules, letters, diacritics, sun = _context(dialect)
    out=[]
    for kind, tok in segment(text):
        if kind == "en":
            out.append(f"<eng>{tok}</eng>")
        else:
            p=transcribe_arabic(tok,letters,diacritics,sun,rules)
            if p: out.append(p)
    return " ".join(out)
