"""Canonical source documents for the corpus.

Two independent, fixed, append-only document lists exist:

- ASCII documents: pure ASCII content, one list per ASCII_CATEGORIES
  entry. Used only under 01_ASCII.
- Shared documents: one list per SHARED_CATEGORIES entry. This is the
  "identical logical corpus" re-encoded into every core Unicode
  encoding (02_UTF8 .. 06_UTF32BE) and, where capable, into every
  legacy encoding family (07_WindowsCodePages, 08_ISO8859,
  09_EastAsian, 10_Cyrillic).

Script content design note: for scripts beyond common European
languages, documents use representative code-point samples from the
relevant Unicode block rather than hand-composed sentences. This is a
deliberate reliability choice: it guarantees every sample is genuinely
in-block and free of transcription error, which matters more for an
encoding-detector test corpus than linguistic authenticity. A few
high-frequency greetings (English/French/German/Spanish/Italian/
Portuguese/Dutch/Nordic/Polish/Czech/Slovak/Hungarian/Romanian/
Russian/Arabic/Hebrew/Vietnamese/Chinese/Japanese/Korean) are
hand-composed and were verified against unicodedata.name() during
generation.

Every document gets one stable, sequential DocumentID (DOC000001,
DOC000002, ...), assigned once by fixed position below and never
reordered - new documents may only be appended to the end of a
category's list, and categories may only be appended at the end of
ASCII_CATEGORIES / SHARED_CATEGORIES.

An optional Source/ directory next to GenerateCorpus.py lets a document
be overridden: if Source/<doc_id>.txt exists, its content (decoded as
UTF-8) replaces the built-in text below. This is entirely optional -
the generator is fully runnable with an empty Source/ directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from generator.categories import ASCII_CATEGORIES, SHARED_CATEGORIES, SharedCategory


@dataclass(frozen=True)
class Document:
    """A single canonical source document."""

    doc_id: str
    group: str            # "ASCII" or "Shared"
    category_code: str      # "" for ASCII docs, e.g. "06" for shared docs
    category_name: str       # e.g. "Programming" or "CJK"
    title: str
    text: str


# ---------------------------------------------------------------------
# ASCII-only documents (01_ASCII)
# ---------------------------------------------------------------------

_ASCII_RAW: dict[str, list[tuple[str, str]]] = {
    "Programming": [
        ("PythonSnippet", "def add(a: int, b: int) -> int:\n    return a + b\n\nprint(add(2, 3))\n"),
        ("CSnippet", "#include <stdio.h>\n\nint main(void) {\n    printf(\"Hello, world!\\n\");\n    return 0;\n}\n"),
        ("JsSnippet", "function greet(name) {\n  return `Hello, ${name}!`;\n}\nconsole.log(greet(\"World\"));\n"),
    ],
    "JSON": [
        ("SimpleObject", '{\n  "name": "test",\n  "value": 42,\n  "active": true\n}\n'),
        ("Array", '{\n  "items": [1, 2, 3, 4, 5],\n  "count": 5\n}\n'),
        ("Nested", '{\n  "user": {\n    "id": 1,\n    "roles": ["admin", "editor"]\n  }\n}\n'),
    ],
    "XML": [
        ("SimpleDoc", '<?xml version="1.0" encoding="UTF-8"?>\n<root>\n  <item id="1">Test</item>\n</root>\n'),
        ("Attributes", '<config debug="true" retries="3">\n  <path>/tmp/data</path>\n</config>\n'),
        ("Namespaces", '<root xmlns:a="urn:a" xmlns:b="urn:b">\n  <a:item>1</a:item>\n  <b:item>2</b:item>\n</root>\n'),
    ],
    "HTML": [
        ("SimplePage", "<!DOCTYPE html>\n<html>\n<head><title>Test</title></head>\n<body><p>Hello</p></body>\n</html>\n"),
        ("Table", "<table>\n  <tr><th>Name</th><th>Value</th></tr>\n  <tr><td>a</td><td>1</td></tr>\n</table>\n"),
        ("Form", '<form action="/submit" method="post">\n  <input type="text" name="q">\n</form>\n'),
    ],
    "Markdown": [
        ("Headings", "# Title\n\n## Subtitle\n\nSome *emphasis* and **bold** text.\n"),
        ("List", "- item one\n- item two\n  - nested item\n1. first\n2. second\n"),
        ("CodeBlock", "Inline `code` and a fenced block:\n\n```\nprint('hi')\n```\n"),
    ],
    "CSV": [
        ("Simple", "id,name,value\n1,alpha,10\n2,beta,20\n3,gamma,30\n"),
        ("Quoted", 'id,"description"\n1,"contains, a comma"\n2,"contains ""quotes"""\n'),
        ("Numeric", "x,y,z\n0.1,0.2,0.3\n-1,-2,-3\n1e10,2e-5,3.0\n"),
    ],
    "Logs": [
        ("Application", "2026-01-15 09:12:03 INFO  Starting service\n2026-01-15 09:12:04 WARN  Cache miss\n2026-01-15 09:12:05 ERROR Connection refused\n"),
        ("Access", '127.0.0.1 - - [15/Jan/2026:09:12:03] "GET /index.html HTTP/1.1" 200 512\n'),
        ("Syslog", "Jan 15 09:12:03 host sshd[1234]: Accepted publickey for user\n"),
    ],
    "Config": [
        ("Ini", "[server]\nhost = 0.0.0.0\nport = 8080\n\n[logging]\nlevel = INFO\n"),
        ("Env", "APP_NAME=demo\nAPP_ENV=production\nDEBUG=false\nMAX_CONNECTIONS=100\n"),
        ("Yaml", "server:\n  host: 0.0.0.0\n  port: 8080\nlogging:\n  level: INFO\n"),
    ],
    "RandomASCII": [
        ("Gibberish1", "kx7 qw2 zt9 vb4 mn8 pl3 rd6 fg1\nhj5 wc0 ey4 ua8 io2 sk7 nt3\n"),
        ("Gibberish2", "The quick brown fox jumps over the lazy dog 0123456789.\n"),
        ("Punctuation", "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~\n"),
    ],
}


# ---------------------------------------------------------------------
# Shared documents (identical logical corpus across Unicode encodings)
# ---------------------------------------------------------------------

_LATIN_RAW: list[tuple[str, str]] = [
        ('English', 'Hello, how are you today?\nThe quick brown fox jumps over the lazy dog.\n'),
        ('French', 'Le café est prêt. Voilà une crème brûlée.\nÀ bientôt, mon ami!\n'),
        ('German', 'Grüße aus München! Die Straße ist schön.\n'),
        ('Spanish', '¿Cómo estás? Mañana iré al parque.\n'),
        ('Italian', 'Buongiorno! Come stai oggi?\nLa città è molto bella.\n'),
        ('Portuguese', 'A criação começou ontem à noite.\n'),
        ('Dutch', 'Goedemorgen! Hoe gaat het met je?\n'),
        ('Swedish', 'Hej! Hur mår du idag?\n'),
        ('Norwegian', 'Hei! Hvordan har du det?\n'),
        ('Danish', 'Hej! Hvordan går det?\n'),
        ('Finnish', 'Hei! Mitä kuuluu?\n'),
        ('Polish', 'Cześć! Dziękuję bardzo za pomoc.\n'),
        ('Czech', 'Ahoj! Jak se máš dnes?\n'),
        ('Slovak', 'Ahoj! Ako sa máš?\n'),
        ('Hungarian', 'Szia! Hogy vagy ma?\n'),
        ('Romanian', 'Bună! Ce mai faci astăzi?\n'),
]

_CYRILLIC_RAW: list[tuple[str, str]] = [
        ('Russian', 'Привет! Как дела?\n'),
        ('Ukrainian_Sample', 'ЀЁЂЃЄЅІЇЈЉЊЋЌЍЎЏАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧ\n'),
        ('Serbian_Sample', 'АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежз\n'),
        ('Bulgarian_Sample', 'абвгдежзийклмнопрстуфхцчшщъыьэюяѐёђѓєѕії\n'),
]

_RTL_RAW: list[tuple[str, str]] = [
        ('Arabic', 'مرحبا بالعالم!\n'),
        ('Hebrew', 'שלום עולם!\n'),
        ('Persian_Sample', 'ؠءآأؤإئابةتثجحخدذرزسشصضطظعغػؼؽ\n'),
        ('Urdu_Sample', 'ٰٱٲٳٴٵٶٷٸٹٺٻټٽپٿڀځڂڃڄڅچڇڈډڊڋڌڍ\n'),
        ('BiDiMixture', '\u200eEnglish then مرحبا بالعالم! then שלום עולם! then English\u200e\n'),
]

_INDIC_RAW: list[tuple[str, str]] = [
        ('Hindi_Sample', 'अआइईउऊऋऌऍऎएऐऑऒओऔकखगघङचछजझञटठडढ\n'),
        ('Bengali_Sample', 'অআইঈউঊঋঌ\u098d\u098eএঐ\u0991\u0992ওঔকখগঘঙচছজঝঞটঠডঢ\n'),
        ('Tamil_Sample', 'அஆஇஈஉஊ\u0b8b\u0b8c\u0b8dஎஏஐ\u0b91ஒஓஔக\u0b96\u0b97\u0b98ஙச\u0b9bஜ\u0b9dஞட\u0ba0\u0ba1\u0ba2\n'),
        ('Telugu_Sample', 'అఆఇఈఉఊఋఌ\u0c0dఎఏఐ\u0c11ఒఓఔకఖగఘఙచఛజఝఞటఠడఢ\n'),
        ('Kannada_Sample', 'ಅಆಇಈಉಊಋಌ\u0c8dಎಏಐ\u0c91ಒಓಔಕಖಗಘಙಚಛಜಝಞಟಠಡಢ\n'),
        ('Malayalam_Sample', 'അആഇഈഉഊഋഌ\u0d0dഎഏഐ\u0d11ഒഓഔകഖഗഘങചഛജഝഞടഠഡഢ\n'),
]

_SEA_RAW: list[tuple[str, str]] = [
        ('Thai_Sample', 'กขฃคฅฆงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพ\n'),
        ('Lao_Sample', 'ກຂ\u0e83ຄ\u0e85ຆງຈຉຊ\u0e8bຌຍຎຏຐຑຒຓດຕຖທຘນບປຜຝພ\n'),
        ('Khmer_Sample', 'កខគឃងចឆជឈញដឋឌឍណតថទធនបផពភមយរលវឝ\n'),
        ('Burmese_Sample', 'ကခဂဃငစဆဇဈဉညဋဌဍဎဏတထဒဓနပဖဗဘမယရလဝ\n'),
        ('Vietnamese', 'Xin chào! Bạn có khỏe không?\n'),
]

_CJK_RAW: list[tuple[str, str]] = [
        ('ChineseSimplified', '你好，世界！\n'),
        ('ChineseTraditional', '你好，世界！\n'),
        ('Japanese', 'こんにちは、世界。\n'),
        ('Korean', '안녕하세요! 세계\n'),
]

_SUPPLEMENTARY_RAW: list[tuple[str, str]] = [
        ('EgyptianHieroglyphs', '𓀀𓀁𓀂𓀃𓀄𓀅𓀆𓀇\n'),
        ('AegeanAndCypriot_LinearB_Cypriot', '𐀀𐀁𐀂𐀃𐀄𐀅𐠀𐠁𐠂𐠃𐠄𐠅\n'),
        ('ItalicRunicGlagolitic_OldItalic_Runic_Glagolitic', '𐌀𐌁𐌂𐌃𐌄𐌅ᚠᚡᚢᚣᚤᚥⰀⰁⰂⰃⰄⰅ\n'),
        ('GermanicScripts_Gothic_Deseret_Osmanya', '𐌰𐌱𐌲𐌳𐌴𐌵𐐀𐐁𐐂𐐃𐐄𐐅𐒀𐒁𐒂𐒃𐒄𐒅\n'),
        ('SemiticAncient_Phoenician_ImperialAramaic_OldTurkic', '𐤀𐤁𐤂𐤃𐤄𐤅𐡀𐡁𐡂𐡃𐡄𐡅𐰀𐰁𐰂𐰃𐰄𐰅\n'),
        ('PersianAvestan_OldPersian_Avestan', '𐎠𐎡𐎢𐎣𐎤𐎥𐬀𐬁𐬂𐬃𐬄𐬅\n'),
        ('AnatolianSeals_Lycian_Carian', '𐊀𐊁𐊂𐊃𐊄𐊅𐊠𐊡𐊢𐊣𐊤𐊥\n'),
        ('EastAsianHistoric_Cuneiform_Tangut_Nushu_Brahmi', '𒀀𒀁𒀂𒀃𒀄𗀀𗀁𗀂𗀃𗀄𛅰𛅱𛅲𛅳𛅴𑀀𑀁𑀂𑀃𑀄\n'),
]

_MATHEMATICS_RAW: list[tuple[str, str]] = [
        ('SetTheory', '∀x ∈ ℕ, x ≥ 0\n∃y ∈ ℤ : y < 0\nA ∪ B ∩ C\n'),
        ('Calculus', '∫₀¹ x² dx = 1/3\nd/dx (sin x) = cos x\n'),
        ('Comparisons', 'a ≠ b, a ≤ b, a ≥ b\n√2 ≈ 1.41421\n'),
        ('Logic', 'p ∧ q → r\np ∨ ¬q\np ↔ q\n'),
        ('MathAlphanumeric', '𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉\n'),
]

_EMOJI_RAW: list[tuple[str, str]] = [
        ('Basic', '😀 😁 🚀 🌍\n'),
        ('ZwjFamily', '👨\u200d👩\u200d👧\u200d👦\n'),
        ('Flags', '🇺🇸 🇯🇵\n'),
        ('SkinTones', '👍🏻 👍🏿\n'),
        ('VariationSelectors', '❤️ plain: ❤\n'),
]

_UNICODE_MISC_RAW: list[tuple[str, str]] = [
        ('Greek', 'Γειά σου!\n'),
        ('CombiningMarks', 'é à ñ ö\ná̂̃̄̅̆̇̈̉\n'),
        ('InvisibleCharacters', 'zero-width-space:[\u200b] zwj:[\u200d] zwnj:[\u200c] word-joiner:[\u2060]\n'),
        ('FullwidthForms', 'ＡＢＣＤＥＦＧＨＩＪ\n'),
        ('BoxDrawing', '─━│┃┄┅┆┇┈┉\n'),
        ('Braille', '⠀⠁⠂⠃⠄⠅⠆⠇⠈⠉\n'),
        ('PlayingCards', '🂡🂢🂣🂤\n'),
        ('ChessSymbols', '♔♕♖♗♘♙♚♛♜♝♞♟\n'),
        ('CurrencySymbols', '$ € £ ¥ ₽ ₹ ₩\n'),
]

# Maps each SharedCategory name to its raw document list, in the fixed
# SHARED_CATEGORIES order (see generator/categories.py).
_SHARED_RAW: dict[str, list[tuple[str, str]]] = {
    "Latin": _LATIN_RAW,
    "Cyrillic": _CYRILLIC_RAW,
    "RTL": _RTL_RAW,
    "Indic": _INDIC_RAW,
    "SoutheastAsian": _SEA_RAW,
    "CJK": _CJK_RAW,
    "SupplementaryPlanes": _SUPPLEMENTARY_RAW,
    "Mathematics": _MATHEMATICS_RAW,
    "Emoji": _EMOJI_RAW,
    "UnicodeMisc": _UNICODE_MISC_RAW,
}


def _build_documents() -> list[Document]:
    """Assign stable sequential DocumentIDs to every raw document.

    Order: all ASCII categories (in ASCII_CATEGORIES order) first, then
    all shared categories (in SHARED_CATEGORIES order). Both orders are
    fixed and append-only.
    """
    documents: list[Document] = []
    counter = 1

    for category in ASCII_CATEGORIES:
        for title, text in _ASCII_RAW.get(category, []):
            doc_id = f"DOC{counter:06d}"
            documents.append(Document(
                doc_id=doc_id, group="ASCII", category_code="", category_name=category,
                title=title, text=text,
            ))
            counter += 1

    for shared_category in SHARED_CATEGORIES:
        for title, text in _SHARED_RAW.get(shared_category.name, []):
            doc_id = f"DOC{counter:06d}"
            documents.append(Document(
                doc_id=doc_id, group="Shared", category_code=shared_category.code,
                category_name=shared_category.name, title=title, text=text,
            ))
            counter += 1

    return documents


def load_documents(source_dir: Path) -> list[Document]:
    """Build the full document list, applying Source/ overrides if present.

    If Source/<doc_id>.txt exists it replaces the built-in text for
    that document (decoded as UTF-8, universal newlines normalized to
    '\\n'). Missing or empty Source/ directory is completely normal.
    """
    documents = _build_documents()
    if not source_dir.is_dir():
        return documents

    overridden: list[Document] = []
    for doc in documents:
        override_path = source_dir / f"{doc.doc_id}.txt"
        if override_path.is_file():
            raw = override_path.read_text(encoding="utf-8")
            normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
            doc = Document(
                doc_id=doc.doc_id, group=doc.group, category_code=doc.category_code,
                category_name=doc.category_name, title=doc.title, text=normalized,
            )
        overridden.append(doc)
    return overridden


def document_count() -> int:
    """Total number of canonical documents (for sanity checks/logging)."""
    return len(_build_documents())
