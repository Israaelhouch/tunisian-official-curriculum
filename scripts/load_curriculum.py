"""Load data/curriculum/*.json into PostgreSQL.

1. Validate every file with `models.ClassCurriculum` (all errors are reported,
   nothing is written if any file is invalid).
2. Check cross-file consistency: a level or subject code repeated in several
   files must carry identical data; a class (level + section) appears once.
3. Upsert in a single transaction, keyed by code:
       levels by code, sections by (level, code), subjects by code,
       section subjects by (section, subject), chapters by code,
       programme units by (section subject, order).
   Re-running updates rows in place. Subjects, chapters and programme units
   that were removed from a file are deleted for that class.

Usage:
    DATABASE_URL=postgresql://user:pass@localhost:5432/exams python scripts/load_curriculum.py
    python scripts/load_curriculum.py --dry-run      # validate only, no database needed
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, TypeVar

from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from models import (  # noqa: E402
    Base,
    Chapter,
    ChapterSchema,
    ClassCurriculum,
    EducationalLevel,
    ProgrammeUnit,
    Section,
    SectionSubject,
    SectionSubjectSchema,
    Subject,
)

log = logging.getLogger("load_curriculum")

DATABASE_URL_ENV = "DATABASE_URL"
DEFAULT_DIR = ROOT / "data" / "curriculum"

M = TypeVar("M", bound=Base)


class LoadError(Exception):
    pass


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def load_files(directory: Path) -> dict[Path, ClassCurriculum]:
    files = sorted(directory.glob("*.json"))
    if not files:
        raise LoadError(f"No JSON files in {directory}")

    parsed: dict[Path, ClassCurriculum] = {}
    errors: list[str] = []
    for path in files:
        try:
            parsed[path] = ClassCurriculum.model_validate_json(path.read_text(encoding="utf-8"))
        except ValidationError as exc:
            errors.append(f"{path.name}:\n{exc}")
    if errors:
        raise LoadError("Invalid curriculum file(s):\n\n" + "\n\n".join(errors))

    check_consistency(parsed)
    return parsed


def check_consistency(parsed: dict[Path, ClassCurriculum]) -> None:
    errors: list[str] = []

    classes = Counter(c.class_key for c in parsed.values())
    errors += [f"class {k} is defined in {n} files" for k, n in classes.items() if n > 1]

    def first_definitions(items: list[tuple[str, str, dict[str, Any]]], kind: str) -> None:
        seen: dict[str, tuple[str, dict[str, Any]]] = {}
        for code, file, data in items:
            if code not in seen:
                seen[code] = (file, data)
            elif seen[code][1] != data:
                errors.append(f"{kind} {code} differs between {seen[code][0]} and {file}: "
                              f"{seen[code][1]} != {data}")

    first_definitions([(c.level.code, p.name, c.level.model_dump()) for p, c in parsed.items()],
                      "level")
    first_definitions([(o.subject.code, p.name, o.subject.model_dump())
                       for p, c in parsed.items() for o in c.subjects], "subject")
    if errors:
        raise LoadError("Inconsistent curriculum files:\n  " + "\n  ".join(errors))


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------


@dataclass
class Stats:
    inserted: Counter[str]
    updated: Counter[str]
    deleted: Counter[str]

    def __init__(self) -> None:
        self.inserted, self.updated, self.deleted = Counter(), Counter(), Counter()


def upsert(session: Session, model: type[M], key: dict[str, Any], values: dict[str, Any],
           stats: Stats) -> M:
    """Fetch by natural key, then insert or update only the changed columns."""
    obj = session.scalars(select(model).filter_by(**key)).one_or_none()
    name = model.__tablename__
    if obj is None:
        obj = model(**key, **values)
        session.add(obj)
        session.flush()
        stats.inserted[name] += 1
        return obj
    changed = False
    for attr, value in values.items():
        if getattr(obj, attr) != value:
            setattr(obj, attr, value)
            changed = True
    if changed:
        session.flush()
        stats.updated[name] += 1
    return obj


def _names(model: Any) -> dict[str, Optional[str]]:
    return {"name_fr": model.name_fr, "name_ar": model.name_ar, "name_en": model.name_en}


def load_class(session: Session, cur: ClassCurriculum, stats: Stats) -> None:
    lvl = cur.level
    level = upsert(session, EducationalLevel, {"code": lvl.code}, {
        **_names(lvl), "cycle": lvl.cycle, "grade_number": lvl.grade_number,
        "display_order": lvl.display_order, "is_national_exam_year": lvl.is_national_exam_year,
    }, stats)
    section = upsert(session, Section, {"level_id": level.id, "code": cur.section.code}, {
        **_names(cur.section), "is_common_core": cur.section.is_common_core,
    }, stats)

    kept: set[int] = set()
    for entry in cur.subjects:
        subject = upsert(session, Subject, {"code": entry.subject.code}, _names(entry.subject), stats)
        kept.add(load_section_subject(session, section, subject, entry, cur.class_key, stats).id)

    # Subjects removed from the file.
    stale = session.scalars(select(SectionSubject).where(
        SectionSubject.section_id == section.id,
        SectionSubject.id.not_in(kept or {0}),
    )).all()
    for obj in stale:
        session.delete(obj)
        stats.deleted[SectionSubject.__tablename__] += 1


def load_section_subject(session: Session, section: Section, subject: Subject,
                         entry: SectionSubjectSchema, class_key: str,
                         stats: Stats) -> SectionSubject:
    row = upsert(session, SectionSubject, {
        "section_id": section.id, "subject_id": subject.id,
    }, {
        "instruction_language": entry.instruction_language,
        "is_optional": entry.is_optional,
        "programme_source": entry.programme.source.model_dump() if entry.programme else None,
    }, stats)

    prefix = f"{class_key}.{subject.code}"
    kept: set[str] = set()
    load_chapters(session, row, entry.chapters, None, prefix, 1, kept, stats)

    for chapter in session.scalars(
        select(Chapter).where(Chapter.section_subject_id == row.id)
    ).all():
        if chapter.code not in kept:
            session.delete(chapter)
            stats.deleted[Chapter.__tablename__] += 1
    load_programme(session, row, entry, stats)
    return row


def load_programme(session: Session, owner: SectionSubject, entry: SectionSubjectSchema,
                   stats: Stats) -> None:
    """Programme units by order; a unit's `chapter` (a printed name) becomes a chapter id."""
    chapter_ids = {c.name_fr or c.name_ar: c.id for c in session.scalars(
        select(Chapter).where(Chapter.section_subject_id == owner.id).order_by(Chapter.code))}
    units = entry.programme.units if entry.programme else []
    for order, unit in enumerate(units, 1):
        upsert(session, ProgrammeUnit, {"section_subject_id": owner.id, "order_index": order}, {
            "domain": unit.domain, "topic": unit.topic,
            "contents": unit.contents, "objectives": unit.objectives,
            "chapter_id": chapter_ids[unit.chapter] if unit.chapter else None,
        }, stats)
    for stale in session.scalars(select(ProgrammeUnit).where(
        ProgrammeUnit.section_subject_id == owner.id, ProgrammeUnit.order_index > len(units),
    )).all():
        session.delete(stale)
        stats.deleted[ProgrammeUnit.__tablename__] += 1


def load_chapters(session: Session, owner: SectionSubject, chapters: list[ChapterSchema],
                  parent: Optional[Chapter], prefix: str, depth: int, kept: set[str],
                  stats: Stats) -> None:
    for ch in chapters:
        code = f"{prefix}.{ch.order_index}"
        kept.add(code)
        row = upsert(session, Chapter, {"code": code}, {
            **_names(ch),
            "section_subject_id": owner.id,
            "parent_id": parent.id if parent else None,
            "depth": depth,
            "order_index": ch.order_index,
            "trimester": ch.trimester,
            "objectives": ch.objectives,
            "suggested_hours": ch.suggested_hours,
        }, stats)
        load_chapters(session, owner, ch.children, row, code, depth + 1, kept, stats)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def database_url() -> str:
    raw = os.environ.get(DATABASE_URL_ENV)
    if not raw:
        raise LoadError(f"Set {DATABASE_URL_ENV}, e.g. postgresql://user:pass@localhost:5432/exams")
    url = make_url(raw)
    if url.drivername == "postgresql":  # default to the psycopg 3 driver from requirements.txt
        url = url.set(drivername="postgresql+psycopg")
    return url.render_as_string(hide_password=False)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR, help="curriculum folder")
    parser.add_argument("--dry-run", action="store_true", help="validate files only")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    try:
        parsed = load_files(args.dir)
        log.info("Validated %d class file(s)", len(parsed))
        if args.dry_run:
            return 0

        engine = create_engine(database_url())
        Base.metadata.create_all(engine)  # Phase 1: no migrations yet
        stats = Stats()
        with Session(engine) as session, session.begin():
            for cur in parsed.values():
                load_class(session, cur, stats)
    except LoadError as exc:
        log.error("%s", exc)
        return 1
    except SQLAlchemyError as exc:
        log.error("Database error, nothing was written: %s", exc.__class__.__name__)
        log.error("%s", str(exc).splitlines()[0])
        return 1

    for table in ("educational_levels", "sections", "subjects", "section_subjects", "chapters",
                  "programme_units"):
        log.info("%-22s inserted=%-4d updated=%-4d deleted=%d", table,
                 stats.inserted[table], stats.updated[table], stats.deleted[table])
    return 0


if __name__ == "__main__":
    sys.exit(main())
