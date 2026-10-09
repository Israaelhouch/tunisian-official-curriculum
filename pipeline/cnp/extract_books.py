"""Step 2 — download each CNP book, extract table-of-contents material, delete the PDF.

Output: .cache/cnp/extract/<code>.json with
  - front / back: text of the first 14 and last 8 pages (sommaire / فهرس usually live there)
  - headings: large-font lines (>= 1.25 x body size) with page numbers, in book order
  - markers: lines that look like "Chapitre 3", "Thème 2", "Unit 4"...
Pages are read from the PDF text layer when it is usable. Scanned pages, and pages whose text layer is
broken (legacy Arabic fonts, or a language book whose letters are not in its own alphabet), are OCR'd
instead, decided page by page, with Tesseract in the book's language (see LANGUAGES).
FORCE_OCR="code ..." forces OCR for books whose text layer is only boilerplate.

Usage: python -m pipeline.cnp.extract_books CODE [CODE ...]
       python -m pipeline.cnp.extract_books --batch bac|3eme|lycee12|college|primaire|all
Requires the `tesseract` binary with the languages in LANGUAGES (ara, fra, eng, deu, spa, ita, por, rus, chi_sim).
"""
import json, os, re, subprocess, sys, tempfile, time, unicodedata
from collections import Counter
import pymupdf

from pipeline.cnp.book_mapping import MAP, batch
from pipeline.cnp.paths import CATALOGUE, EXTRACT_DIR, PDF_DIR

MARKER = re.compile(r"^\s*(chapitre|chap\.|thème|theme|partie|module|unité|unit|lesson|leçon|séquence|kapitel|"
                    r"lektion|unidad|unità|lezione|الفصل|المحور|الوحدة|الباب|الجزء|الدرس|المجال|المحطة|الموضوع|القسم)\b",
                    re.I)
ARABIC = re.compile(r"[؀-ۿ]")
LETTER = re.compile(r"[^\W\d_]")
SOUP = re.compile(r"[À-ɏ‘-›∀-⋿°«»¬¿μƒ∏∫≤≥ﬁﬂ]")
LATIN = re.compile(r"[A-Za-zÀ-ɏ]")
CYRILLIC = re.compile(r"[Ѐ-ӿ]")
CJK = re.compile(r"[一-鿿]")

# Foreign-language textbooks: Tesseract languages + the alphabet their pages must contain.
# Every other book (Arabic, French, sciences, humanities) is Arabic/French.
DEFAULT_LANGUAGE = ("ara+fra", None)
LANGUAGES = {
    "ANGL": ("eng", LATIN), "ALLEM": ("deu", LATIN), "ESPA": ("spa", LATIN), "ITAL": ("ita", LATIN),
    "PORT": ("por", LATIN), "RUSSE": ("rus", CYRILLIC), "CHIN": ("chi_sim+eng", CJK),
}


def book_language(code: str):
    """(tesseract languages, expected alphabet or None) for a book, from the subject it serves."""
    subjects = {subj for _, subj in MAP.get(code, [])}
    profiles = {LANGUAGES[s] for s in subjects if s in LANGUAGES}
    return profiles.pop() if len(profiles) == 1 and len(subjects) == 1 else DEFAULT_LANGUAGE


def require_languages(langs: str) -> None:
    out = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout.split()
    missing = [lang for lang in langs.split("+") if lang not in out]
    if missing:
        raise RuntimeError(f"Tesseract language data missing: {', '.join(missing)} "
                           "(macOS: brew install tesseract-lang)")


def norm(text: str) -> str:
    """NFKC turns Arabic presentation forms (ﻛﺘﺎﺏ) into regular letters (كتاب)."""
    return re.sub(r"[ \t]+", " ", unicodedata.normalize("NFKC", text)).strip()


def garbled(text: str, alphabet=None) -> bool:
    """Broken text layer. Arabic/French books: legacy-font Arabic (few Arabic letters, many accented-Latin /
    symbol glyphs). Language books: too few letters of the book's own alphabet."""
    letters = len(LETTER.findall(text))
    if letters < 4:
        return False
    if alphabet is not None:
        return len(alphabet.findall(text)) < 0.3 * letters
    return len(ARABIC.findall(text)) < 0.3 * letters and len(SOUP.findall(text)) > 0.25 * letters


def ocr(pix, psm: int, langs: str = DEFAULT_LANGUAGE[0]) -> str:
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        pix.save(f.name)
        r = subprocess.run(["tesseract", f.name, "-", "-l", langs, "--psm", str(psm)],
                           capture_output=True, text=True)
    return norm(r.stdout)


FORCE_OCR = set(os.environ.get("FORCE_OCR", "").split())  # books whose text layer is only boilerplate


def page_text(doc, i, force=False, language=DEFAULT_LANGUAGE):
    langs, alphabet = language
    text = norm(doc[i].get_text())
    if force or garbled(text, alphabet) or len(text) < 30:  # broken text layer, or a scan with none
        return ocr(doc[i].get_pixmap(dpi=200), psm=4, langs=langs), True
    return text, False


def extract(pdf_paths, force_ocr=False, language=DEFAULT_LANGUAGE):
    langs, alphabet = language
    front, back, headings, markers, pages, ocr_pages = [], [], [], [], 0, 0
    for path in pdf_paths:
        doc = pymupdf.open(path)
        sizes, lines = Counter(), []
        for pno, page in enumerate(doc):
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    text = norm(" ".join(s["text"] for s in line["spans"]))
                    if not text:
                        continue
                    size = round(max(s["size"] for s in line["spans"]), 1)
                    sizes[size] += len(text)
                    lines.append((pages + pno + 1, size, text, pno, line["bbox"]))
        body = sizes.most_common(1)[0][0] if sizes else 10
        prev, found = None, []
        for p, size, text, pno, bbox in lines:
            if size >= body * 1.25 and len(text) > 2 and re.search(r"\w", text):
                if prev and prev[0] == p and abs(prev[1] - size) < 0.6 and len(prev[2]) < 120:
                    prev[2] += " " + text  # multi-line title
                    prev[4] = pymupdf.Rect(prev[4]) | pymupdf.Rect(bbox)
                else:
                    prev = [p, size, text, pno, pymupdf.Rect(bbox)]
                    found.append(prev)
            if MARKER.match(text) and len(text) < 140 and not garbled(text, alphabet):
                markers.append([p, text])
        raw_counts = Counter(h[2] for h in found)
        kept = [h for h in found if raw_counts[h[2]] <= 3]  # drop running headers / rubric names
        for h in kept:
            if garbled(h[2], alphabet) and len(h[2]) < 200:
                clip = h[4] + (-8, -6, 8, 6)
                h[2] = ocr(doc[h[3]].get_pixmap(dpi=220, clip=clip), psm=7, langs=langs) or h[2]
        headings += [h[:3] for h in kept]
        n = doc.page_count
        for target, rng in ((front, range(min(14, n))), (back, range(max(14, n - 8), n))):
            for i in rng:
                text, used = page_text(doc, i, force_ocr, language)
                ocr_pages += used
                target.append(f"[p{pages + i + 1}] {text}")
        pages += n
        doc.close()
    clip = lambda texts: "\n".join(re.sub(r"\n\s*\n+", "\n", t)[:3500] for t in texts)
    return {"pages": pages, "ocr_pages": ocr_pages, "front": clip(front), "back": clip(back),
            "headings": [[p, s, t[:160]] for p, s, t in headings if not garbled(t, alphabet)][:700],
            "markers": markers[:400]}


def main(codes):
    books = {b["code"]: b for b in json.load(open(CATALOGUE, encoding="utf-8"))}
    for code in codes:
        out = EXTRACT_DIR / f"{code}.json"
        if os.path.exists(out):
            print(code, "already extracted", flush=True)
            continue
        book = books[code]
        language = book_language(code)
        paths = []
        try:
            require_languages(language[0])
            for i, url in enumerate(book["pdfs"]):
                path = str(PDF_DIR / f"{code}_{i}.pdf")
                subprocess.run(["curl", "-sS", "-m", "900", "-A", "Mozilla/5.0", "-o", path, url], check=True)
                paths.append(path)
                time.sleep(2)
            size = sum(os.path.getsize(p) for p in paths)
            data = extract(paths, force_ocr=code in FORCE_OCR, language=language)
        except Exception as exc:  # keep going; the book can be retried later
            print(f"{code} FAILED: {exc}", flush=True)
            continue
        finally:
            for p in paths:
                if os.path.exists(p):
                    os.remove(p)  # books are not kept
        data.update(code=code, title=book["title"], targets=MAP[code], pdfs=book["pdfs"], ocr_languages=language[0])
        out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{code} {book['title'][:40]:<40} {size / 1e6:6.1f} MB {data['pages']:>4} p  "
              f"ocr pages {data['ocr_pages']:>2}  {len(data['headings']):>3} headings  "
              f"{len(data['markers']):>3} markers", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    main(batch(args[1]) if args[:1] == ["--batch"] else args)
