# Tunisian Official Curriculum

## Project Overview
A standalone dataset of the official Tunisian curriculum (levels → sections → subjects → chapters, French/Arabic),
plus the pipeline that builds it from official sources. Other projects (e.g. exam generation) consume
`data/curriculum.json`; keep this repo focused on the data and its pipeline.

## Tech Stack
- Python 3.11, Pydantic v2, SQLAlchemy 2.0, PostgreSQL (psycopg 3)
- Textbook pipeline: PyMuPDF + Tesseract OCR (per-book language: Arabic/French, English, German, Spanish, Italian, Portuguese, Russian, Chinese), structuring by Claude

## Layout
- `data/curriculum/<class>.json`: source of truth, one file per class (30 classes). See `data/README.md`.
- `data/curriculum.json` + `data/CURRICULUM_NOTES.md`: generated single-file export and gap notes.
- `data/cnp/`: CNP textbook catalogue, one file per textbook (`books/<code>.json`, full table of contents),
  `chapter_depth.json`.
- `models.py`: SQLAlchemy tables + Pydantic schemas. `scripts/`: load into PostgreSQL, export.
- `pipeline/cnp/`: textbook pipeline (see its README).
- `data/translations/en.json` + `pipeline/translate_names.py`: English machine translations (`name_en`), applied by the
  merge; never replace printed names.

## Data rules
- Subjects per class come from the official decrees (2019-1085, 2021-143); chapters only from the official
  CNP textbooks. No third-party platforms (tadris.tn was dropped).
- Names exactly as printed in the source, never inferred or guessed; unreadable titles are dropped.
- Keep chapters only (themes/parts above them allowed), not sections or lessons. No coefficients,
  weekly hours or exam durations.
- Chapters in `data/curriculum/` are generated: fix them in `data/cnp/books/` or `chapter_depth.json`,
  then run `python -m pipeline.cnp.merge_chapters --all` and `python scripts/export_curriculum.py`.

## Core Rules for Code Generation
- Data models represent the hierarchy: Level (e.g. 7ème base, Bac) -> Section (e.g. Sciences, Informatique)
  -> Subject -> Chapter.
- Bilingual French/Arabic names (`name_fr` / `name_ar`, at least one).
- Write modular, clean code with explicit typing and error handling.
