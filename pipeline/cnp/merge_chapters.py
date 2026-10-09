"""Step 4 — write the per-book chapter trees into data/curriculum/<class>.json.

data/cnp/books/<code>.json: {"code", "title", "used_for", "toc": [{"name", "children"}], "notes"}
(or "by_subject" for multi-subject books, "by_class" for one book covering several years).
Only the classes/subjects served by the given books are touched.

By default only chapters are kept: each book tree is cut at its chapter level from
data/cnp/chapter_depth.json (1 = top-level items are chapters, 2 = themes/parts -> chapters);
sections, lessons and texts below are dropped. --full keeps the whole tree.

Usage: python -m pipeline.cnp.merge_chapters --all [--full]          (recommended: rebuilds every subject)
       python -m pipeline.cnp.merge_chapters CODE [CODE ...] [--full] (all books of a subject must be listed)
"""
import json, sys, os, re, unicodedata
from pathlib import Path
from collections import defaultdict
from models import ChapterSchema, ClassCurriculum
from pipeline.cnp.book_mapping import MAP
from pipeline.cnp.paths import CATALOGUE, CHAPTER_DEPTH, CURRICULUM_DIR, BOOKS_DIR

ARABIC_LETTER = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
LATIN_LETTER = re.compile(r"[A-Za-zÀ-ÿ]")


def bilingual(text):
    """Store a title in name_ar or name_fr according to its script."""
    text = re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()
    arabic = len(ARABIC_LETTER.findall(text)) > len(LATIN_LETTER.findall(text))
    return {"name_ar": text} if arabic else {"name_fr": text}


def write_class(curriculum, path: Path):
    data = curriculum.model_dump(mode="json", exclude_none=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


DISCIPLINE = {"223": ("Physique", "الفيزياء"), "224": ("Chimie", "الكيمياء")}


# Positional labels written where a title was unreadable (never a real title).
PLACEHOLDER = re.compile(
    r"(غير مقروء|^\[placeholder\]"
    r"|^(النص|الدرس|الوحدة|المحور|المبحث|القسم|الفترة|مدار الاهتمام|الباب|درس|نص) ?[\d١-٩]+$"
    r"|^(النص|الدرس|الوحدة|المحور|المبحث|القسم|الباب)\s+(الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن)$"
    r"|^درس ص [\d\-–]+"
    r"|^Chapitre [IVX\d]+$|^(Lesson|Module|Theme|Unit|Séquence|Unité|Partie) ?[\dIVX]+$"
    r"|^Module (d'apprentissage|de lecture) \d+$)"
)
PAGE_REF = re.compile(r"\s*\(ص\s*[\d\-–]+\)")  # "(ص 28-31)" page references, not part of a title


def clean(name):
    return PAGE_REF.sub("", re.sub(r"^\[placeholder\]\s*", "", name)).strip()


def cut(items, levels):
    """Keep `levels` levels of the tree (the chapter level and the groupings above it)."""
    if levels <= 0:
        return []
    return [{"name": it["name"], "children": cut(it.get("children", []), levels - 1)} for it in items]


def prune(items):
    """Drop unreadable-title lessons; keep a placeholder container only if it groups named children."""
    out = []
    for it in items:
        children = prune(it.get("children", []))
        name = clean(it["name"])
        if (PLACEHOLDER.search(it["name"]) or PLACEHOLDER.search(name)) and not children:
            continue
        out.append({"name": name, "children": children})
    return out


def node(item, order):
    return ChapterSchema(order_index=order, **bilingual(item["name"]),
                         children=[node(c, i) for i, c in enumerate(item.get("children", []), 1)])


def main(codes, full=False):
    levels = {} if full else json.load(open(CHAPTER_DEPTH, encoding="utf-8"))
    books = {b["code"]: b for b in json.load(open(CATALOGUE, encoding="utf-8"))}
    targets = defaultdict(list)  # (class, subject) -> [book codes]
    for code in codes:
        if not (BOOKS_DIR / f"{code}.json").exists():
            print("missing book file for", code); continue
        for cls, subj in MAP[code]:
            targets[(cls, subj)].append(code)
    by_class = defaultdict(dict)
    for (cls, subj), book_codes in targets.items():
        book_codes.sort()
        def chapters_for(c):
            data = json.load(open(BOOKS_DIR / f"{c}.json", encoding="utf-8"))
            if "by_class" in data:  # one book for several years (collège informatique)
                tree, key = data["by_class"].get(cls, []), f"{c}/{cls}"
            elif "by_subject" in data:  # المواد الاجتماعية: history + geography + civics in one book
                tree, key = data["by_subject"].get(subj, []), f"{c}/{subj}"
            else:
                tree, key = data["toc"], c
            return tree if full else cut(tree, levels.get(key, 1))
        parts = [(c, chapters_for(c)) for c in book_codes]
        disciplines = {c[:3] for c, _ in parts}
        if len(disciplines) > 1 and disciplines <= set(DISCIPLINE):  # Physique + Chimie
            items = [{"name": DISCIPLINE[c[:3]][0], "children": ch} for c, ch in parts]
        else:
            items = [x for _, ch in parts for x in ch]
        items = prune(items)
        by_class[cls][subj] = ([node(x, i) for i, x in enumerate(items, 1)], book_codes)
    for cls, subjects in sorted(by_class.items()):
        path = CURRICULUM_DIR / f"{cls}.json"
        cur = ClassCurriculum.model_validate_json(open(path, encoding="utf-8").read())
        refs = [r for r in cur.references if not r.startswith("CNP ")]
        used = set()
        new_subjects = []
        for s in cur.subjects:
            if s.subject.code in subjects:
                chapters, book_codes = subjects[s.subject.code]
                s = s.model_copy(update={"chapters": chapters}); used.update(book_codes)
            new_subjects.append(s)
        refs += [f"CNP {c} — {books[c]['title']} — {books[c]['pdfs'][0]}" for c in sorted(used)]
        cur = cur.model_copy(update={"subjects": new_subjects, "references": refs})
        write_class(ClassCurriculum.model_validate(cur.model_dump()), path)
        print(f"{cls:<30} " + ", ".join(f"{k}:{len(v[0])}" for k, v in sorted(subjects.items())))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--full"]
    main(list(MAP) if args == ["--all"] else args, full="--full" in sys.argv)
