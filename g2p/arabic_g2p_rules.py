"""
Expert-revised Arabic G2P rules + diacritize-then-G2P architecture.
Grounded in: sun/moon letter assimilation (lam IS a sun letter), hamza = glottal stop,
alif = /aː/ medially & glottal onset word-initially, and the principle that short vowels
require a diacritization stage (CAMeL/Mishkal/Farasa) before G2P.
"""
import re

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
        "Khaliji Arabic":  {"ث":"/θ/","ج":"/dʒ/","ذ":"/ð/","ظ":"/ðˤ/","ق":"/g/","ر":"/r/","ة":"/a/ or /at/"},
        "Modern Standard Arabic (MSA)": {"ث":"/θ/","ج":"/dʒ/","ذ":"/ð/","ظ":"/ðˤ/","ق":"/q/","ر":"/r/","ة":"/a/ or /at/"},
    }
    art = {  # (moon prefix, sun prefix) — narrow transcription from the xlsx
        "Egyptian": ("/el-/","/e-/"),
        "Levantine Arabic": ("/ɪl-/","/ɪ-/"),
        "Khaliji Arabic": ("/ɪl-/","/ɪ-/"),
        "Modern Standard Arabic (MSA)": ("/al-/","/a-/"),
    }
    lil = {"Egyptian":"/lel-/","Levantine Arabic":"/lil-/","Khaliji Arabic":"/lil-/","Modern Standard Arabic (MSA)":"/lal-/"}
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
def DIACRITIZE_HOOK(text, enable=False):
    """
    Recover short vowels BEFORE G2P (the linguistically correct fix).
    Tries CAMeL Tools, then Mishkal; identity fallback if neither installed.
    Off by default so the pipeline runs without heavy deps.
    """
    if not enable: return text
    try:
        from camel_tools.disambig.mle import MLEDisambiguator
        mle = MLEDisambiguator.pretrained()
        toks = text.split()
        out = []
        for d in mle.disambiguate(toks):
            diac = d.analyses[0].analysis.get('diac') if d.analyses else None
            out.append(diac or d.word)
        return " ".join(out)
    except Exception:
        pass
    try:
        from mishkal.tashkeel import TashkeelClass
        return TashkeelClass().tashkeel(text)
    except Exception:
        return text  # identity; output will be a consonant+long-vowel skeleton

def get_rules(dialect):
    if not isinstance(dialect,str): return IPA_RULES["dialects"]["Modern Standard Arabic (MSA)"]
    if "Egyptian" in dialect: return IPA_RULES["dialects"]["Egyptian"]
    if "Levantine" in dialect: return IPA_RULES["dialects"]["Levantine Arabic"]
    if "Khaliji" in dialect or "Gulf" in dialect: return IPA_RULES["dialects"]["Khaliji Arabic"]
    return IPA_RULES["dialects"]["Modern Standard Arabic (MSA)"]

def _consume_diacritics(word, j, n, diacritics, units):
    """Consume a run of diacritics from index j. Shadda doubles the last unit;
    a vowel diacritic is appended. Order-independent (handles consonant+shadda+vowel)."""
    shadda=False; vowel=None
    while j<n and word[j] in diacritics:
        if word[j]=='\u0651':            # shadda
            shadda=True
        else:
            v=diacritics[word[j]]
            if v not in ("","doubled"): vowel=v.strip('/')
        j+=1
    if shadda and units: units.append(units[-1])
    if vowel: units.append(vowel)
    return j

def transcribe_arabic(word, letters, diacritics, sun_letters, rules):
    units=[]; i=0; n=len(word)
    while i<n:
        ch=word[i]
        # word-initial للـ
        if i==0 and ch=='\u0644' and i+1<n and word[i+1]=='\u0644':
            units.append(rules.get("lil_prefix","/lil-/").strip('/')); i+=2; continue
        # word-initial definite article الـ
        if i==0 and ch=='\u0627' and i+1<n and word[i+1]=='\u0644':
            if i+2<n and word[i+2] in sun_letters:
                pre=rules["phonological_rules"]["al_prefix_sun"]["ipa"].strip('/')
                sp=letters.get(word[i+2],{}).get("phoneme","").split(" or ")[0].strip('/')
                units.append(f"{pre}{sp}{sp}"); i+=3
                i=_consume_diacritics(word,i,n,diacritics,units); continue
            else:
                units.append(rules["phonological_rules"]["al_prefix_moon"]["ipa"].strip('/')); i+=2; continue
        # bare alif: word-initial glottal onset /ʔ/, else long /aː/ (fatha+alif merge)
        if ch=='\u0627':
            if i==0: units.append("ʔ")
            elif units and units[-1]=="a": units[-1]="aː"   # preceding fatha lengthens
            else: units.append("aː")
            i=_consume_diacritics(word,i+1,n,diacritics,units); continue
        # taa marbuta: /a/ in pausal, but DO NOT double if preceded by fatha (last unit "a")
        if ch == '\u0629':                                  # ة
            if not (units and units[-1] == "a"):
                units.append("a")
            # (no diacritic consumption needed; ة doesn't take a vowel)
            i += 1; continue
        # regular letter
        if ch in letters:
            ph=letters[ch]["phoneme"]
            if " or " in ph: ph=ph.split(" or ")[0]
            if ph: units.append(ph.strip('/'))
            i=_consume_diacritics(word,i+1,n,diacritics,units); continue
        i+=1
    joined="".join(units)
    return f"/{joined}/" if joined else ""

def transcribe_protected(text, dialect, diacritize=False):
    if text is None or text=="": return ""
    text = DIACRITIZE_HOOK(str(text), enable=diacritize)
    rules=get_rules(dialect); letters=rules["letters"]
    diacritics={**rules["vowels"]["short"],**rules["diacritics"]}
    spec=rules["phonological_rules"]["al_prefix_sun"].get("letters")
    sun=set(spec.replace(",","").replace(" ","")) if spec else SUN_LETTERS
    out=[]
    for chunk in re.split(r'(<eng>.*?</eng>)',str(text)):
        if chunk.startswith("<eng>") and chunk.endswith("</eng>"): out.append(chunk)
        elif chunk.strip():
            for w in chunk.strip().split():
                p=transcribe_arabic(w,letters,diacritics,sun,rules)
                if p: out.append(p)
    return " ".join(out)
