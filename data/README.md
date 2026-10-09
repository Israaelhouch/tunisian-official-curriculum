# Data

| File | Role | Edit by hand? |
|------|------|---------------|
| `curriculum/<class>.json` | **Source of truth**, one file per class (30 classes) | Yes (subjects, names), then run the export |
| `curriculum.json` | Everything in one file, generated from `curriculum/` | No: `python scripts/export_curriculum.py` |
| `CURRICULUM_NOTES.md` | What is missing (generated with `curriculum.json`) | No |
| `cnp/catalogue.json` | All official CNP student textbooks: code, title, PDF links | No: `python -m pipeline.cnp.crawl_catalogue` |
| `cnp/books/<code>.json` | One textbook's full table of contents (`toc`) + `notes` on sources and doubts | Yes, to fix a chapter; then merge + export |
| `cnp/chapter_depth.json` | Per book: depth at which chapters sit in its `toc` (1 or 2) | Yes; then merge + export |

Chapters in `curriculum/` are written by `python -m pipeline.cnp.merge_chapters --all` from `cnp/books/`:
fix a chapter in the book file, not in the class file, or the next merge will overwrite it.

## `curriculum.json`

```json
{
  "generated": "2026-10-09",
  "subjects": { "MATH": {"name_fr": "Mathématiques", "name_ar": "الرياضيات"}, "...": {} },
  "levels": [
    {
      "code": "BAC", "name_fr": "Baccalauréat (4ème année secondaire)", "name_ar": "البكالوريا ...",
      "cycle": "secondaire", "grade_number": 4,
      "sections": [
        {
          "code": "INFO", "name_fr": "Sciences de l'informatique", "name_ar": "علوم الإعلامية",
          "class_key": "bac-informatique",
          "sources": ["Décret ... 2019-1085 ...", "CNP 222472 — ... — https://www.cnp.com.tn/arabic/PDF/222472P00.pdf"],
          "subjects": [
            { "code": "MATH", "language": "fr",
              "chapters": [ {"name_fr": "Suites réelles"}, {"name_fr": "Limites de fonctions"} ] },
            { "code": "PHYS", "language": "fr",
              "chapters": [ {"name_fr": "Physique", "chapters": [
                  {"name_fr": "Évolution de systèmes électriques", "chapters": [{"name_fr": "Le condensateur ; le dipôle RC"}]} ]} ] },
            { "code": "ALLEM", "language": "de", "optional": true }
          ]
        }
      ]
    }
  ]
}
```

- A chapter has `name_fr` and/or `name_ar` (the name as printed, in its own script). Nested `chapters` are
  chapters grouped under a theme or part; leaves are the chapters.
- A subject without `chapters` has no official CNP textbook (see `CURRICULUM_NOTES.md`).
- `optional: true` = option chosen by the student (3rd language, music, arts…).

## `curriculum/<class>.json`

Same content for one class, with all fields explicit: `level`, `section`, `subjects[]` (each with `subject`,
`instruction_language`, `is_optional`, `chapters[]` where chapters have `order_index` and `children`), and
`references` (official texts and textbooks used). Validated by `models.ClassCurriculum`
(`python scripts/load_curriculum.py --dry-run`).

## Codes

**Levels** (`level.code`)

| Code | Level | | Cycle |
|------|-------|---|-------|
| `1P`–`6P` | 1ère–6ème année primaire | السنة الأولى–السادسة ابتدائي | primaire |
| `7B`–`9B` | 7ème–9ème année de base | السنة السابعة–التاسعة أساسي | preparatoire (collège) |
| `1S`, `2S`, `3S` | 1ère–3ème année secondaire | السنة الأولى–الثالثة ثانوي | secondaire (lycée) |
| `BAC` | Baccalauréat (4ème année secondaire) | البكالوريا | secondaire (lycée) |

**Sections** (`section.code`; a class = level + section, e.g. `BAC` + `INFO` = `bac-informatique.json`)

| Code | Section | | Levels |
|------|---------|---|--------|
| `TC` | Tronc commun (no specialty) | جذع مشترك | 1P–9B, 1S |
| `SPORT` | Sport | رياضة | 1S, 2S, 3S, BAC |
| `LET` | Lettres | آداب | 2S, 3S, BAC |
| `SCI` | Sciences | علوم | 2S |
| `TI` | Technologie de l'informatique | تكنولوجيا الإعلامية | 2S |
| `ECOSERV` | Économie et services | اقتصاد وخدمات | 2S |
| `ECO` | Économie et gestion | اقتصاد وتصرف | 3S, BAC |
| `INFO` | Sciences de l'informatique | علوم الإعلامية | 3S, BAC |
| `MATH` | Mathématiques | رياضيات | 3S, BAC |
| `SCEXP` | Sciences expérimentales | علوم تجريبية | 3S, BAC |
| `TECH` | Sciences techniques | العلوم التقنية | 3S, BAC |

**Subjects** (`subject.code`; full names in `curriculum.json` → `subjects`)

| Code | Subject | Code | Subject |
|------|---------|------|---------|
| `ARAB` | Arabe | `HIST` | Histoire |
| `FRAN` | Français | `GEO` | Géographie |
| `ANGL` | Anglais | `HISTGEO` | Histoire-Géographie (Bac, one exam) |
| `ALLEM` | Allemand (option) | `ISLAM` | Éducation / Pensée islamique |
| `ESPA` | Espagnol (option) | `CIVIQ` | Éducation civique |
| `ITAL` | Italien (option) | `PHILO` | Philosophie |
| `RUSSE` | Russe (option) | `ECO` | Économie |
| `CHIN` | Chinois (option) | `GEST` | Gestion |
| `PORT` | Portugais (option) | `EVEIL` | Éveil scientifique (primaire) |
| `MATH` | Mathématiques | `TECHNO` | Technologie (incl. génie mécanique / électrique) |
| `PHYS` | Sciences physiques (physique + chimie) | `EPS` | Éducation physique |
| `SVT` | Sciences de la vie et de la terre | `SPORTSPEC` | Spécialité sportive |
| `BIO` | Sciences biologiques (section Sport) | `MUSIQ` | Éducation musicale |
| `INFO` | Informatique | `ARTPL` | Arts plastiques |
| `ALGO` | Algorithmique et programmation | `THEATRE` | Éducation théâtrale |
| `STI` | Systèmes et technologies de l'informatique | | |

**Language** (`language` / `instruction_language`): `ar`, `fr`, `en`, `de`, `es`, `it`, `ru`, `zh`, `pt`.
