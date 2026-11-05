"""
Expert-revised Arabic G2P rules + diacritize-then-G2P architecture.
Grounded in: sun/moon letter assimilation (lam IS a sun letter), hamza = glottal stop,
alif = /aː/ medially & glottal onset word-initially, and the principle that short vowels
require a diacritization stage (CAMeL/Mishkal/Farasa) before G2P.
"""
import re
import unicodedata
import warnings

# 14 sun letters (INCLUDING lam, per Sibawayh's coronal-assimilation class)
SUN_LETTERS = set("تثدذرزسشصضطظلن")
MOON_LETTERS = set("ءأإآبجحخعغفقكمهوي") | set("\u06A4\u0686\u06AF\u067E\u06A8")   # + loan letters ڤ چ گ پ ڨ

# Hamza family: glottal stop /ʔ/; inherent orthographic vowels only where the glyph fixes them
HAMZA = {"ء":"/ʔ/","أ":"/ʔ/","إ":"/ʔi/","آ":"/ʔaː/","ؤ":"/ʔ/","ئ":"/ʔ/"}

def build_rules():
    base = {
        "ء":"/ʔ/","أ":"/ʔ/","إ":"/ʔi/","آ":"/ʔaː/","ؤ":"/ʔ/","ئ":"/ʔ/",
        "ب":"/b/","ت":"/t/","ث":"/t/","ج":"/ɡ/","ح":"/ħ/","خ":"/x/","د":"/d/","ذ":"/d/",
        "ر":"/ɾ/","ز":"/z/","س":"/s/","ش":"/ʃ/","ص":"/sˤ/","ض":"/dˤ/","ط":"/tˤ/","ظ":"/zˤ/",
        "ع":"/ʕ/","غ":"/ɣ/","ف":"/f/","ق":"/ʔ/","ك":"/k/","ل":"/l/","م":"/m/","ن":"/n/",
        "ه":"/h/","و":"/w/","ي":"/j/","ة":"/a/ or /et/","ا":"/aː/",
        # letters used for loanwords: ڤ /v/, چ /tʃ/, گ /ɡ/, پ /p/; ڨ is /ɡ/ (Maghrebi spelling) except
        # in Egyptian and Levantine, where it is written for ڤ (الڨيديو, ڨيتامين): /v/
        "\u06A4":"/v/","\u0686":"/tʃ/","\u06AF":"/ɡ/","\u06A8":"/v/","\u067E":"/p/",
    }
    over = {
        "Egyptian": {},  # base IS Egyptian (Cairene)
        "Levantine Arabic": {"ث":"/t/","ج":"/ʒ/","ذ":"/d/","ق":"/ʔ/","ر":"/r/","ة":"/a/ or /e/"},
        "Khaliji Arabic":  {"ث":"/θ/","ج":"/dʒ/","ذ":"/ð/","ظ":"/ðˤ/","ض":"/ðˤ/","ق":"/ɡ/","ر":"/r/","ة":"/a/ or /at/",
                            "ڨ":"/ɡ/"},
        "Modern Standard Arabic (MSA)": {"ث":"/θ/","ج":"/dʒ/","ذ":"/ð/","ظ":"/ðˤ/","ق":"/q/","ر":"/r/","ة":"/a/ or /at/",
                                         "ڨ":"/ɡ/"},
    }
    art = {  # (moon prefix, sun prefix) — narrow transcription from the xlsx
        "Egyptian": ("/el-/","/e-/"),
        "Levantine Arabic": ("/ɪl-/","/ɪ-/"),
        "Khaliji Arabic": ("/ɪl-/","/ɪ-/"),
        "Modern Standard Arabic (MSA)": ("/al-/","/a-/"),
    }
    lil = {"Egyptian":"/lel-/","Levantine Arabic":"/lɪl-/","Khaliji Arabic":"/lɪl-/","Modern Standard Arabic (MSA)":"/lil-/"}
    # v1.6. Vowel of each proclitic before the article (Wāw, Fāʾ, Bāʾ, Kāf): the article's
    # hamzat al-waṣl is elided and the proclitic carries the vowel (/wel-/, /bil-/, /wal-/).
    proc = {
        "Egyptian": {"و":"we","ف":"fe","ب":"be","ك":"ke"},
        "Levantine Arabic": {"و":"wɪ","ف":"fɪ","ب":"bɪ","ك":"kɪ"},
        "Khaliji Arabic": {"و":"wɪ","ف":"fɪ","ب":"bɪ","ك":"kɪ"},
        "Modern Standard Arabic (MSA)": {"و":"wa","ف":"fa","ب":"bi","ك":"ka"},
    }
    # construct state (iḍāfa): Tāʾ Marbūṭa before a definite noun
    construct = {"Egyptian":"et","Levantine Arabic":"ɪt","Khaliji Arabic":"at","Modern Standard Arabic (MSA)":"at"}
    # 3rd-person masculine suffix -ه after a consonant (None: written /h/ is kept)
    pron = {"Egyptian":"u","Levantine Arabic":"o","Khaliji Arabic":None,"Modern Standard Arabic (MSA)":None}
    learned = {"Egyptian":{"ث":"s","ذ":"z"},"Levantine Arabic":{"ث":"s","ذ":"z"},
               "Khaliji Arabic":{},"Modern Standard Arabic (MSA)":{}}
    short = {"َ":"/a/","ُ":"/u/","ِ":"/i/","\u0670":"/aː/"}   # U+0670 superscript (dagger) alif
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
            "proclitic_vowel":proc[d],
            "construct_ta":construct[d],
            "pronoun_suffix":pron[d],
            "learned":learned[d],
            # Tāʾ Marbūṭa surfaces as /t/ before a written case vowel or tanwīn only in MSA;
            # the dialects are pausal, so case marks on it are ignored.
            "taa_marbuta_t": d == "Modern Standard Arabic (MSA)",
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
_ARABIC_LETTER = re.compile(r"[\u0621-\u063A\u0641-\u064A\u067E\u0686\u06A4\u06A8\u06AF]")
def _strip_inner(tok):
    """Remove Tatweel and punctuation inside a token (ال"يوتيوب, ال(بوستات)."""
    return "".join(ch for ch in tok.replace(TATWEEL, "") if not unicodedata.category(ch).startswith("P"))
_DIACRITIC = re.compile(r"[\u064B-\u0652\u0670]")
_LATIN = re.compile(r"([A-Za-z]+(?:['\u2019-][A-Za-z]+)*)")
_NUMBER = re.compile(r"([0-9\u0660-\u0669\u06F0-\u06F9]+(?:[.,\u066B\u066C][0-9\u0660-\u0669\u06F0-\u06F9]+)*)")

# Lexical exceptions (bare, undiacritized forms).
# LONG_A: frequent words whose long /aː/ is not written (superscript alif); value = letter
# indices after which /aː/ is inserted. ALLAH: the name of God and its proclitic forms,
# pronounced with a geminate Lām and long /aː/ in every variety, not by the article rule.
LONG_A = {"هذا": {0}, "هذه": {0}, "ذلك": {0}, "لكن": {0}, "لكنه": {0}, "لكنها": {0},
          "هؤلاء": {0}, "هكذا": {0}, "الرحمن": {4}, "إله": {1}}
ALLAH = {"الله": "allaːh", "والله": "wallaːh", "بالله": "billaːh", "لله": "lillaːh",
         "فالله": "fallaːh", "تالله": "tallaːh", "ولله": "walillaːh", "فلله": "falillaːh",
         "الحمدلله": "alħamdulillaːh", "والحمدلله": "walħamdulillaːh"}
LEXICAL = ARTICLE - 1   # source index for units that come from a lexical exception

# v1.6 lexicons (bare forms; matched on the word or on its stem, see stems()).
# Words in which proclitic + ال is not an article (والد "father", بالها "her mind", ...).
# Every lexicon entry below is attested in the training split of the corpus.
# والد "father" / والدة "mother" with a pronominal suffix is never an article word.
_WALID_SUFFIXES = {"", "ي", "ه", "ك", "ها", "هم", "كم", "نا", "ة", "تي", "ته", "تها", "تك", "تهم", "تكم", "تنا",
                   "يه", "يها", "يهم", "يك", "اه", "ان", "اي"}
NOT_ARTICLE = {"والدي", "والده", "والدة", "والدك", "والدهم", "والدتي", "والدته", "والدتها", "والدتك",
               "والديه", "بالها", "بالهم", "بالكم", "بالنا", "بالغة", "بالغين", "بالغا", "بالغت", "بالون",
               "كاليفورنيا", "كالوري", "كالوريز", "واللا", "والتر"}
PROCLITICS = "وفبك"
# Adverbs written with the Alif of tanwīn but without its mark: final Alif -> /an/.
TANWIN_ADV = {
    "جدا", "طبعا", "مثلا", "فعلا", "تقريبا", "أصلا", "اصلا", "تماما", "دائما", "دايما", "أبدا", "ابدا",
    "أيضا", "ايضا", "أخيرا", "اخيرا", "خصوصا", "أهلا", "اهلا", "أحيانا", "احيانا", "أولا", "اولا",
    "ثانيا", "ثالثا", "شيئا", "كثيرا", "قليلا", "حرفيا", "شكرا", "تحديدا", "غالبا", "قائلا", "عموما",
    "بعيدا", "سنويا", "يوميا", "حاليا", "فعليا", "شخصيا", "حقا", "أساسا", "اساسا", "قريبا", "حتما",
    "حسنا", "نهائيا", "رسميا", "تلقائيا", "نسبيا", "جميعا", "معا", "سابقا", "لاحقا", "فورا", "مؤخرا",
    "حديثا", "مجانا", "صباحا", "ليلا", "نهارا", "سريعا", "إطلاقا", "اطلاقا", "عفوا",
    # v1.7
    "طبيا", "قولا", "عملا", "شكلا", "موضوعا", "علميا", "عمليا", "ماديا", "نفسيا", "تاريخيا", "سياسيا",
    "اقتصاديا", "اجتماعيا", "دوليا", "محليا", "عالميا", "أسبوعيا", "اسبوعيا", "شهريا", "تدريجيا",
    "مبدئيا", "جزئيا", "كليا",
}
# Final ه after a consonant that is not the 3rd-person suffix: root /h/ (شبه, وجه, ...),
# learned forms (هذه, به), and the Egyptian demonstratives/adverbs whose ه spells /a/.
H_ROOT = {"هذه", "به", "شبه", "أشبه", "اشبه", "تشبه", "يشبه", "نشبه", "وجه", "واجه", "تواجه",
          "يواجه", "نواجه", "اتجه", "تتجه", "يتجه", "توجه", "يتوجه", "نتوجه", "آه", "اه", "هه", "جه",
          "فقه", "تافه", "انتبه", "نبه", "منبه", "إله", "اله", "فواكه", "اتجه", "ينتبه", "تنتبه", "ننتبه",
          "يكره", "تكره", "نكره", "اكره", "طه",
          # v1.7
          "ينبه", "تنبه", "يوجه", "شوه", "يشوه", "تشوه", "نوه", "ينوه", "تنوه", "يفقه", "تفقه", "يأبه"}
H_VOWEL = {"ده", "كده", "لسه", "بره", "النهارده", "بكره"}
# Learned (Classical) vocabulary in which Egyptian and Levantine speakers realize Thāʾ and
# Dhāl as /s/ and /z/ rather than the colloquial /t/ and /d/ (إذا /iza/, حادث /ħaːdis/).
LEARNED = {
    "هذا", "هذه", "ذلك", "كذلك", "كذا", "هكذا", "ماذا", "لماذا", "إذا", "اذا", "إذن", "اذن", "منذ", "ثم",
    "ذات", "بحث", "أبحاث", "ابحاث", "باحث", "باحثين", "يبحث", "حدث", "أحداث", "احداث", "حادث", "حادثة",
    "حوادث", "حديث", "حديثة", "تحدث", "يتحدث", "حدثت", "أحدث", "ثورة", "ثورات", "ثوري", "ثورية", "ثوار",
    "ثابت", "ثابتة", "ثبت", "أثبت", "اثبت", "أثبتت", "أثر", "اثر", "آثار", "اثار", "أثار", "تأثير",
    "تأثر", "يتأثر", "اتأثر", "مؤثر", "مؤثرة", "يؤثر", "أثرية", "مثلا", "مثال", "أمثلة", "مثالي",
    "مثالية", "تمثيل", "ممثل", "تمثال", "تماثيل", "ثقافة", "ثقافي", "ثقافية", "ثقة", "ذكر", "ذكرى",
    "ذكريات", "ذاكرة", "تذكر", "يذكر", "ذكاء", "ذكي", "غذاء", "غذائي", "غذائية", "تغذية", "أغذية",
    "اغذية", "أستاذ", "استاذ", "كارثة", "كوارث", "تنفيذ", "نفوذ", "إنقاذ", "انقاذ", "ينقذ", "استثمار",
    "مستثمر", "مستثمرين", "استثناء", "استثنائي", "أثناء", "اثناء", "كثافة", "جاذبية", "يجذب",
    "ثانيا", "عذاب", "حذر", "ذهن", "ذهنية", "تلميذ", "تلاميذ", "نموذج", "وراثية", "وثيقة", "وثائق",
    # v1.7
    "أنقذ", "انقذ", "تنقذ", "منقذ", "ذوات", "ذو", "ذوي", "جثة", "جثث", "بذل", "بذلت", "بذلنا", "بذلوا", "يبذل", "تبذل", "مبذول",
    "لثة", "أتحدث", "اتحدث", "نتحدث", "متحدث",
}
_PREFIXES = sorted({a + b + c for a in ("", "و", "ف") for b in ("", "ب", "ك", "ل") for c in ("", "ال")}
                   | {a + "لل" for a in ("", "و", "ف")}, key=len, reverse=True)
_SUFFIXES = ("", "ه", "ها", "هم", "هن", "ك", "كم", "نا", "ي", "ة", "ات", "ين", "ون", "ا", "ية", "يات")
NOT_LEARNED = {"هذاك", "هذيك"}                                  # Levantine colloquial demonstratives (hadaːk)

def stems(bare, suffixes=False):
    """The bare word and the forms left after removing proclitics/article (and, if suffixes,
    one pronoun or inflectional suffix), keeping at least two letters."""
    out = set()
    for p in _PREFIXES:
        if bare.startswith(p) and len(bare) - len(p) >= 2:
            s = bare[len(p):]
            out.add(s)
            if suffixes:
                out.update(s[:-len(x)] for x in _SUFFIXES if x and s.endswith(x) and len(s) - len(x) >= 2)
    return out

def is_learned(bare):
    """True if the bare word is (an inflected form of) a learned word of the LEARNED lexicon."""
    return not (stems(bare) & NOT_LEARNED) and bool(stems(bare, suffixes=True) & LEARNED)

def article_parse(word):
    """Analyse word-initial article material. Returns (kind, proclitics, start) where kind is
    'article' (ال), 'proc' (proclitic(s) + ال), 'lil' (لل, possibly after و/ف) or None;
    proclitics is the string of proclitic letters; start is the index of the first stem letter."""
    pos = [k for k, ch in enumerate(word) if not _DIACRITIC.match(ch)]   # letter positions
    bare = strip_diacritics(word)
    if bare in NOT_ARTICLE or (bare.startswith("والد") and bare[4:] in _WALID_SUFFIXES) or is_form8_lam(bare):
        return None, "", 0                                     # والدي, الفين, التزام: ال is not the article
    if is_article(word):
        return "article", "", pos[2]
    letters = [word[k] for k in pos]
    for lead in ("", "و", "ف"):
        m = len(lead)
        if "".join(letters[:m]) != lead:
            continue
        if letters[m:m + 2] == [LAM, LAM] and len(letters) >= m + 3 and _ARABIC_LETTER.match(letters[m + 2]):
            return "lil", lead, pos[m + 2]
        if (len(letters) >= m + 5 and letters[m] in PROCLITICS and letters[m + 1] == ALIF
                and letters[m + 2] == LAM and letters[m + 3] != ALIF_MAQSURA
                and _ARABIC_LETTER.match(letters[m + 3]) and (m == 0 or letters[m] in "بك")):
            return "proc", lead + letters[m], pos[m + 3]
    return None, "", 0

# Derived verbal nouns of forms VII, VIII and X begin with hamzat al-waṣl, which is not
# pronounced after the article (الاستثمار /el-stθmaːr/, not /el-ʔstθmaːr/).
# The nouns اسم, ابن, اثنين/اتنين and امرأة also begin with hamzat al-waṣl (with or
# without a pronominal suffix; the plurals أسماء, أبناء have a pronounced hamza).
WASL_NOUNS = {"اسم", "ابن", "ابنة", "ابنت", "اثنين", "اثنان", "اتنين", "امرأة", "امراة"}
WASL_IMPERATIVES = ("اسمع", "اسمح")                            # اسمع "listen", اسمح "allow", with endings
NOT_WASL = {"باتمان", "واتساب", "فاتنات", "كاتدرائية"}           # loanwords and nouns shaped like form VIII
NOT_WASL_STEMS = ("استرال", "اسطوان")                            # أستراليا, أسطوانة: hamzat al-qaṭʿ
NOT_FORMX = ("استراتيج", "استاذ", "استاد", "استوديو", "استديو", "استيك", "استوك")   # loans, أستاذ: not form X
NOT_PLURAL = {"جوا", "سوا", "هوا"}                               # جوا "inside", سوا "together", هوا "air": not verbs
_PRON = ("", "ه", "ها", "هم", "ي", "ك", "نا", "كم")

def _wasl_stem(stem, after_article=True):
    s = strip_diacritics(stem)
    if not s or s[0] != ALIF:
        return False
    if any(s.endswith(x) and s[:len(s) - len(x)] in WASL_NOUNS for x in _PRON) or s.startswith(WASL_IMPERATIVES):
        return True
    if s.startswith(NOT_WASL_STEMS):
        return False
    if is_form8_lam(s) or (not after_article and len(s) >= 6 and s.startswith("است") and not s.startswith(NOT_FORMX)):
        return True                                            # التزام; واستخدم (Form X verb after و/ف, see below)
    return ((len(s) >= 6 and ((s[4] == ALIF and (s[1] == "ن" or s[2] in "تطد"))
                              or (s.startswith("است") and s[5:6] == ALIF)))
            or (len(s) >= 5 and s[1] == "ت" and s[3] == ALIF))   # assimilated form VIII: اتجاه, اتصال

# لأن "because" written with a bare Alif: the Alif is the hamza seat /ʔ/, not a long vowel.
LAN = {"لان", "لانه", "لانها", "لانهم", "لاني", "لانك", "لاننا", "لانكم", "لانو"}
# Words with a silent final Wāw.
SILENT_WAW = {"عمرو"}

# ---------- v1.7 lexicons ----------
# Proclitics that can precede a LONG_A word (وهذا, بهذه, ولكن, لذلك, كهذا).
LONG_A_PROCLITICS = ("وب", "فب", "وك", "فك", "ول", "فل", "و", "ف", "ب", "ك", "ل")
# ألف "thousand" and its forms written with a bare Alif: ال is the root, not the article.
_ALF = {"الف", "الفين", "الفان", "الاف", "الفا", "الفي"}
NOT_ARTICLE |= _ALF | {p + w for p in ("و", "ف", "ب", "ك", "وب", "فب") for w in _ALF if len(p + w) >= 5}
# Form VIII of roots with first radical Lām (التقى, التزام): ال is part of the stem. Exact stems
# (with pronoun or plural endings) only: a prefix test would also catch التفاصيل, التحقيق, التمساح.
FORM8_LAM = {"التقاء", "التقى", "التقيت", "التقينا", "التقوا", "التقت", "التزام", "التزامات", "التزم",
             "التزمت", "التزموا", "التزمنا", "التهاب", "التهابات", "التحاق", "التحق", "التحقت",
             "التحقوا", "التماس", "التفات", "التفاتة", "التفت", "التفتت", "التفتوا", "التصاق", "التصق",
             "التصقت", "التحام", "التحم", "التحمت", "التفاف", "التواء", "التواءات", "التوى", "التهب", "التهبت"}
_F8_ENDINGS = ("", "ه", "ها", "هم", "ي", "ك", "نا", "كم", "اتي", "اته", "اتها", "اتهم", "اتنا", "اتك", "اتكم")
NOT_FORM8 = {"التماسك", "التفتت"}                              # al-tamāsuk "cohesion", al-tafattut "fragmentation"
def is_form8_lam(bare):
    """True if bare is (proclitic +) a Form VIII word of a Lām-initial root (التزاماتي, والتقى)."""
    if bare in NOT_FORM8:
        return False
    for p in LONG_A_PROCLITICS + ("",):
        r = bare[len(p):] if bare.startswith(p) else None
        if r and any(r.endswith(x) and r[:len(r) - len(x)] in FORM8_LAM for x in _F8_ENDINGS):
            return True
    return False
# MSA relative pronouns spelled with one Lām: ال + the pronoun's own Lām, pronounced /-ll-/
# (الذي /a-llaðiː/, not /a-ððiː/); their Dhāl is learned /z/ in Egyptian and Levantine.
REL_ONE_LAM = {"الذي", "الذى", "التي", "التى", "الذين"}
# Stems whose initial bare Alif is a hamza seat after و or ف (واربعة /wʔrbʕa/, not /waːrbʕa/).
PROCLITIC_HAMZA = {"اربع", "اربعة", "اربعين", "احسن", "افضل", "اكتر", "اكثر", "اكبر", "اصغر", "انا", "انت",
                   "انتي", "انتم", "انتو", "احنا", "ايه", "ازاي", "امتى", "امبارح", "اول", "اخر", "اذا",
                   "ايران", "اوروبا", "امريكا"}
# Final ه after ي/و that is the 3rd-person suffix after a consonantal Yāʾ/Wāw (رأيه /ɾʔju/, زيه).
DIPHTHONG_H = {"رأي", "راي", "زي", "عدو", "سعي", "وعي"}
# Feminine nouns frequently spelled with ه for ة (سنه "year", مره "time"): final ه is /a/.
UNIT_HA = {"مره", "دقيقه", "ثانيه", "ساعه", "نقطه", "درجه", "ليره", "قطعه", "خطوه"}
UNIT_HA_AFTER_NUM = {"سنه", "سعره", "حبه"}                  # only after a numeral: 41 سنه, 2000 سعره "calories"
# Classical words with /q/ in every variety.
QAF_Q = {"قرآن", "قريش", "قحلاء"}
# Loanwords whose ج is /ɡ/ in every variety.
JIM_G = {"جراند", "جوجل"}
# Proclitic + bare article before a shielded numeral or Latin-script word (بال2013, والAI).
ART_BEFORE_SHIELD = {"وال", "فال", "بال", "كال", "لل", "وبال", "فبال", "وكال", "ولل", "فلل"}
# Construct state after a demonstrative هال (Levantine, Gulf) or a possessed kinship noun.
NOT_HAL = {"هالة", "هالات", "هالك", "هالكة", "هالو", "هالوين", "هالقد"}         # هالقد "this much": adverb
KIN_NOUNS = {"اولاد", "أولاد", "ولاد", "اهل", "أهل", "صحاب", "اصحاب", "أصحاب", "اصدقاء", "أصدقاء", "اخوات",
             "أخوات", "اخوان", "إخوان", "بنات", "عيال", "ام", "أم", "اب", "أب", "ابو", "أبو", "اخو", "أخو"}

# ---------- Stage 1: normalization and lexical shield ----------
def normalize_token(tok):
    """Remove Tatweel and strip non-letter characters (punctuation, digits, symbols)
    from both ends of an Arabic token; diacritics on the last letter are kept."""
    tok = _strip_inner(tok)
    a, b = 0, len(tok)
    while a < b and not _ARABIC_LETTER.match(tok[a]):
        a += 1
    while b > a and not (_ARABIC_LETTER.match(tok[b - 1]) or _DIACRITIC.match(tok[b - 1])):
        b -= 1
    return tok[a:b]

def segment(text):
    """Yield ("en", span) for shielded Latin-script material, ("num", digits) for numerals,
    ("ar", token) for normalized Arabic tokens, and ("pb", raw) where punctuation separates words. Explicit <eng>...</eng> tags are honoured, and Latin-script
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
                    continue
                for sub in _NUMBER.split(part):
                    if not sub:
                        continue
                    if _NUMBER.fullmatch(sub):
                        yield ("num", sub)
                        continue
                    p = normalize_token(sub)
                    if p:
                        raw = sub.replace(TATWEEL, "")
                        if not _ARABIC_LETTER.match(raw[0]):
                            yield ("pb", sub)                  # punctuation before the word
                        yield ("ar", p)
                        if not (_ARABIC_LETTER.match(raw[-1]) or _DIACRITIC.match(raw[-1])):
                            yield ("pb", sub)                  # punctuation after the word
                    elif sub.strip():
                        yield ("pb", sub)
                continue

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

def strip_diacritics(word):
    return _DIACRITIC.sub("", word)

def is_article(word):
    """Word-initial definite article: ال followed by an Arabic letter other than Alif maqṣūra
    (so that the unhamzated preposition الى is not read as an article). Diacritics written
    on the Alif or the Lām (hand-vocalized الْ) are skipped."""
    letters = [ch for ch in word if not _DIACRITIC.match(ch)]
    return (len(letters) >= 3 and letters[0] == ALIF and letters[1] == LAM
            and letters[2] != ALIF_MAQSURA and bool(_ARABIC_LETTER.match(letters[2]))
            and letters != [ALIF, LAM, ALIF])                # الا "except" (ʔillā)

def _h_vowel(bare, rules):
    """ده, كده, لسه, بره, النهارده, بكره, alone or after و/ف and ب/ل; bare ده after a proclitic
    only in Egyptian (Levantine بده is biddo 'he wants', Gulf وده is widda 'he wants')."""
    for lead in ("", "و", "ف"):
        for prep in ("", "ب", "ل"):
            p = lead + prep
            if bare.startswith(p) and bare[len(p):] in H_VOWEL:
                stem = bare[len(p):]
                return not (stem == "ده" and p and rules["pronoun_suffix"] != "u")
    return False

def _final(word, i):
    """True if only diacritics follow position i."""
    return not strip_diacritics(word[i + 1:])

def long_a_positions(word):
    """Letter indices after which an unwritten /aː/ is inserted (LONG_A), also after proclitics
    (وهذا, بهذه, ولكن, لذلك). Undiacritized input only."""
    if word in LONG_A:
        return LONG_A[word]
    for p in LONG_A_PROCLITICS:
        if word.startswith(p) and word[len(p):] in LONG_A:
            return {k + len(p) for k in LONG_A[word[len(p):]]}
    return ()

def _stems_in(bare, lex):
    return bool(stems(bare, suffixes=True) & lex)

def transcribe_aligned(word, letters, diacritics, sun_letters, rules, construct=False, before_shield=False,
                       after_num=False):
    """Return the word's realization as a list of (ipa_unit, source_index).
    construct: the word is followed by a definite noun (Tāʾ Marbūṭa takes its construct form).
    before_shield: the next token is a shielded numeral or Latin-script span (بال2013).
    after_num: the previous token is a numeral (2000 سعره)."""
    units=[]; i=0; n=len(word)
    bare = strip_diacritics(word)
    if bare in ALLAH:
        return [(ALLAH[bare], LEXICAL)]
    long_a = long_a_positions(word)
    moon = rules["phonological_rules"]["al_prefix_moon"]["ipa"].strip('/')
    if word == ALIF + LAM:                                     # bare article attached to a shielded word (الـAI)
        return [(moon, ARTICLE)]
    if before_shield and word in ART_BEFORE_SHIELD:            # بال2013, والAI: proclitic + article
        if word.endswith(LAM + LAM):
            pre = rules.get("lil_prefix", "/lil-/").strip('/'); lead = word[:-2]
        else:
            pre = rules["proclitic_vowel"][word[-3]] + "l-"; lead = word[:-3]
        return [(letters[ch]["phoneme"].strip('/'), k) for k, ch in enumerate(lead)] + [(pre, ARTICLE)]
    learned = rules.get("learned", {}) if is_learned(bare) else {}
    qaf_q = _stems_in(bare, QAF_Q)
    jim_g = _stems_in(bare, JIM_G)

    def lookup(ch):
        if ch in learned:
            return learned[ch]                                 # learned word: /s/, /z/ (EGY, LEV)
        if ch == "ق" and qaf_q:
            return "q"                                         # القرآن: /q/ in every variety
        if ch == "ج" and jim_g:
            return "ɡ"                                         # جوجل: loanword /ɡ/
        if ch == "غ" and _final(word, i_now[0]) and bare.endswith("ينغ") and len(bare) >= 4:
            return "ɡ"                                         # -ing loanwords (كينغ, الكريفينغ)
        return letters[ch]["phoneme"].split(" or ")[0].strip('/')
    i_now = [0]

    # word-initial article material: ال, proclitic(s) + ال, لل
    kind, procs, start = article_parse(word)
    if kind:
        if kind == "article":
            moon_pre, sun_pre = moon, rules["phonological_rules"]["al_prefix_sun"]["ipa"].strip('/')
            lead = ""
        elif kind == "proc":
            v = rules["proclitic_vowel"][procs[-1]]
            moon_pre, sun_pre, lead = v + "l-", v + "-", procs[:-1]
        else:                                                  # لل
            moon_pre = rules.get("lil_prefix", "/lil-/").strip('/')
            sun_pre, lead = moon_pre[:-2] + "-", procs
        k = 0
        for ch in lead:                                        # و/ف before ب, ك or لل
            while word[k] != ch: k += 1
            units.append((lookup(ch), k)); k = _consume_diacritics(word, k + 1, n, diacritics, units)
        stem = strip_diacritics(word[start:])
        if "ال" + stem in REL_ONE_LAM:                         # الذي, والتي, للذين: /-ll-/
            learned = rules.get("learned", {})
            lam = start - 1
            while word[lam] != LAM: lam -= 1
            units.append((sun_pre, ARTICLE)); units.extend([("l", lam), ("l", lam)]); i = start
        elif word[start] in sun_letters:
            sp = lookup(word[start])
            if sp == "ɾ": sp = "r"                              # geminate tap -> trill
            units.append((sun_pre, ARTICLE))
            units.extend([(sp, start), (sp, start)])           # assimilated + geminated
            i=_consume_diacritics(word,start+1,n,diacritics,units,absorb_shadda=True)
        else:
            units.append((moon_pre, ARTICLE)); i=start
    while i<n:
        i_now[0] = i
        ch=word[i]
        nxt=word[i+1] if i+1<n else ""
        # bare Alif / Alif maqṣūra
        if ch==ALIF or ch==ALIF_MAQSURA:
            after_article = bool(units) and units[-1][1]==ARTICLE
            second = len(strip_diacritics(word[:i])) == 1      # second letter of the word
            after_proclitic = second and word[0] in PROCLITICS + LAM
            if (ch==ALIF and bare not in NOT_WASL and (after_article or after_proclitic)
                    and _wasl_stem(word[i:], after_article or word[0] not in "وف")):
                pass                                           # hamzat al-waṣl after the article or a proclitic: silent
            elif ch==ALIF and second and (bare in LAN or (bare[0] in "وف" and bare[1:] in PROCLITIC_HAMZA)):
                units.append(("ʔ", i))                          # لانه, واربعة: hamza seat
            elif ch==ALIF and (i==0 or after_article):
                units.append(("ʔ", i))                          # glottal onset (also after the article)
            elif units and units[-1][0]=="an":
                pass                                           # ًا : Alif is the silent seat of tanwīn
            elif nxt in TANWIN_MARKS:                          # اً : tanwīn written on the Alif
                if units and units[-1][0]=="a": units.pop()
                units.append((TANWIN_MARKS[nxt], i)); i+=1
            elif ch==ALIF and _final(word, i) and (bare in TANWIN_ADV or bare[1:] in TANWIN_ADV and bare[0] in "وف"):
                if units and units[-1][0]=="a": units.pop()
                units.append(("an", i))                        # unmarked tanwīn of an adverb: جدا /ɡdan/
            elif (ch==ALIF and _final(word, i) and len(bare)>=4 and bare[-2]=="و" and bare[-3]!=ALIF and not kind
                  and not (bare[0] in "وفبل" and bare[1:] in NOT_PLURAL)):
                if units and units[-1][0]=="w":                # plural ending ـوا: Wāw is /uː/, Alif silent
                    units[-1]=("uː", units[-1][1])
            elif units and units[-1][0]=="a":
                units[-1]=("aː", i)                            # fatḥa + Alif -> one long vowel
            else:
                units.append(("aː", i))
            i=_consume_diacritics(word,i+1,n,diacritics,units); continue
        # Tāʾ Marbūṭa: pausal /a/; in MSA /t/ surfaces when a vowel or tanwīn is written on it;
        # in the construct state (before a definite noun) it is /et/, /ɪt/ or /at/ in every variety.
        if ch == TAA_MARBUTA:
            after_long = bool(units) and units[-1][0] == "aː"         # صلاة, حياة: /aː/ already written
            if not (units and units[-1][0] in ("a", "aː")):
                units.append(("a", i))
            if (nxt in VOWEL_MARKS or nxt in TANWIN_MARKS) and rules.get("taa_marbuta_t", False):
                units.append(("t", i))
                i=_consume_diacritics(word,i+1,n,diacritics,units); continue
            i += 1
            while i < n and word[i] in diacritics:             # dialects: case marks ignored
                i += 1
            if construct:
                ct = rules["construct_ta"]
                if not after_long:
                    units[-1] = (ct[:-1], units[-1][1])
                units.append((ct[-1], i))
            continue
        # regular letter
        if ch in letters:
            ph=lookup(ch)
            # long vowels: Wāw after ḍamma / Yāʾ after kasra, with no vowel or shadda of their own
            if (ch in "وي" and units and units[-1][0]==("u" if ch=="و" else "i")
                    and nxt not in VOWEL_MARKS and nxt not in TANWIN_MARKS and nxt!=SHADDA):
                units[-1]=(units[-1][0]+"ː", i)
                i=_consume_diacritics(word,i+1,n,diacritics,units); continue
            if ch==HAMZA_BELOW and nxt=="\u0650":
                ph="ʔ"                                         # explicit kasra supplies the /i/
            # final Hāʾ after a consonant (EGY, LEV): the 3rd-person suffix is a vowel (عنده /ʕndu/);
            # ده, كده, ... spell /a/; root and learned /h/ is kept (شبه, هذه)
            unmarked = i + 1 >= n                              # no diacritic written on the final ه
            if ch == "ه" and _final(word, i) and unmarked and not rules["taa_marbuta_t"] and _h_vowel(bare, rules):
                units.append(("a", i)); i = n; continue        # ده, كده: ه spells /a/ (dialects)
            if (ch == "ه" and _final(word, i) and unmarked and not rules["taa_marbuta_t"] and not kind
                    and word == bare and (stems(bare) & UNIT_HA or after_num and stems(bare) & UNIT_HA_AFTER_NUM)):
                units.append(("a", i)); i = n; continue        # سنه "year", 2000 سعره: ه spells Tāʾ Marbūṭa
            if (ch == "ه" and rules.get("pronoun_suffix") and _final(word, i) and unmarked and len(bare) >= 2
                    and (bare[-2] not in "اويى" or stems(bare) & {d + "ه" for d in DIPHTHONG_H})
                    and not (stems(bare) & H_ROOT)):
                # a definite noun takes no possessive suffix: its final ه spells Tāʾ Marbūṭa (الكوره)
                if units and units[-1][0] in ("a", "i", "u"):
                    units.pop()                                # a written vowel before the suffix (عِنْدُه)
                units.append(("a" if kind else rules["pronoun_suffix"], i))
                i = n; continue
            if ch == "و" and _final(word, i) and bare in SILENT_WAW:
                i = n; continue                                # عمرو: silent Wāw
            if ph: units.append((ph, i))
            k=i
            i=_consume_diacritics(word,i+1,n,diacritics,units)
            if k in long_a: units.append(("aː", LEXICAL))     # unwritten long /aː/
            continue
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
    segs=list(segment(text))
    for k, (kind, tok) in enumerate(segs):
        if kind == "en":
            out.append(f"<eng>{tok}</eng>")
        elif kind == "num":
            out.append(f"<num>{tok}</num>")
        elif kind == "ar":
            u=transcribe_aligned(tok,letters,diacritics,sun,rules,construct=is_construct(segs,k,rules),
                                 before_shield=k + 1 < len(segs) and segs[k + 1][0] in ("en", "num"),
                                 after_num=k > 0 and segs[k - 1][0] == "num")
            if u: out.append("/" + "".join(x for x,_ in u) + "/")
    return " ".join(out)

def is_construct(segs, k, rules=None):
    """Tāʾ Marbūṭa construct state: an undetermined word ending in ة directly followed (no
    punctuation) by a definite word: a word with the article (كرة السلة /kuɾet e-ssl.../), in
    Levantine and Gulf a word with the demonstrative هال (مناسبة هالكلام), or a possessed
    kinship noun (جثة أولادها)."""
    kind, tok = segs[k]
    bare = strip_diacritics(tok)
    if (kind != "ar" or not bare.endswith(TAA_MARBUTA) or article_parse(tok)[0] or bare in NO_CONSTRUCT
            or any(m in tok for m in TANWIN_MARKS)):         # written tanwīn: the noun is indefinite
        return False
    if not (k + 1 < len(segs) and segs[k + 1][0] == "ar"):
        return False
    nxt = segs[k + 1][1]
    nb = strip_diacritics(nxt)
    if is_article(nxt):                                        # also الفين, التزام: counted noun, verbal noun
        return nb not in RELATIVES
    if (rules is not None and rules["construct_ta"] in ("ɪt", "at") and not rules["taa_marbuta_t"]
            and nb.startswith("هال") and len(nb) >= 5 and nb not in NOT_HAL):
        return True                                            # Levantine/Gulf هالـ "this"
    return any(nb.endswith(x) and nb[:len(nb) - len(x)] in KIN_NOUNS for x in _PRON if x)

# Words after which a following article word is not a construct dependent.
RELATIVES = {"اللي", "الذي", "التي", "الذين", "اللذان", "اللتان", "اللذين", "اللتين", "اللاتي", "اللواتي", "اللائي"}
NO_CONSTRUCT = {"برة"}                                         # adverb "outside" (Egyptian barra)
