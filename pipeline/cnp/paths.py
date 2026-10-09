"""Shared locations for the CNP textbook pipeline."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CURRICULUM_DIR = ROOT / "data" / "curriculum"  # source of truth: one file per class

DATA_DIR = ROOT / "data" / "cnp"  # versioned: small, reviewed outputs
CATALOGUE = DATA_DIR / "catalogue.json"  # every CNP student textbook (code, title, PDF links)
BOOKS_DIR = DATA_DIR / "books"  # one file per textbook: full table of contents + notes
TRANSLATIONS_EN = ROOT / "data" / "translations" / "en.json"  # printed name -> English machine translation
CHAPTER_DEPTH = DATA_DIR / "chapter_depth.json"  # per book: depth at which chapters sit (1 or 2)

CACHE_DIR = ROOT / ".cache" / "cnp"  # not versioned: regenerable
EXTRACT_DIR = CACHE_DIR / "extract"  # table-of-contents material extracted from each PDF
PDF_DIR = CACHE_DIR / "pdf"  # PDFs live here only while a book is being processed
CATALOGUE_PAGES_DIR = CACHE_DIR / "catalogue_pages"

for _d in (BOOKS_DIR, EXTRACT_DIR, PDF_DIR, CATALOGUE_PAGES_DIR):
    _d.mkdir(parents=True, exist_ok=True)
