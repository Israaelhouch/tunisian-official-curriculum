# CNP textbook chapters

Fills the `chapters` of `data/curriculum/*.json` from the official student textbooks published by the
Centre National Pédagogique (cnp.com.tn). Only chapter and lesson **names and their order** are kept;
the PDFs are deleted as soon as a book is processed.

Run every step from the repository root.

## Steps

| # | Command | Output |
|---|---------|--------|
| 1 | `python -m pipeline.cnp.crawl_catalogue` | `data/cnp/catalogue.json`: every CNP student textbook (code, title, PDF links) |
| 2 | `python -m pipeline.cnp.extract_books --batch bac` (or `3eme`, `lycee12`, `college`, `primaire`, `all`, or book codes) | `.cache/cnp/extract/<code>.json`: sommaire/فهرس pages, large-font headings, chapter markers |
| 2b | `python -m pipeline.cnp.ocr_chapter_pages CODE[:pages] ...` (weak books only) | adds `opener_pages`: full-page OCR of chapter openers, or of every page |
| 3 | `python -m pipeline.cnp.structure_books CODE ...` or `--batch bac` / `--collect BATCH_ID` (Claude API, rules in `AI_STRUCTURING_RULES.md`) | `.cache/cnp/proposed/<code>.json` for review; `--apply` writes `data/cnp/books/<code>.json` (table of contents + `notes`) |
| 3b | `data/cnp/chapter_depth.json` (reviewed by hand / with Claude) | per book tree: 1 = top-level items are chapters, 2 = themes/parts → chapters |
| 4 | `python -m pipeline.cnp.merge_chapters --all` (`--full` keeps sections and lessons) | `data/curriculum/*.json` chapters, plus the books in each file's `references` |
| 5 | `python scripts/load_curriculum.py` | PostgreSQL |

`book_mapping.py` (step 3a) says which book serves which class and subject. Books not listed are excluded on
purpose: exercise workbooks, English Activity Books, lycées/collèges pilotes editions, collèges techniques.

## What each step handles

- **Broken text layers and scans.** Many CNP books store Arabic in old fonts whose text layer is unreadable
  glyph soup, and some are pure scans; the Russian and Chinese books have broken font encodings. `extract_books`
  checks each page and OCRs it with Tesseract **in the book's language** (`LANGUAGES` in `extract_books.py`:
  `ara+fra` by default; `eng`, `deu`, `spa`, `ita`, `por`, `rus`, `chi_sim` for language textbooks, whose pages
  must contain their own alphabet). `FORCE_OCR="code ..."` forces OCR for books whose text layer is only boilerplate.
- **Weak books.** When the sommaire is an image or OCR'd badly, `ocr_chapter_pages` OCRs the chapter opening
  pages (found by font size) or, with an explicit page list, every page.
- **Step 3 is done by Claude** (`structure_books.py`: Claude Opus 5.5, structured outputs with a fixed 3-level schema, rules as a cached system prompt, Batch API for many books at half price; results are proposed for review before `--apply`). Rules: book order, max 3 levels, names exactly
  as printed in the book, never inferred from content, a preface or another book; unreadable titles get a
  positional label listed in `notes`.
- **Chapters only.** The curriculum keeps chapters (and the themes/parts grouping them), not sections, lessons or texts:
  each tree is cut at its level in `chapter_depth.json`. The full trees stay in `data/cnp/books/`.
- **Merge rules.**
  - Several volumes of a subject (tome 1 + 2) are concatenated.
  - Physique and Chimie books are grouped under "Physique" / "Chimie".
  - Multi-subject books (المواد الاجتماعية) are split with `by_subject`.
  - The collège informatique book is split per year with `by_class`.
  - Positional labels: lessons are dropped; containers are kept only when they group named children.
  - Page references such as "(ص 28-31)" are removed.

`merge_chapters --all` always rebuilds every subject from `data/cnp/books`, so it can be re-run safely
after changing `book_mapping.py` or a book file.

## Requirements

`pip install -r requirements.txt` (PyMuPDF, anthropic; step 3 needs `ANTHROPIC_API_KEY` or `ant auth login`) and the `tesseract` binary with the language data `ara fra eng deu spa ita por rus chi_sim`
(`brew install tesseract tesseract-lang` installs them all; the scripts stop with a clear message if one is missing).

## Known gaps

- No CNP textbook (so no chapters): ALGO, STI, Économie, Informatique outside collège, EPS, arts, Portugais,
  Russe at Bac, Éducation islamique / Technologie / English in primaire.
- Weakest sources (noisy scans): primaire 3ème–6ème Arabic, Maths and Éveil books, collège Arabic books.
  Each book's `notes` in `data/cnp/books/` lists what could not be read.
