# Rebuilding the table of contents of a Tunisian CNP textbook

Used as the system prompt by `structure_books.py` (Claude API), and as instructions for an agent doing the
same work by hand.

## Input: one extract per book (`.cache/cnp/extract/<code>.json`; the PDF itself is gone)
- `title`, `targets` (which classes/subjects the book serves), `pages`.
- `front`: text of the first 14 pages, `back`: text of the last 8 pages. The sommaire / table des matières /
  فهرس is usually in one of them, often with page numbers. Some pages were OCR'd: expect OCR noise
  (wrong letters, stray Latin in Arabic, broken numbers, reversed number order).
- `headings`: large-font lines `[page, font_size, text]` in book order: chapter/theme titles and section titles.
- `markers`: lines like "Chapitre 3", "Thème 2", "Unit 4", "المحور الأول" with page numbers.
- `opener_pages` (only for weak books): full-page OCR of chapter opening pages, or of every page.

## Output
The book's table of contents as nested items `{"name": ..., "children": [...]}` (`toc`), plus `notes`:
which pages each part came from, and every doubt or positional label. Example:
```json
{"toc": [
  {"name": "Suites réelles", "children": [{"name": "Généralités"}, {"name": "Opérations sur les limites"}]},
  {"name": "Limites de fonctions", "children": []}
], "notes": "Chapters from the sommaire p.4; sections from each chapter's plan."}
```
Books bundling several subjects (المواد الاجتماعية) give one list per subject code from `targets`
(`by_subject`: HIST, GEO, CIVIQ…) instead of `toc`; each list follows the same rules.
When saved, the file `data/cnp/books/<code>.json` also gets `code`, `title` and `used_for`
(from the catalogue and `book_mapping.py`).

## Rules
1. **Order** = the book's order (sommaire order / page order). Never reorder or invent.
2. **Levels:** use what the book actually has, max 3 levels deep.
   - Themes/parts grouping chapters (Thème, Partie, Module, القسم, المحور containing chapters): theme → chapter → section.
   - Only chapters: chapter → sections (I., II., 1.1 … headings, or sub-titles in the sommaire).
   - Text anthologies (Arabic/French literature, philosophy): axis/module/محور → text or lesson titles.
     Keep the text title only (drop the author and page numbers).
   - Language textbooks (English, German…): unit/module → lesson titles.
   - If sections are not reliably recoverable, give chapters with empty children rather than guessing.
3. **Never infer a name** from the content, a preface or another book. If a title is unreadable, use a
   positional label ("المحور الثاني", "Chapitre III", "الدرس 5") and list it in notes. (The merge step drops
   positional lessons and keeps positional containers only when they group named children.)
4. **Names as printed**, in the book's language. Remove numbering prefixes ("Chapitre 3 :", "I.", "1.2",
   "المحور الأول :", "Unit 2 -"), page numbers and dotted leaders. Convert ALL CAPS to normal case.
   Fix OCR errors only when the correct word is evident (e.g. "Dérivabilité.sssss" → "Dérivabilité",
   "التتوحيدي" → "التوحيدي").
5. **Exclude non-programme items:** préface, avant-propos, mode d'emploi, sommaire, remerciements, exercices,
   QCM, vrai ou faux, corrigés, solutions, évaluation, "l'essentiel", "en savoir plus", fiche technique,
   annexes, bibliographie, index, lexique, glossaire, tableaux, authors' names, "تقديم", "فهرس", "تمارين",
   "تقييم", "إصلاح".
6. **One book only:** multi-volume books (ج1 / ج2, tome 1 / 2) and physics vs chemistry books are separate
   books; structure only the book given.
