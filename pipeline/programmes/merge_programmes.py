"""Write the official programmes (learning objectives) into data/curriculum/<class>.json.

data/programmes/<class>__<SUBJECT>.json: {"class", "subject", "source": {document, issuer, url, pages},
"units": [{"domain", "topic", "contents", "objectives"}], "notes"}, copied verbatim from the Ministry's
programme (see RULES.md). Run after pipeline.cnp.merge_chapters.

A unit is linked to a chapter of the same subject only when their names are near-identical once accents,
numbering ("I-2.", "1-") and articles are ignored. Otherwise `chapter` stays empty: no guessed links.

Usage: python -m pipeline.programmes.merge_programmes
"""
import difflib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Optional

from models import ClassCurriculum, ProgrammeSchema, chapter_names
from pipeline.cnp.merge_chapters import write_class
from pipeline.cnp.paths import CURRICULUM_DIR, ROOT

PROGRAMMES_DIR = ROOT / "data" / "programmes"
MIN_RATIO = 0.92  # tolerates spelling/punctuation variants, not different wording
NUMBERING = re.compile(r"^\s*(?:[IVX]+|\d+|[A-Z])(?:\s*[-.]\s*\d+)*\s*[-.)/]\s*")
ARTICLES = re.compile(r"\b(les|le|la|l|des|de|du|d|et|un|une|en|a|aux|au)\b")


def norm(name: str) -> str:
    name = NUMBERING.sub("", name.split(">")[-1])
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    name = ARTICLES.sub(" ", re.sub(r"[^a-z0-9 ]+", " ", name))
    return re.sub(r"\s+", " ", name).strip()


def link(topic: Optional[str], chapters: set[str]) -> Optional[str]:
    """The chapter whose name is near-identical to the topic, if exactly one is."""
    n = norm(topic or "")
    if len(n) < 4:
        return None
    hits = [c for c in chapters if difflib.SequenceMatcher(None, n, norm(c)).ratio() >= MIN_RATIO]
    return hits[0] if len(hits) == 1 else None


def main() -> None:
    files = sorted(PROGRAMMES_DIR.glob("*.json"))
    by_class: dict[str, dict[str, dict]] = defaultdict(dict)
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        if f.stem != f"{data['class']}__{data['subject']}":
            sys.exit(f"{f.name}: file name does not match class/subject")
        by_class[data["class"]][data["subject"]] = data

    if unknown := set(by_class) - {p.stem for p in CURRICULUM_DIR.glob("*.json")}:
        sys.exit(f"no such class {sorted(unknown)}")
    for path in sorted(CURRICULUM_DIR.glob("*.json")):  # every class, so removed programmes are cleared
        cls, programmes = path.stem, by_class.get(path.stem, {})
        cur = ClassCurriculum.model_validate_json(path.read_text(encoding="utf-8"))
        codes = {s.subject.code for s in cur.subjects}
        if unknown := set(programmes) - codes:
            sys.exit(f"{cls}: no such subject {sorted(unknown)}")
        subjects = []
        for s in cur.subjects:
            data = programmes.get(s.subject.code)
            s = s.model_copy(update={"programme": None})
            if data:
                names = chapter_names(s.chapters)
                units = [{k: u[k] for k in ("domain", "topic", "contents", "objectives")}
                         | {"chapter": link(u["topic"], names)} for u in data["units"]]
                s = s.model_copy(update={"programme": ProgrammeSchema.model_validate(
                    {"source": data["source"], "units": units})})
                linked = sum(1 for u in units if u["chapter"])
                print(f"{cls:<30} {s.subject.code:<5} {len(units):>3} units, "
                      f"{sum(len(u['objectives']) for u in units):>3} objectives, {linked} linked to chapters")
            subjects.append(s)
        cur = cur.model_copy(update={"subjects": subjects})
        write_class(ClassCurriculum.model_validate(cur.model_dump()), path)


if __name__ == "__main__":
    main()
