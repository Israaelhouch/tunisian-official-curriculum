"""Bundle data/curriculum/*.json into one readable file, plus brief notes on what is missing.

Outputs (data/):
  curriculum.json       levels -> sections -> subjects -> chapters, with a subject catalogue
  CURRICULUM_NOTES.md   gaps: subjects without chapters, dropped unreadable titles, positional labels
  curriculum_chapters.csv   one row per chapter (flat table for Kaggle / Hugging Face / spreadsheets)
  curriculum_subjects.csv   one row per class subject, including subjects without chapters
  curriculum_objectives.csv one row per learning objective of the official programmes (data/programmes/)

The class files stay the source of truth: re-run this after any change.
Usage: python scripts/export_curriculum.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from models import ClassCurriculum  # noqa: E402
from pipeline.cnp.book_mapping import MAP  # noqa: E402
from pipeline.cnp.merge_chapters import PLACEHOLDER, clean, cut  # noqa: E402
from pipeline.cnp.paths import CHAPTER_DEPTH, CURRICULUM_DIR, BOOKS_DIR  # noqa: E402

OUT_JSON = ROOT / "data" / "curriculum.json"
OUT_NOTES = ROOT / "data" / "CURRICULUM_NOTES.md"
OUT_CHAPTERS_CSV = ROOT / "data" / "curriculum_chapters.csv"
OUT_SUBJECTS_CSV = ROOT / "data" / "curriculum_subjects.csv"
OUT_OBJECTIVES_CSV = ROOT / "data" / "curriculum_objectives.csv"
CLASS_COLUMNS = ["cycle", "level_code", "level_fr", "level_ar", "level_en",
                 "section_code", "section_fr", "section_ar", "section_en",
                 "class_key", "subject_code", "subject_fr", "subject_ar", "subject_en", "language", "optional"]
CYCLE_LABEL = {"primaire": "Primaire", "preparatoire": "Collège (enseignement de base)",
               "secondaire": "Lycée (secondaire)"}


def name(node: Any) -> dict[str, str]:
    return {k: v for k, v in (("name_fr", node.name_fr), ("name_ar", node.name_ar), ("name_en", node.name_en)) if v}


def chapter(node: Any) -> dict[str, Any]:
    out: dict[str, Any] = name(node)
    if node.children:
        out["chapters"] = [chapter(c) for c in node.children]
    return out


def leaves(nodes: list[Any]) -> int:
    return sum(leaves(n.children) if n.children else 1 for n in nodes)


def load_classes() -> list[tuple[str, ClassCurriculum]]:
    classes = [(p.stem, ClassCurriculum.model_validate_json(p.read_text(encoding="utf-8")))
               for p in CURRICULUM_DIR.glob("*.json")]
    return sorted(classes, key=lambda kc: (kc[1].level.display_order, kc[1].section.code))


def build_json(classes: list[tuple[str, ClassCurriculum]]) -> dict[str, Any]:
    catalogue: dict[str, dict[str, str]] = {}
    levels: dict[str, dict[str, Any]] = {}
    for key, cur in classes:
        lvl = levels.setdefault(cur.level.code, {
            "code": cur.level.code, **name(cur.level), "cycle": cur.level.cycle.value,
            "grade_number": cur.level.grade_number, "sections": [],
        })
        subjects = []
        for s in cur.subjects:
            catalogue[s.subject.code] = name(s.subject)
            entry: dict[str, Any] = {"code": s.subject.code, "language": s.instruction_language.value}
            if s.is_optional:
                entry["optional"] = True
            if s.chapters:
                entry["chapters"] = [chapter(c) for c in s.chapters]
            if s.programme:
                entry["programme"] = s.programme.model_dump(exclude_none=True)
            subjects.append(entry)
        lvl["sections"].append({
            "code": cur.section.code, **name(cur.section), "class_key": key,
            "sources": cur.references, "subjects": subjects,
        })
    return {
        "generated": date.today().isoformat(),
        "description": "Official Tunisian curriculum: levels -> sections -> subjects -> chapters. Subjects per "
                       "class from decrees 2019-1085 / 2021-143; chapters from the official CNP textbooks; "
                       "`programme` = learning objectives from the Ministry's official programmes (verbatim). "
                       "See CURRICULUM_NOTES.md for gaps.",
        "subjects": dict(sorted(catalogue.items())),
        "levels": list(levels.values()),
    }


def is_placeholder(label: str) -> bool:
    return bool(PLACEHOLDER.search(label) or PLACEHOLDER.search(clean(label)))


def missing_chapters() -> dict[tuple[str, str], int]:
    """Unreadable titles at chapter level (cut at chapter_depth.json), per (class, subject)."""
    levels = json.loads(CHAPTER_DEPTH.read_text(encoding="utf-8"))

    def count(items: list[dict]) -> int:  # unreadable leaves = chapters that could not be named
        return sum(count(i["children"]) if i["children"] else is_placeholder(i["name"]) for i in items)

    out: dict[tuple[str, str], int] = defaultdict(int)
    for code, pairs in MAP.items():
        data = json.loads((BOOKS_DIR / f"{code}.json").read_text(encoding="utf-8"))
        for cls, subj in pairs:
            if "by_class" in data:
                tree, key = data["by_class"].get(cls, []), f"{code}/{cls}"
            elif "by_subject" in data:
                tree, key = data["by_subject"].get(subj, []), f"{code}/{subj}"
            else:
                tree, key = data["toc"], code
            n = count(cut(tree, levels.get(key, 1)))
            if n:
                out[(cls, subj)] += n
    return out


def build_notes(classes: list[tuple[str, ClassCurriculum]], bundle: dict[str, Any]) -> str:
    cycle_of = {k: cur.level.cycle.value for k, cur in classes}
    total_subjects = sum(len(cur.subjects) for _, cur in classes)
    with_chapters = sum(bool(s.chapters) for _, cur in classes for s in cur.subjects)
    n_chapters = sum(leaves(s.chapters) for _, cur in classes for s in cur.subjects)

    no_chapters = defaultdict(lambda: defaultdict(list))  # cycle -> subject -> [class keys]
    positional = defaultdict(int)  # (class, subject) -> untitled groupings kept
    for key, cur in classes:
        for s in cur.subjects:
            if not s.chapters:
                no_chapters[cycle_of[key]][s.subject.code].append(key)

            def walk(nodes: list[Any]) -> None:
                for n in nodes:
                    if n.children:
                        positional[(key, s.subject.code)] += is_placeholder(n.name_fr or n.name_ar or "")
                        walk(n.children)
            walk(s.chapters)

    def fmt_classes(keys: list[str]) -> str:
        return ", ".join(keys) if len(keys) <= 3 else f"{len(keys)} classes"

    lines = [
        "# Curriculum notes",
        "",
        f"Generated {bundle['generated']} by `scripts/export_curriculum.py` from `data/curriculum/*.json`; "
        f"data in `curriculum.json`.",
        f"{len(classes)} classes · {total_subjects} class subjects · {with_chapters} with chapters · "
        f"{n_chapters} chapters. Subjects: decrees 2019-1085 / 2021-143. Chapters: official CNP textbooks, "
        "names as printed, never inferred.",
        "",
        "## Subjects without chapters (no CNP textbook)",
    ]
    for cycle in ("secondaire", "preparatoire", "primaire"):
        subjects = no_chapters.get(cycle, {})
        parts = [f"{code} ({fmt_classes(keys)})" for code, keys in sorted(subjects.items())]
        lines.append(f"- **{CYCLE_LABEL[cycle]}:** " + ("; ".join(parts) or "none"))

    missing = missing_chapters()
    lines += ["", "## Chapters missing (title unreadable in the textbook, not guessed)"]
    for cycle in ("secondaire", "preparatoire", "primaire"):
        rows = sorted(((n, cls, subj) for (cls, subj), n in missing.items() if cycle_of[cls] == cycle), reverse=True)
        parts = [f"{cls} {subj} ({n})" for n, cls, subj in rows]
        lines.append(f"- **{CYCLE_LABEL[cycle]}:** " + (", ".join(parts) or "none"))

    programmes = [(key, s) for key, cur in classes for s in cur.subjects if s.programme]
    units = [u for _, s in programmes for u in s.programme.units]
    lines += ["", "## Learning objectives (official programmes)",
              f"- {len(programmes)} class subjects so far ({sum(len(u.objectives) for u in units)} objectives): "
              + ", ".join(f"{key} {s.subject.code}" for key, s in programmes) + ".",
              f"- {sum(bool(u.chapter) for u in units)} of {sum(bool(u.topic) for u in units)} programme topics "
              "are linked to a chapter (near-identical names only); the 2011 programmes often word "
              "topics differently from the textbooks, so the others are left unlinked."]

    lines += ["", "## Untitled groupings kept (their chapters are named)"]
    rows = [f"{cls} {subj} ({n})" for (cls, subj), n in sorted(positional.items()) if n]
    lines.append("- " + (", ".join(rows) or "none"))
    lines += ["", "## To check",
              "- Chinese and Russian titles were decoded from a broken font encoding.",
              "- Borderline chapter levels: `data/cnp/chapter_depth.json`. "
              "Per-book sources and doubts: `data/cnp/books/<code>.json` (`notes`).", ""]
    return "\n".join(lines)


def write_csvs(classes: list[tuple[str, ClassCurriculum]]) -> tuple[int, int, int]:
    """Flat tables. A chapter's `theme` is the path of the groupings above it (e.g. "Physique > Ondes")."""
    chapter_rows, subject_rows, objective_rows = [], [], []
    for key, cur in classes:
        for s in cur.subjects:
            base = {
                "cycle": cur.level.cycle.value, "level_code": cur.level.code,
                "level_fr": cur.level.name_fr or "", "level_ar": cur.level.name_ar or "",
                "level_en": cur.level.name_en or "",
                "section_code": cur.section.code,
                "section_fr": cur.section.name_fr or "", "section_ar": cur.section.name_ar or "",
                "section_en": cur.section.name_en or "",
                "class_key": key, "subject_code": s.subject.code,
                "subject_fr": s.subject.name_fr or "", "subject_ar": s.subject.name_ar or "",
                "subject_en": s.subject.name_en or "",
                "language": s.instruction_language.value, "optional": s.is_optional,
            }
            order = 0

            def walk(nodes: list[Any], path: list[str], path_en: list[str]) -> None:
                nonlocal order
                for n in nodes:
                    label = n.name_fr or n.name_ar or ""
                    if n.children:
                        walk(n.children, path + [label], path_en + [n.name_en or ""])
                    else:
                        order += 1
                        chapter_rows.append({**base, "theme": " > ".join(path), "chapter_order": order,
                                             "chapter": label, "theme_en": " > ".join(path_en),
                                             "chapter_en": n.name_en or ""})
            walk(s.chapters, [], [])
            subject_rows.append({**base, "chapter_count": order})
            n = 0
            for u in s.programme.units if s.programme else []:
                for objective in u.objectives:
                    n += 1
                    objective_rows.append({**base, "domain": u.domain or "",
                                           "scope": "topic" if u.topic else "domain", "topic": u.topic or "",
                                           "chapter": u.chapter or "", "objective_order": n,
                                           "objective": objective})

    for path, rows, columns in (
        (OUT_CHAPTERS_CSV, chapter_rows, CLASS_COLUMNS + ["theme", "chapter_order", "chapter", "theme_en", "chapter_en"]),
        (OUT_SUBJECTS_CSV, subject_rows, CLASS_COLUMNS + ["chapter_count"]),
        (OUT_OBJECTIVES_CSV, objective_rows,
         CLASS_COLUMNS + ["domain", "scope", "topic", "chapter", "objective_order", "objective"]),
    ):
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    return len(chapter_rows), len(subject_rows), len(objective_rows)


def main() -> None:
    classes = load_classes()
    bundle = build_json(classes)
    OUT_JSON.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_NOTES.write_text(build_notes(classes, bundle), encoding="utf-8")
    n_chapters, n_subjects, n_objectives = write_csvs(classes)
    print(f"Wrote {OUT_JSON.name} ({OUT_JSON.stat().st_size // 1024} KB), {OUT_NOTES.name}, "
          f"{OUT_CHAPTERS_CSV.name} ({n_chapters} rows), {OUT_SUBJECTS_CSV.name} ({n_subjects} rows), "
          f"{OUT_OBJECTIVES_CSV.name} ({n_objectives} rows)")


if __name__ == "__main__":
    main()
