"""Step 2b — re-download weak books and OCR their chapter/axis opening pages in full.

Opening pages = pages whose largest font is much bigger than the body text
(chapter and axis title pages), plus any pages given explicitly. Results are
added to .cache/cnp/extract/<code>.json as "opener_pages": [[page, text], ...]; PDFs are deleted.
Give every page (CODE:1,2,...,N) for scans whose pages carry no font sizes.

Usage: python -m pipeline.cnp.ocr_chapter_pages CODE[:p1,p2,...] ...
"""
import json, os, subprocess, sys, time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

import pymupdf

from pipeline.cnp.extract_books import book_language, norm, require_languages
from pipeline.cnp.paths import CATALOGUE, EXTRACT_DIR, PDF_DIR


def ocr_page(args):
    path, pno, langs = args
    doc = pymupdf.open(path)
    pix = doc[pno].get_pixmap(dpi=200)
    png = f"{path}.{pno}.png"
    pix.save(png)
    r = subprocess.run(["tesseract", png, "-", "-l", langs, "--psm", "4"], capture_output=True, text=True)
    os.remove(png)
    return norm(r.stdout)


def opener_pages(doc, max_pages=70):
    sizes, page_max = Counter(), {}
    for pno, page in enumerate(doc):
        biggest = 0
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if span["text"].strip():
                        sizes[round(span["size"])] += len(span["text"])
                        biggest = max(biggest, span["size"])
        page_max[pno] = biggest
    body = sizes.most_common(1)[0][0] if sizes else 10
    ranked = sorted((p for p, s in page_max.items() if s >= 1.8 * body), key=lambda p: -page_max[p])
    return sorted(ranked[:max_pages])


def main(specs):
    books = {b["code"]: b for b in json.load(open(CATALOGUE, encoding="utf-8"))}
    for spec in specs:
        code, _, explicit = spec.partition(":")
        out = EXTRACT_DIR / f"{code}.json"
        data = json.load(open(out))
        langs = book_language(code)[0]  # OCR in the book's language (ara+fra unless a language book)
        paths = []
        try:
            require_languages(langs)
            for i, url in enumerate(books[code]["pdfs"]):
                path = str(PDF_DIR / f"reocr_{code}_{i}.pdf")
                subprocess.run(["curl", "-sS", "-m", "900", "-A", "Mozilla/5.0", "-o", path, url], check=True)
                paths.append(path)
                time.sleep(2)
            jobs, offset = [], 0
            wanted = {int(p) - 1 for p in explicit.split(",") if p}
            for path in paths:
                doc = pymupdf.open(path)
                pages = set(opener_pages(doc)) | {p - offset for p in wanted if 0 <= p - offset < doc.page_count}
                jobs += [(path, p, offset) for p in sorted(pages)]
                offset += doc.page_count
                doc.close()
            with ProcessPoolExecutor(max_workers=6) as pool:
                texts = list(pool.map(ocr_page, [(path, p, langs) for path, p, _ in jobs]))
            data["opener_pages"] = [[off + p + 1, t[:2500]] for (_, p, off), t in zip(jobs, texts)]
            out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"{code} {data['title'][:40]:<40} OCR'd {len(jobs)} opening pages ({langs})", flush=True)
        except Exception as exc:
            print(f"{code} FAILED: {exc}", flush=True)
        finally:
            for p in paths:
                if os.path.exists(p):
                    os.remove(p)  # books are not kept


if __name__ == "__main__":
    main(sys.argv[1:])
