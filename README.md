# Tunisian Official Curriculum

Every class of the Tunisian school system, its official subjects (named in French and Arabic) and their
chapters (as printed in the official textbooks), in one JSON file. From 1ère primaire to every Bac section.


|                      | Classes | Subjects | Chapters  |
| -------------------- | ------- | -------- | --------- |
| Primaire             | 6       | 61       | 474       |
| Collège              | 3       | 48       | 312       |
| Lycée (all sections) | 21      | 333      | 2,106     |
| **Total**            | **30**  | **442**  | **2,892** |


## Data structure

```
level (BAC)  →  section (INFO)  →  subject (MATH)  →  chapters
```

```json
{
  "subjects": { "MATH": { "name_fr": "Mathématiques", "name_ar": "الرياضيات", "name_en": "Mathematics" } },
  "levels": [{
    "code": "BAC", "name_fr": "Baccalauréat", "name_ar": "البكالوريا", "cycle": "secondaire",
    "sections": [{
      "code": "INFO", "name_fr": "Sciences de l'informatique", "name_ar": "علوم الإعلامية",
      "subjects": [
        { "code": "MATH", "language": "fr",
          "chapters": [ { "name_fr": "Suites réelles", "name_en": "Real sequences" }, { "name_fr": "Limites de fonctions", "name_en": "Limits of functions" } ] },
        { "code": "PHYS", "language": "fr",
          "chapters": [ { "name_fr": "Physique", "chapters": [
              { "name_fr": "Ondes", "chapters": [ { "name_fr": "Ondes mécaniques progressives" } ] } ] } ] },
        { "code": "ALLEM", "language": "de", "optional": true }
      ]
    }]
  }]
}
```

- **Names** are in `name_fr` and/or `name_ar`, as printed in the source; `name_en` is an English machine translation.
- **Nested** `chapters` group chapters under a theme (Physique → Ondes → Ondes mécaniques progressives); the innermost items are the chapters.
- `optional: true` marks an option the student chooses (3rd language, music, arts).
- **No** `chapters` means there is no official textbook for that subject.



## Use it

```python
import json
data = json.load(open("data/curriculum.json"))
bac = next(l for l in data["levels"] if l["code"] == "BAC")
info = next(s for s in bac["sections"] if s["code"] == "INFO")
math = next(s for s in info["subjects"] if s["code"] == "MATH")
print([c["name_fr"] for c in math["chapters"]])   # ['Suites réelles', 'Limites de fonctions', ...]
```

Format and codes: [data/README.md](data/README.md) · What is missing: [data/CURRICULUM_NOTES.md](data/CURRICULUM_NOTES.md)

## Sources

- **Subjects per class:** decrees 2019-1085 and 2021-143 (official timetables).
- **Chapters:** the official CNP textbooks, names exactly as printed. Subjects without a CNP textbook
(EPS, arts, ALGO/STI…) have no chapters.



## How it was built

A pipeline ([pipeline/cnp/](pipeline/cnp/README.md)) reads 180+ CNP textbooks, many of them scans or PDFs with
broken Arabic fonts:

1. **Extract** the table-of-contents pages, with OCR (Tesseract, in the book's language) where the text is unreadable.
2. **Structure** each book's table of contents with Claude, under strict rules: book order, names as printed,
  never guessed. Unreadable titles are dropped, not invented.
3. **Merge** the chapters into one file per class, validated with Pydantic.

**Limits:** some primaire chapters are missing (unreadable scans); Chinese and Russian titles were decoded from
broken font encodings and deserve a native check.

## Repository

```
data/curriculum.json        everything in one file
data/*.csv                  the same as flat tables (one row per chapter / per class subject)
data/curriculum/            one file per class (source of truth)
data/translations/en.json   English machine translations of all names
data/cnp/                   textbook catalogue and per-book tables of contents
models.py                   Pydantic schemas + SQLAlchemy tables
scripts/                    load into PostgreSQL, export curriculum.json
pipeline/cnp/               the textbook pipeline
pipeline/translate_names.py English translation of new names (Claude)
```

```bash
pip install -r requirements.txt                    # Python 3.10+
python scripts/load_curriculum.py --dry-run        # validate
python scripts/export_curriculum.py                # rebuild data/curriculum.json
```



## License

Code: [MIT](LICENSE). Data (`data/`): [CC BY 4.0](data/LICENSE.md). Curriculum facts come from the Tunisian
Ministry of Education and the CNP textbooks, which are referenced, not reproduced.