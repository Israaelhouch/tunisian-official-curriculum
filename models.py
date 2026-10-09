"""Curriculum data layer for the Tunisian exam generator (Phase 1).

Hierarchy (official Tunisian school system):

    EducationalLevel  (e.g. "1ère année secondaire", "Bac")
      └── Section     (e.g. "Informatique", "Sciences expérimentales", "Tronc commun")
            └── SectionSubject  (which official subjects this class has)
                  └── Chapter   (ordered, nestable: chapter -> lesson)

`Subject` is a global catalogue (MATH, ALGO...) shared by every section; what
differs per section is whether the subject is taught, its teaching language
and its chapter list, so those hang off `SectionSubject`.

Source of truth: one JSON file per class in `data/curriculum/` (validated by
`ClassCurriculum`). PostgreSQL is loaded from those files by
`scripts/load_curriculum.py`.

Two layers are defined:
  * SQLAlchemy 2.0 ORM models (persistence, PostgreSQL)
  * Pydantic v2 schemas (validation of the `data/curriculum/*.json` files)
"""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Cycle(str, enum.Enum):
    """Stage of the Tunisian education system."""

    PRIMAIRE = "primaire"  # التعليم الابتدائي (1ère → 6ème année)
    PREPARATOIRE = "preparatoire"  # التعليم الإعدادي / enseignement de base (7ème → 9ème)
    SECONDAIRE = "secondaire"  # التعليم الثانوي (1ère → Bac)


class InstructionLanguage(str, enum.Enum):
    """Language a subject is taught (and examined) in."""

    AR = "ar"
    FR = "fr"
    EN = "en"
    DE = "de"
    ES = "es"
    IT = "it"
    RU = "ru"
    ZH = "zh"
    PT = "pt"


class Trimester(int, enum.Enum):
    T1 = 1
    T2 = 2
    T3 = 3


# ---------------------------------------------------------------------------
# SQLAlchemy ORM
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


def _enum(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """Store enum *values* ("fr", "secondaire") rather than member names."""
    return SAEnum(enum_cls, name=name, values_callable=lambda e: [str(m.value) for m in e])


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class BilingualNameMixin:
    """French / Arabic labels. At least one is required: some official labels
    exist in a single language (e.g. foreign-language subjects, Arabic-only lessons)."""

    name_fr: Mapped[Optional[str]] = mapped_column(String(255))
    name_ar: Mapped[Optional[str]] = mapped_column(String(255))


def _has_a_name(table: str) -> CheckConstraint:
    return CheckConstraint("name_fr IS NOT NULL OR name_ar IS NOT NULL", name=f"ck_{table}_name")


class EducationalLevel(TimestampMixin, BilingualNameMixin, Base):
    """A school year, e.g. 7ème année de base, 1ère année secondaire, Bac."""

    __tablename__ = "educational_levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)  # "1S", "BAC"
    cycle: Mapped[Cycle] = mapped_column(_enum(Cycle, "cycle"), nullable=False)
    # Year number as it is commonly named: 1–6 primaire, 7–9 base, 1–4 secondaire (Bac = 4).
    grade_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Global sort order across all cycles (5ème primaire = 5 ... Bac = 13).
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_national_exam_year: Mapped[bool] = mapped_column(default=False, nullable=False)

    sections: Mapped[list[Section]] = relationship(
        back_populates="level", cascade="all, delete-orphan", order_by="Section.code"
    )

    __table_args__ = (
        CheckConstraint("grade_number BETWEEN 1 AND 9", name="ck_level_grade"),
        _has_a_name("level"),
    )

    def __repr__(self) -> str:
        return f"<EducationalLevel {self.code}>"


class Section(TimestampMixin, BilingualNameMixin, Base):
    """A specialty/stream within a level. Levels without streams
    (primaire, base, 1ère secondaire) get a single "tronc commun" section,
    so every subject always hangs off a section."""

    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    level_id: Mapped[int] = mapped_column(
        ForeignKey("educational_levels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)  # "INFO", "TC"
    is_common_core: Mapped[bool] = mapped_column(default=False, nullable=False)

    level: Mapped[EducationalLevel] = relationship(back_populates="sections")
    subjects: Mapped[list[SectionSubject]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("level_id", "code", name="uq_section_level_code"),
        _has_a_name("section"),
    )

    def __repr__(self) -> str:
        return f"<Section {self.code} level_id={self.level_id}>"


class Subject(TimestampMixin, BilingualNameMixin, Base):
    """Global subject catalogue, independent of level/section."""

    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)  # "MATH", "ALGO"

    section_subjects: Mapped[list[SectionSubject]] = relationship(back_populates="subject")

    __table_args__ = (_has_a_name("subject"),)

    def __repr__(self) -> str:
        return f"<Subject {self.code}>"


class SectionSubject(TimestampMixin, Base):
    """An official subject of a class (Section × Subject).

    Chapters belong here because the same subject has different programmes
    per section (Maths Bac Info ≠ Maths Bac Math). Teaching language lives
    here too: Maths is taught in Arabic up to 9ème and in French in secondaire.
    """

    __tablename__ = "section_subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    instruction_language: Mapped[InstructionLanguage] = mapped_column(
        _enum(InstructionLanguage, "instruction_language"), nullable=False
    )
    # Options chosen by the student (3rd foreign language, music, arts...).
    is_optional: Mapped[bool] = mapped_column(default=False, nullable=False)

    section: Mapped[Section] = relationship(back_populates="subjects")
    subject: Mapped[Subject] = relationship(back_populates="section_subjects")
    # Every chapter and lesson of this programme (flat); see `root_chapters`.
    chapters: Mapped[list[Chapter]] = relationship(
        back_populates="section_subject",
        cascade="all, delete-orphan",
        order_by="Chapter.order_index",
    )

    __table_args__ = (
        UniqueConstraint("section_id", "subject_id", name="uq_section_subject"),
    )

    @property
    def root_chapters(self) -> list[Chapter]:
        """Top-level chapters only (lessons are reachable via `Chapter.children`)."""
        return [c for c in self.chapters if c.parent_id is None and c.parent is None]

    def __repr__(self) -> str:
        return f"<SectionSubject section_id={self.section_id} subject_id={self.subject_id}>"


class Chapter(TimestampMixin, BilingualNameMixin, Base):
    """A node of a section-subject programme. Self-referencing so a chapter
    can hold lessons (chapter -> lesson)."""

    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stable key derived from the position in the tree, e.g. "BAC.INFO.ALGO.3.2".
    # Lets the loader update rows in place instead of duplicating them.
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    section_subject_id: Mapped[int] = mapped_column(
        ForeignKey("section_subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    depth: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 = chapter, 2 = lesson...
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    trimester: Mapped[Optional[Trimester]] = mapped_column(_enum(Trimester, "trimester"))
    # Learning objectives / competencies, used to ground exam generation.
    objectives: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    suggested_hours: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 1))

    section_subject: Mapped[SectionSubject] = relationship(back_populates="chapters")
    parent: Mapped[Optional[Chapter]] = relationship(
        back_populates="children", remote_side="Chapter.id"
    )
    children: Mapped[list[Chapter]] = relationship(
        back_populates="parent", cascade="all, delete-orphan", order_by="Chapter.order_index"
    )

    __table_args__ = (
        CheckConstraint("order_index >= 1", name="ck_chapter_order_positive"),
        CheckConstraint("depth >= 1", name="ck_chapter_depth_positive"),
        _has_a_name("chapter"),
    )

    def __repr__(self) -> str:
        return f"<Chapter {self.code} {(self.name_fr or self.name_ar)!r}>"


# ---------------------------------------------------------------------------
# Pydantic schemas — one `ClassCurriculum` per file in data/curriculum/
# ---------------------------------------------------------------------------

CODE_PATTERN = r"^[A-Z0-9_]{2,32}$"


class StrictModel(BaseModel):
    """Curriculum files are the source of truth: unknown keys are rejected."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class BilingualName(StrictModel):
    name_fr: Optional[str] = Field(default=None, min_length=1, max_length=255)
    name_ar: Optional[str] = Field(default=None, min_length=1, max_length=255)

    @model_validator(mode="after")
    def _at_least_one_name(self) -> BilingualName:
        if not (self.name_fr or self.name_ar):
            raise ValueError("name_fr or name_ar is required")
        return self


class ChapterSchema(BilingualName):
    order_index: int = Field(ge=1)
    trimester: Optional[Trimester] = None
    objectives: list[str] = Field(default_factory=list)
    suggested_hours: Optional[Decimal] = Field(default=None, gt=0)
    children: list[ChapterSchema] = Field(default_factory=list)

    @field_validator("children")
    @classmethod
    def _unique_child_order(cls, v: list[ChapterSchema]) -> list[ChapterSchema]:
        _ensure_unique([c.order_index for c in v], "children.order_index")
        return v


class SubjectSchema(BilingualName):
    """Catalogue entry; repeated in every class file that offers the subject
    and must be identical across files (checked by the loader)."""

    code: str = Field(pattern=CODE_PATTERN)


class SectionSubjectSchema(StrictModel):
    """An official subject of this class."""

    subject: SubjectSchema
    instruction_language: InstructionLanguage
    is_optional: bool = False
    chapters: list[ChapterSchema] = Field(default_factory=list)

    @field_validator("chapters")
    @classmethod
    def _unique_chapter_order(cls, v: list[ChapterSchema]) -> list[ChapterSchema]:
        _ensure_unique([c.order_index for c in v], "chapters.order_index")
        return v


class LevelSchema(BilingualName):
    """Level definition; must be identical in every file of the same level."""

    code: str = Field(pattern=CODE_PATTERN)
    cycle: Cycle
    grade_number: int = Field(ge=1, le=9)
    display_order: int = Field(ge=1)
    is_national_exam_year: bool = False


class SectionSchema(BilingualName):
    code: str = Field(pattern=CODE_PATTERN)
    is_common_core: bool = False


class ClassCurriculum(StrictModel):
    """Root schema of one `data/curriculum/<class>.json` file (one class = level + section)."""

    schema_version: str = "3.0"
    # Official texts the subject list is based on (decrees, arrêtés), with links.
    references: list[str] = Field(default_factory=list)
    level: LevelSchema
    section: SectionSchema
    subjects: list[SectionSubjectSchema]

    @field_validator("subjects")
    @classmethod
    def _unique_subjects(cls, v: list[SectionSubjectSchema]) -> list[SectionSubjectSchema]:
        _ensure_unique([s.subject.code for s in v], "subjects.subject.code")
        return v

    @property
    def class_key(self) -> str:
        return f"{self.level.code}.{self.section.code}"


def _ensure_unique(values: list[object], field: str) -> None:
    seen: set[object] = set()
    dupes = {v for v in values if v in seen or seen.add(v)}  # type: ignore[func-returns-value]
    if dupes:
        raise ValueError(f"Duplicate values for {field}: {sorted(map(str, dupes))}")


ChapterSchema.model_rebuild()
