"""Build the human-evaluation workbooks (design A: annotators judge the engine's own output --
consonants, the definite article, written long vowels -- on undiacritized text).

Outputs, in <out_dir>:
  annotator_EGY-A.xlsx ... annotator_GLF-B.xlsx   one file per annotator: only that dialect's
                                                  50 sentences and that annotator's columns, so
                                                  the two annotators of a dialect judge blind
  G2P_human_evaluation_150.xlsx                   adjudication workbook: filled by
                                                  merge_annotations.py, then adjudicated

Usage: python build_workbook.py <sentences.csv> <out_dir>
"""
import csv
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.worksheet.datavalidation import DataValidation

rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
F = "Arial"
HDR = Font(name=F, bold=True, color="FFFFFF"); HFILL = PatternFill("solid", fgColor="1F4E78")
INPUT = PatternFill("solid", fgColor="FFF2CC"); CALC = PatternFill("solid", fgColor="F2F2F2")
RED = PatternFill("solid", fgColor="F8CBAD")
thin = Side(style="thin", color="BFBFBF"); BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
RTL = Alignment(horizontal="right", vertical="top", wrap_text=True, readingOrder=2)
WRAP = Alignment(vertical="top", wrap_text=True)
CENTER = Alignment(horizontal="center", vertical="top", wrap_text=True)
DIALECT_NAME = {"EGY": "Egyptian", "LEV": "Levantine", "GLF": "Gulf"}
ERROR_TYPES = ["Dialect consonant", "Definite article", "Long vowel or lexical word",
               "Foreign name or loanword", "Other"]
UNLOCK = Protection(locked=False)
CONTACT = "Robeir Basily, robeir.samir@eng.asu.edu.eg"

# ------------------------------------------------------------------ guide (English, Egyptian Arabic)
EN = [
 ("Who fills this in", "One native-speaker annotator, alone. Please do not use AI tools, automatic transcription, or anyone else's answers, and do not discuss the sentences with the other annotator of your dialect until you have both finished. Your judgments will be released anonymised, under your annotator code only; by filling in the sheet you agree to this. Expected time: about 1.5 to 2 hours for 50 sentences. Questions: " + CONTACT + "."),
 ("Task", "Each row is one sentence of your dialect and the engine's IPA transcription of it. Judge whether the engine pronounces the consonants, the definite article, and the written long vowels of every word as a native speaker of the dialect naturally would in this sentence."),
 ("Reference variety", "Judge against the main urban variety of the dialect: Egyptian = Cairo; Levantine = the urban speech of Syria, Lebanon, Palestine and Jordan (Qāf as glottal stop /ʔ/, Jīm as /ʒ/); Gulf = the common Gulf koine (Jīm /dʒ/, Qāf /ɡ/, Kāf /k/). If the engine's form is common in a major city variety of the dialect, accept it even if your own variety differs (for example, Gulf /j/ for Jīm or /tʃ/ for Kāf is not required)."),
 ("What the transcription contains", "A consonantal skeleton. Short vowels are not written in the source text, so they are intentionally absent (except where the sentence itself has vowel marks, which the engine copies): do NOT judge missing short vowels. Wāw and Yāʾ are written /w/ and /j/ even where they are long vowels (e.g. /ʔkjd/ for أكيد): do NOT judge this. Doubled consonants appear only where the text writes a shadda or the article assimilates: do NOT judge a missing doubling elsewhere. A long vowel that the script does not write (as in هذين) is not judged either; the engine restores it only in a few frequent words (هذا, ذلك, لكن). The symbols are explained on the 'Symbols' sheet."),
 ("What to judge", "(1) Every consonant (Jīm, Qāf, Thāʾ, Dhāl, Ẓāʾ, Ḍād and all others), as the dialect pronounces it in this word. (2) The definite article, also after و, ف, ب, ك and in لل: its vowel and whether it assimilates (sun letters) or not (moon letters); e.g. والشمس /we-ʃʃms/ in Egyptian. (3) Written long vowels and word endings: Alif and Alif maqṣūra are /aː/; hamza and Alif at the start of a word are /ʔ/ (إ is /ʔi/); Tāʾ Marbūṭa at the end of a word is /a/, and in a construct phrase (iḍāfa) /et/ (Egyptian), /ɪt/ (Levantine) or /at/ (Gulf), whatever follows: a noun with the article, a name, or an indefinite noun (كرة السلة, جامعة القاهرة, حركة بيع); tanwīn written with Alif is /an/ (جدا /ɡdan/); the ending ـه 'his, him' as the dialect pronounces it (Egyptian /u/, Levantine /o/; in Gulf, /h/ is fine). (4) Letters that are not pronounced must not appear: the Alif of the plural ending ـوا (written /uː/); the Alif of the article after و, ف, ب, ك, ل; the waṣl Alif (no glottal stop) of words such as استخدام and اسم after the article or after و, ف, ب, ك, ل; the Wāw of عمرو. (5) Names and loanwords: their consonants."),
 ("Learned words and variants", "Judge by how a native speaker would naturally pronounce THIS word when reading THIS sentence aloud, formal or colloquial as the sentence is: in a formal (MSA-like) sentence, learned pronunciations are natural. If more than one pronunciation is natural for speakers of the dialect (for example /ʔ/ or /q/ for Qāf, /t/ or /s/ for Thāʾ in some learned words), accept any natural one. Mark Not OK only if the engine's form is one a native speaker of this dialect would not use for this word (e.g. /ɡ/ in a learned Gulf word that speakers always say with /q/)."),
 ("Ignore", "Fine phonetic detail (how far emphasis spreads; the exact quality of the article vowel e/ɪ/i); the length of a vowel at the end of a word (/aː/ or /a/); Levantine final Tāʾ Marbūṭa as /e/ (the engine always writes /a/); whether the article assimilates before Jīm or Kāf, where both are heard; the hyphen after the article (/e-ʃʃms/), which only marks a boundary; anything in <eng>…</eng> (Latin script) or <num>…</num> (numerals), which the engine passes through on purpose."),
 ("Typos in the sentence", "Judge the engine against the word as it is written. If a word is misspelled in the source, do not mark Not OK for the typo itself; mention it in Notes. If the intended word cannot be recovered, judge the letters as written."),
 ("Colloquial spellings", "A final ه written for Tāʾ Marbūṭa (حاجه for حاجة) is a normal colloquial spelling, not a typo: judge the engine against the intended word (حاجه = /ħaːɡa/). A word from another dialect is judged with its own pronunciation (كده in a Gulf sentence = /kda/). An abbreviation is read as the full word (كم after a number = kilometre); the engine does not expand abbreviations, so mark it Not OK with error type Other."),
 ("Your decision", "Judgment = OK if everything under 'What to judge' is right. Judgment = Not OK if at least one word has a wrong consonant, article form, written long vowel or word ending, or a letter that is pronounced although it should not be. For Not OK, also fill: Error type, Wrong word, the engine's IPA of that word (copy it from column D), and the Correct IPA, for the MAIN error, in the engine's style (consonants and long vowels only, no short vowels). Main error: the one that most changes how the word sounds; if unsure, the first one in the sentence. Other errors go in Notes."),
 ("Error types", "Dialect consonant: a consonant pronounced in a way that is not the dialect's (Jīm, Qāf, Thāʾ, Dhāl, Ẓāʾ, Ḍād, including learned words). Definite article: the article's vowel, assimilation or form, also after a proclitic, in لل, and in اللي. Long vowel or lexical word: a written long vowel, a letter that should not be pronounced, tanwīn, Tāʾ Marbūṭa, the ending ـه, or an irregular frequent word. Foreign name or loanword: only words of non-Arabic origin (names and borrowings); an Arabic name goes under the other types. Other: anything else (e.g. an abbreviation)."),
 ("Cells to edit", "Only the yellow cells. Everything else is locked. Use the drop-down lists; other values are rejected."),
]
AR = [
 ("مين يملا الشيت", "مقيّم واحد من أهل اللهجة، لوحده. من فضلك ما تستخدمش أدوات ذكاء اصطناعي أو تفريغ صوتي آلي أو إجابات حد تاني، وما تتكلمش في الجمل مع المقيّم التاني بتاع لهجتك غير لما انتو الاتنين تخلصوا. تقييماتك هتتنشر من غير اسمك، بكود المقيّم بس؛ ولما تملا الشيت تبقى موافق على كده. الوقت المتوقع: حوالي ساعة ونص لساعتين لـ 50 جملة. للاستفسار: " + CONTACT + "."),
 ("المهمة", "كل صف فيه جملة من لهجتك، والنطق اللي طلّعه البرنامج ليها مكتوب بالرموز الصوتية (IPA). قيّم: هل البرنامج نطق الحروف، وأداة التعريف، وحروف المد المكتوبة، في كل كلمة، زي ما ابن اللهجة بينطقها طبيعي في الجملة دي؟"),
 ("اللهجة المرجعية", "قيّم على أساس لهجة المدن الأساسية: المصري = القاهرة؛ الشامي = كلام المدن في سوريا ولبنان وفلسطين والأردن (القاف همزة /ʔ/، والجيم /ʒ/)؛ الخليجي = الخليجي المشترك (الجيم /dʒ/، القاف /ɡ/، الكاف /k/). لو نطق البرنامج منتشر في مدينة كبيرة من مدن اللهجة، اقبله حتى لو لهجتك انت مختلفة (مثلاً: الجيم /j/ أو الكاف /tʃ/ في الخليجي مش مطلوبين)."),
 ("شكل الرموز الصوتية", "الحروف بس من غير حركات قصيرة. الحركات القصيرة مش مكتوبة في النص الأصلي، فمش موجودة في الرموز عن قصد (إلا لو الجملة نفسها فيها تشكيل، والبرنامج بينقله): ما تقيّمش غياب الحركات. والواو والياء مكتوبين /w/ و /j/ حتى لو بيتنطقوا حروف مد (زي /ʔkjd/ لـ أكيد): ما تقيّمش ده. والتشديد بيظهر بس لو مكتوب شدة أو مع أداة التعريف الشمسية: ما تقيّمش غياب التشديد في أي مكان تاني. وحرف المد اللي مش مكتوب (زي اللي في هذين) ما بيتقيّمش برضه؛ البرنامج بيرجّعه بس في كام كلمة شائعة (هذا، ذلك، لكن). الرموز مشروحة في شيت Symbols."),
 ("بتقيّم إيه", "(1) نطق كل حرف (الجيم والقاف والثاء والذال والظاء والضاد وغيرهم) زي ما اللهجة بتنطقه في الكلمة دي. (2) أداة التعريف، حتى بعد و ف ب ك وفي لل: الحركة بتاعتها، وهل اندمجت (حروف شمسية) ولا لأ (حروف قمرية)، زي والشمس /we-ʃʃms/ في المصري. (3) حروف المد المكتوبة وآخر الكلمة: الألف والألف المقصورة /aː/؛ الهمزة والألف في أول الكلمة /ʔ/ (والإ /ʔi/)؛ التاء المربوطة في آخر الكلمة /a/، وفي الإضافة /et/ (مصري) أو /ɪt/ (شامي) أو /at/ (خليجي) مهما كان اللي بعدها: اسم معرّف أو اسم علم أو نكرة (كرة السلة، جامعة القاهرة، حركة بيع)؛ التنوين المكتوب بألف /an/ (جدا /ɡdan/)؛ هاء الضمير (بتاعه، شافه) زي ما اللهجة بتنطقها (مصري /u/، شامي /o/؛ في الخليجي /h/ مقبول). (4) الحروف اللي المفروض ما تتنطقش لازم ما تظهرش: ألف واو الجماعة (ـوا مكتوبة /uː/)، ألف أداة التعريف بعد و ف ب ك ل، ألف الوصل (من غير همزة) في كلمات زي استخدام واسم بعد أداة التعريف أو بعد و ف ب ك ل، وواو عمرو. (5) الأسماء والكلمات الأجنبية: حروفها."),
 ("الكلمات الفصيحة والاختلافات", "قيّم على أساس النطق الطبيعي للكلمة دي لما ابن اللهجة يقرا الجملة دي بصوت عالي، رسمي ولا عامي زي ما الجملة مكتوبة: في جملة رسمية (قريبة من الفصحى) النطق الفصيح طبيعي. لو فيه أكتر من نطق طبيعي عند أهل اللهجة (زي /ʔ/ أو /q/ للقاف، أو /t/ أو /s/ للثاء في بعض الكلمات الفصيحة)، اقبل أي نطق طبيعي. اكتب Not OK بس لو البرنامج نطق الكلمة بشكل ابن اللهجة مش هيستخدمه (زي /ɡ/ في كلمة فصيحة الخليجي بينطقها دايماً /q/)."),
 ("تجاهل", "التفاصيل الصوتية الدقيقة (قد إيه التفخيم بيمتد، وحركة أداة التعريف e/ɪ/i بالظبط)؛ طول الحركة في آخر الكلمة (/aː/ ولا /a/)؛ التاء المربوطة الشامية لما تتنطق /e/ (البرنامج دايماً بيكتب /a/)؛ هل أداة التعريف بتندمج قبل الجيم أو الكاف، لأن الاتنين مسموعين؛ الشرطة بعد أداة التعريف (/e-ʃʃms/) لأنها بتعلّم الحدود بس؛ وأي حاجة بين <eng>…</eng> أو <num>…</num> (البرنامج بيعديها من غير نطق عن قصد)."),
 ("أخطاء الكتابة في الجملة", "قيّم البرنامج على الكلمة زي ما هي مكتوبة. لو الكلمة مكتوبة غلط في الأصل، ما تكتبش Not OK بسبب الغلطة الإملائية نفسها؛ اذكرها في الملاحظات. لو مش عارف الكلمة المقصودة، قيّم الحروف زي ما هي."),
 ("الكتابة العامية", "الهاء اللي مكتوبة مكان التاء المربوطة (حاجه بدل حاجة) كتابة عامية عادية مش غلطة: قيّم البرنامج على الكلمة المقصودة (حاجه = /ħaːɡa/). الكلمة اللي من لهجة تانية تتقيّم بنطقها هي (كده في جملة خليجية = /kda/). والاختصار يتقرا كلمة كاملة (كم بعد رقم = كيلومتر)؛ البرنامج ما بيفكّش الاختصارات، فاكتب Not OK ونوع الغلطة Other."),
 ("قرارك", "Judgment = OK لو كل حاجة في (بتقيّم إيه) صح. Judgment = Not OK لو فيه كلمة واحدة على الأقل فيها حرف أو أداة تعريف أو حرف مد أو آخر كلمة غلط، أو حرف المفروض ما يتنطقش واتنطق. ولو Not OK، املا كمان: نوع الغلطة، والكلمة الغلط، ورموزها من البرنامج (انسخها من عمود D)، والرموز الصح، للغلطة الأساسية، بنفس أسلوب البرنامج (الحروف وحروف المد بس، من غير حركات قصيرة). الغلطة الأساسية: اللي بتغيّر صوت الكلمة أكتر؛ ولو مش متأكد، أول غلطة في الجملة. وباقي الأخطاء اكتبها في الملاحظات."),
 ("أنواع الأخطاء", "Dialect consonant: حرف اتنطق بطريقة مش بتاعة اللهجة (الجيم، القاف، الثاء، الذال، الظاء، الضاد، حتى في الكلمات الفصيحة). Definite article: حركة أداة التعريف أو اندماجها أو شكلها، حتى بعد حرف جر أو عطف، وفي لل، وفي اللي. Long vowel or lexical word: حرف مد مكتوب، أو حرف المفروض ما يتنطقش، أو تنوين، أو تاء مربوطة، أو هاء الضمير، أو كلمة شائعة نطقها شاذ. Foreign name or loanword: الكلمات اللي أصلها مش عربي بس (أسماء وكلمات أجنبية)؛ الاسم العربي يتحط في الأنواع التانية. Other: أي حاجة تانية (زي الاختصارات)."),
 ("الخانات اللي تتعدّل", "الخانات الصفرا بس. الباقي مقفول. استخدم القوايم المنسدلة؛ أي قيمة تانية مش هتتقبل."),
]
ADJ = [
 ("Adjudication", "After both annotators of a dialect have finished, merge_annotations.py copies their judgments into this workbook. Then the two annotators meet: (a) for every row where 'Initial disagreement' is Yes, they discuss and enter the agreed decision (Yes = correct, No = not correct) in 'Adjudicated'; (b) for rows where both said Not OK, they confirm that they share at least one wrong word, and if they do not, they treat the row as a disagreement and enter the agreed decision in 'Adjudicated'; (c) for every row whose Final decision is No, they agree on the Error type, Wrong word, Engine IPA of that word and Correct IPA (pre-filled from annotator A where both said Not OK; edit if needed). If the two cannot agree, a third native speaker of the dialect decides; write that in 'Adjudication note'."),
]
ADJ_AR = [
 ("حسم الاختلاف", "بعد ما المقيّمين الاتنين بتوع اللهجة يخلصوا، merge_annotations.py بينقل تقييماتهم للشيت ده. وبعدين المقيّمين يقعدوا مع بعض: (أ) كل صف فيه Initial disagreement = Yes يتناقشوا ويكتبوا القرار المتفق عليه (Yes = صح، No = غلط) في Adjudicated؛ (ب) الصفوف اللي الاتنين قالوا فيها Not OK يتأكدوا إن فيه كلمة غلط واحدة على الأقل متفقين عليها، ولو لأ يعتبروها اختلاف ويكتبوا القرار في Adjudicated؛ (ج) كل صف قراره النهائي No يتفقوا على نوع الغلطة والكلمة الغلط ورموزها من البرنامج والرموز الصح (متملية من المقيّم A لو الاتنين قالوا Not OK؛ عدّلوها لو محتاج). ولو ما اتفقوش، مقيّم تالت من أهل اللهجة يحسم، واكتبوا ده في Adjudication note."),
]
SYMBOLS = [  # symbol, Arabic letter(s), how it sounds
    ("ʔ", "ء أ إ آ ؤ ئ، والقاف في المصري والشامي", "glottal stop (hamza)"),
    ("ɡ", "ج (مصري)، ق (خليجي)", "g as in English 'go'"),
    ("dʒ", "ج (خليجي، فصحى)", "j as in 'jam'"),
    ("ʒ", "ج (شامي)", "s as in 'measure'"),
    ("q", "ق (فصحى)", "uvular q"),
    ("θ / ð", "ث / ذ (خليجي، فصحى)", "th in 'think' / th in 'this'"),
    ("s / z", "ث / ذ في الكلمات الفصيحة (مصري، شامي)", "s / z"),
    ("ðˤ", "ظ، ض (خليجي)", "emphatic th"),
    ("sˤ dˤ tˤ zˤ", "ص ض ط ظ", "emphatic s, d, t, z (ˤ = emphasis)"),
    ("ħ ʕ x ɣ", "ح ع خ غ", ""),
    ("ʃ", "ش", "sh"),
    ("ɾ / r", "ر", "tap r (Egyptian) / trilled r; doubled ر is /rr/"),
    ("j / w", "ي / و", "y as in 'yes' / w"),
    ("ː", "", "marks a long vowel: /aː/ = ا, /uː/ = و"),
    ("e, ɪ, a", "حركة أداة التعريف", "article vowel: Egyptian e, Levantine and Gulf ɪ, MSA a"),
    ("-", "", "boundary after the article; not a sound"),
]


def style_guide(ws, code=None, master=False):
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 3; ws.column_dimensions["B"].width = 30; ws.column_dimensions["C"].width = 100
    r = 2
    ws.cell(r, 2, "Human evaluation of the dialectal G2P engine — annotation guide / دليل التقييم").font = Font(name=F, bold=True, size=14); r += 1
    if code:
        ws.cell(r, 2, f"Annotator code: {code}   ·   Dialect: {DIALECT_NAME[code[:3]]}   ·   كود المقيّم: {code}").font = Font(name=F, bold=True, size=12, color="1F4E78"); r += 1
    if master:
        ws.cell(r, 2, "ADJUDICATION WORKBOOK: filled by merge_annotations.py from the six annotator files, then adjudicated (see 'Adjudication').").font = Font(name=F, bold=True, color="C00000"); r += 1
    r += 1
    for k, v in EN + (ADJ if master else []):
        ws.cell(r, 2, k).font = Font(name=F, bold=True); ws.cell(r, 2).alignment = WRAP
        c = ws.cell(r, 3, v); c.font = Font(name=F); c.alignment = WRAP; r += 1
    r += 1
    ws.cell(r, 2, "بالعربي").font = Font(name=F, bold=True, size=12); r += 1
    for k, v in AR + (ADJ_AR if master else []):
        a = ws.cell(r, 2, k); a.font = Font(name=F, bold=True); a.alignment = RTL
        b = ws.cell(r, 3, v); b.font = Font(name=F); b.alignment = RTL; r += 1
    r += 1
    ws.cell(r, 2, "Legend / الألوان").font = Font(name=F, bold=True); r += 1
    for text, fill in (("Yellow = your input / أصفر = تكتب فيه", INPUT), ("Grey = locked or calculated / رمادي = مقفول أو محسوب", CALC),
                       ("Red = something missing / أحمر = فيه حاجة ناقصة", RED)):
        ws.cell(r, 2, text).fill = fill; ws.cell(r, 2).font = Font(name=F); r += 1
    r += 1
    ws.cell(r, 2, "Worked example (not part of the data) / مثال").font = Font(name=F, bold=True); r += 1
    for k, v in [("Sentence (Gulf)", "دورت عليه في جوجل"), ("Engine IPA output", "/dwrt/ /ʕljh/ /fj/ /dʒwdʒl/"),
                 ("Judgment (OK / Not OK)", "Not OK"), ("Error type", "Foreign name or loanword"), ("Wrong word", "جوجل"),
                 ("Engine IPA of that word", "/dʒwdʒl/"), ("Correct IPA", "/ɡwɡl/"),
                 ("Notes", "Google is said with /ɡ/, not /dʒ/. / جوجل بتتنطق بالـ g مش بالجيم.")]:
        ws.cell(r, 2, k).font = Font(name=F, italic=True); c = ws.cell(r, 3, v); c.font = Font(name=F, italic=True); c.alignment = WRAP; r += 1
    ws.protection.sheet = True


def symbols_sheet(wb):
    sy = wb.create_sheet("Symbols")
    sy.sheet_view.showGridLines = False
    for col, w in zip("ABC", (16, 44, 50)):
        sy.column_dimensions[col].width = w
    for j, h in enumerate(["IPA symbol", "Arabic letter(s) / الحرف", "Sound"], 1):
        c = sy.cell(1, j, h); c.font = HDR; c.fill = HFILL; c.alignment = CENTER
    for i, (a, b, c_) in enumerate(SYMBOLS, 2):
        sy.cell(i, 1, a).font = Font(name=F, size=12); sy.cell(i, 2, b).alignment = RTL; sy.cell(i, 3, c_)
        for j in (1, 2, 3):
            sy.cell(i, j).border = BOX
    sy.protection.sheet = True


def validation(ws, formula, ref, title):
    dv = DataValidation(type="list", formula1=formula, allow_blank=True, showErrorMessage=True,
                        errorStyle="stop", errorTitle=title, error="Please choose a value from the list.")
    ws.add_data_validation(dv); dv.add(ref)


def protect(ws, last_col, last):
    ws.protection.sheet = True
    ws.protection.autoFilter = False; ws.protection.sort = False; ws.protection.formatRows = False
    ws.protection.formatColumns = False
    ws.auto_filter.ref = f"A1:{last_col}{last}"


OKF = '"OK,Not OK"'
ETF = '"' + ",".join(ERROR_TYPES) + '"'

# ------------------------------------------------------------------ annotator files
for tag in ("EGY", "LEV", "GLF"):
    sub = [r for r in rows if r["Dialect"] == tag]
    for slot in "AB":
        code = f"{tag}-{slot}"
        wb = Workbook()
        style_guide(wb.active, code=code); wb.active.title = "Instructions"
        ws = wb.create_sheet("Annotation")
        cols = [("No.", 5), ("Item", 9), ("Sentence (Arabic)", 46), ("Engine IPA output", 50),
                ("Judgment (OK / Not OK)", 13), ("Error type (if Not OK)", 22), ("Wrong word (Arabic)", 16),
                ("Engine IPA of that word", 18), ("Correct IPA", 18), ("Notes", 34)]
        for j, (h, w) in enumerate(cols, 1):
            c = ws.cell(1, j, h); c.font = HDR; c.fill = HFILL; c.alignment = CENTER; c.border = BOX
            ws.column_dimensions[c.column_letter].width = w
        ws.row_dimensions[1].height = 36
        ws.freeze_panes = "E2"
        last = len(sub) + 1
        for i, rr in enumerate(sub, 2):
            for j, v in enumerate([i - 1, rr["Item"], rr["Transcript"], rr["IPA"]], 1):
                c = ws.cell(i, j, v); c.font = Font(name=F, size=12 if j == 3 else 10); c.border = BOX
                c.alignment = RTL if j == 3 else WRAP
                if j <= 2: c.fill = CALC
            for j in range(5, 11):
                c = ws.cell(i, j); c.fill = INPUT; c.border = BOX; c.font = Font(name=F, size=10)
                c.alignment = RTL if j == 7 else WRAP; c.protection = UNLOCK
        validation(ws, OKF, f"E2:E{last}", "Judgment")
        validation(ws, ETF, f"F2:F{last}", "Error type")
        for col in "EFGHI":
            cond = '$E2=""' if col == "E" else f'AND($E2="Not OK",${col}2="")'
            ws.conditional_formatting.add(f"{col}2:{col}{last}", FormulaRule(formula=[cond], fill=RED))
        ws.conditional_formatting.add(f"F2:I{last}", FormulaRule(formula=['AND($E2="OK",F2<>"")'], fill=RED))
        ws.cell(1, 5).comment = Comment("OK = consonants, definite article and written long vowels of every word are as a native speaker of this dialect would say them. Short vowels and /w/ /j/ for long vowels are NOT judged.", "G2P study")
        ws.cell(1, 6).comment = Comment("Only for Not OK: the main error. Then fill the wrong word, its engine IPA (copy from column D) and the correct IPA.", "G2P study")
        protect(ws, "J", last)
        symbols_sheet(wb)
        wb.active = 0
        wb.save(OUT / f"annotator_{code}.xlsx")

# ------------------------------------------------------------------ adjudication workbook
wb = Workbook()
style_guide(wb.active, master=True); wb.active.title = "Instructions"
ws = wb.create_sheet("Annotation")
cols = [("No.", 5), ("Item", 9), ("Dialect", 10), ("Sentence (Arabic)", 44), ("Engine IPA output", 50),
        ("A: annotator", 9), ("A: Judgment", 11), ("A: Notes", 30),
        ("B: annotator", 9), ("B: Judgment", 11), ("B: Notes", 30),
        ("Initial disagreement", 12), ("Adjudicated (if needed)", 14), ("Final: correct", 11),
        ("Error type (if Final = No)", 22), ("Wrong word (Arabic)", 16), ("Engine IPA of that word", 18), ("Correct IPA", 18),
        ("Corpus ID", 9), ("Adjudication note", 30)]
for j, (h, w) in enumerate(cols, 1):
    c = ws.cell(1, j, h); c.font = HDR; c.fill = HFILL; c.alignment = CENTER; c.border = BOX
    ws.column_dimensions[c.column_letter].width = w
ws.row_dimensions[1].height = 45
ws.freeze_panes = "F2"
last = len(rows) + 1
for i, rr in enumerate(rows, 2):
    for j, v in enumerate([i - 1, rr["Item"], DIALECT_NAME[rr["Dialect"]], rr["Transcript"], rr["IPA"]], 1):
        c = ws.cell(i, j, v); c.font = Font(name=F, size=11 if j == 4 else 10); c.border = BOX
        c.alignment = RTL if j == 4 else WRAP
    ws.cell(i, 6, f"{rr['Dialect']}-A"); ws.cell(i, 9, f"{rr['Dialect']}-B"); ws.cell(i, 19, rr["ID"])
    for j in (6, 9, 19):
        c = ws.cell(i, j); c.fill = CALC; c.border = BOX; c.font = Font(name=F, size=10)
    for j in (7, 8, 10, 11, 13, 15, 16, 17, 18, 20):
        c = ws.cell(i, j); c.fill = INPUT; c.border = BOX; c.font = Font(name=F, size=10)
        c.alignment = RTL if j == 16 else WRAP; c.protection = UNLOCK
    ws.cell(i, 12, f'=IF(OR(G{i}="",J{i}=""),"",IF(G{i}=J{i},"No","Yes"))')
    ws.cell(i, 14, f'=IF(M{i}<>"",M{i},IF(L{i}="No",IF(G{i}="OK","Yes","No"),""))')
    for j in (12, 14):
        c = ws.cell(i, j); c.fill = CALC; c.border = BOX; c.font = Font(name=F, size=10); c.alignment = CENTER
validation(ws, OKF, f"G2:G{last}", "Judgment"); validation(ws, OKF, f"J2:J{last}", "Judgment")
validation(ws, '"Yes,No"', f"M2:M{last}", "Adjudicated"); validation(ws, ETF, f"O2:O{last}", "Error type")
ws.conditional_formatting.add(f"L2:L{last}", FormulaRule(formula=['$L2="Yes"'], fill=RED))
ws.conditional_formatting.add(f"M2:M{last}", FormulaRule(formula=['AND($L2="Yes",$M2="")'], fill=RED))
for col in "OPQR":
    ws.conditional_formatting.add(f"{col}2:{col}{last}", FormulaRule(formula=[f'AND($N2="No",${col}2="")'], fill=RED))
ws.cell(1, 13).comment = Comment("Fill when 'Initial disagreement' is Yes, or when both said Not OK but for different words: the decision both annotators agree on after discussion.", "G2P study")
protect(ws, "T", last)

sm = wb.create_sheet("Summary")
sm.column_dimensions["A"].width = 30
for col in "BCDEFGH": sm.column_dimensions[col].width = 15
for j, h in enumerate(["Dialect", "Sentences", "Fully judged", "Correct (final)", "Accuracy", "Initial disagreements",
                       "Both OK (initial)", "Cohen's kappa"], 1):
    c = sm.cell(1, j, h); c.font = HDR; c.fill = HFILL; c.alignment = CENTER
A_ = f"Annotation!$C$2:$C${last}"; N_ = f"Annotation!$N$2:$N${last}"; L_ = f"Annotation!$L$2:$L${last}"
O_ = f"Annotation!$O$2:$O${last}"; G_ = f"Annotation!$G$2:$G${last}"; J_ = f"Annotation!$J$2:$J${last}"


def kappa_formula(n, dis, pa, pb):
    pe = f"({pa}*{pb}+(1-{pa})*(1-{pb}))"
    return f'=IF(OR({n}=0,1-{pe}=0),"",(({n}-{dis})/{n}-{pe})/(1-{pe}))'


for i, d in enumerate(["Egyptian", "Levantine", "Gulf"], 2):
    sm.cell(i, 1, d)
    sm.cell(i, 2, f"=COUNTIF({A_},A{i})")
    sm.cell(i, 3, f'=COUNTIFS({A_},A{i},{N_},"Yes")+COUNTIFS({A_},A{i},{N_},"No")')
    sm.cell(i, 4, f'=COUNTIFS({A_},A{i},{N_},"Yes")')
    sm.cell(i, 5, f'=IF(C{i}=0,"",D{i}/C{i})')
    sm.cell(i, 6, f'=COUNTIFS({A_},A{i},{L_},"Yes")')
    sm.cell(i, 7, f'=COUNTIFS({A_},A{i},{G_},"OK",{J_},"OK")')
    n = f'(COUNTIFS({A_},A{i},{L_},"Yes")+COUNTIFS({A_},A{i},{L_},"No"))'
    sm.cell(i, 8, kappa_formula(n, f"F{i}", f'COUNTIFS({A_},A{i},{G_},"OK",{L_},"<>")/{n}', f'COUNTIFS({A_},A{i},{J_},"OK",{L_},"<>")/{n}'))
sm.cell(5, 1, "Overall")
for j, col in zip(range(2, 8), "BCDEFG"):
    sm.cell(5, j, '=IF(C5=0,"",D5/C5)' if col == "E" else f"=SUM({col}2:{col}4)")
n = f'(COUNTIF({L_},"Yes")+COUNTIF({L_},"No"))'
sm.cell(5, 8, kappa_formula(n, "F5", f'COUNTIFS({G_},"OK",{L_},"<>")/{n}', f'COUNTIFS({J_},"OK",{L_},"<>")/{n}'))
for i in range(2, 6):
    sm.cell(i, 5).number_format = "0.00%"; sm.cell(i, 8).number_format = "0.00"
    for j in range(1, 9):
        sm.cell(i, j).font = Font(name=F, bold=(i == 5)); sm.cell(i, j).border = BOX
sm.cell(7, 1, "Error types (final = No)").font = Font(name=F, bold=True)
for k, e in enumerate(ERROR_TYPES, 8):
    sm.cell(k, 1, e).font = Font(name=F); sm.cell(k, 2, f'=COUNTIFS({N_},"No",{O_},A{k})').font = Font(name=F)
    sm.cell(k, 1).border = BOX; sm.cell(k, 2).border = BOX
sm.cell(13, 1, "Missing error type").font = Font(name=F, italic=True)
sm.cell(13, 2, f'=COUNTIFS({N_},"No",{O_},"")').font = Font(name=F, italic=True)
sm.cell(15, 1, "Accuracy = Correct (final) / Fully judged. Cohen's kappa uses the two initial judgments of the rows judged by both annotators. All cells on this sheet are calculated.").font = Font(name=F, italic=True, color="595959")
sm.protection.sheet = True
symbols_sheet(wb)
wb.active = 0
wb.save(OUT / "G2P_human_evaluation_150.xlsx")
print("saved", sorted(p.name for p in OUT.glob("*.xlsx")))
