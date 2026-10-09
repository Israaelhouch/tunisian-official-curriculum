---
license: cc-by-4.0
pretty_name: Tunisian Official Curriculum
language:
  - ar
  - fr
  - en
  - es
  - zh
  - it
  - de
  - ru
tags:
  - education
  - curriculum
  - tunisia
  - edtech
  - arabic
  - french
size_categories:
  - 1K<n<10K
configs:
  - config_name: chapters
    data_files: curriculum_chapters.csv
    default: true
  - config_name: subjects
    data_files: curriculum_subjects.csv
---

# Tunisian Official Curriculum

Every class of the Tunisian school system (1ère primaire → every Bac section), its official subjects and
their chapters, as clean tables. Subjects are named in French and Arabic; chapters are given exactly as
printed in the official CNP textbooks. Every name also has an English machine translation (`*_en` columns).

| | Classes | Subjects | Chapters |
|---|---|---|---|
| Primaire | 6 | 61 | 474 |
| Collège | 3 | 48 | 312 |
| Lycée (all sections) | 21 | 333 | 2,106 |
| **Total** | **30** | **442** | **2,892** |

## Files

| File | Rows | One row per |
|---|---|---|
| `curriculum_chapters.csv` | 2,892 | chapter |
| `curriculum_subjects.csv` | 442 | subject of a class (including the 153 subjects with no textbook, `chapter_count = 0`) |
| `curriculum.json` | – | the same data as a nested tree: levels → sections → subjects → chapters |

## Columns

| Column | Meaning | Example |
|---|---|---|
| `cycle` | `primaire`, `preparatoire` (collège) or `secondaire` (lycée) | `secondaire` |
| `level_code`, `level_fr`, `level_ar` | school year | `BAC`, Baccalauréat, البكالوريا |
| `section_code`, `section_fr`, `section_ar` | stream (`TC` = no specialty) | `INFO`, Sciences de l'informatique |
| `class_key` | level + section, unique per class | `bac-informatique` |
| `subject_code`, `subject_fr`, `subject_ar` | official subject | `MATH`, Mathématiques, الرياضيات |
| `language` | teaching language of the subject (ISO 639-1) | `fr` |
| `optional` | option chosen by the student (3rd language, music, arts) | `False` |
| `theme` | groupings above the chapter, joined by ` > ` (empty if none) | `Physique > Ondes` |
| `chapter_order` | position of the chapter within its subject (book order) | `3` |
| `chapter` | chapter name, as printed in the textbook | `Suites réelles` |
| `level_en`, `section_en`, `subject_en`, `theme_en`, `chapter_en` | English machine translation of the names | `Real sequences` |
| `chapter_count` | (subjects file) number of chapters | `13` |

Chapters by teaching language: Arabic 1,222 · French 944 · English 246 · Spanish 156 · Chinese 126 ·
Italian 72 · German 66 · Russian 60.

## Example

```python
import pandas as pd

chapters = pd.read_csv("curriculum_chapters.csv")
bac_info_math = chapters[(chapters.class_key == "bac-informatique") & (chapters.subject_code == "MATH")]
print(bac_info_math.chapter.tolist())   # ['Suites réelles', 'Limites de fonctions', ...]
```

## Sources

- **Subjects per class:** Tunisian government decrees 2019-1085 and 2021-143 (official weekly timetables).
- **Chapters:** the official student textbooks of the Centre National Pédagogique (CNP, cnp.com.tn).
  Each book's table of contents was extracted (OCR for scans and legacy-font Arabic PDFs) and structured
  with Claude under strict rules: book order, names exactly as printed, never guessed; unreadable titles
  were dropped rather than invented.

The textbooks themselves are not included, only facts about them (subject lists and chapter titles).

## Limitations

- Subjects without an official CNP textbook have no chapters (EPS, arts, ALGO/STI, Économie…).
- Some primaire chapters are missing where the textbook scans were unreadable.
- Chinese and Russian titles were decoded from broken font encodings and deserve a native check.
- Chapter names are in the language printed in the book. The `*_en` columns are machine translations (Claude),
  not official translations; specialised terms may have more usual English equivalents.

## Source code and updates

Built and maintained at https://github.com/Israaelhouch/tunisian-official-curriculum (pipeline, per-class
JSON files, PostgreSQL loader). That repository is the source of truth; this dataset is a published copy.

## License and citation

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): free to share and adapt with attribution.

> Tunisian Official Curriculum dataset, by Israaelhouch (2026), CC BY 4.0.
> https://github.com/Israaelhouch/tunisian-official-curriculum
