"""Translate printed curriculum names into English, with Claude (machine translation).

Collects every name in data/curriculum/*.json (levels, sections, subjects, themes, chapters), keeps those not yet
in data/translations/en.json, and asks Claude to translate them in batches, each with its context (class, subject,
themes above it), under the rules in TRANSLATION_RULES.md. New translations are merged into en.json; existing ones
are never changed (edit en.json by hand to correct one).

Then run `python -m pipeline.cnp.merge_chapters --all` (adds name_en to the class files) and
`python scripts/export_curriculum.py`.

Usage: python -m pipeline.translate_names [--dry-run]
Credentials: ANTHROPIC_API_KEY, or a profile from `ant auth login`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

import anthropic
from pydantic import BaseModel

from pipeline.cnp.paths import CURRICULUM_DIR, TRANSLATIONS_EN

MODEL = "claude-opus-5-5"
CHUNK = 150  # names per request
RULES_FILE = Path(__file__).with_name("TRANSLATION_RULES.md")


class Translation(BaseModel):
    text: str
    en: str


class Translations(BaseModel):
    translations: list[Translation]


OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {"translations": {"type": "array", "items": {
        "type": "object", "properties": {"text": {"type": "string"}, "en": {"type": "string"}},
        "required": ["text", "en"], "additionalProperties": False}}},
    "required": ["translations"], "additionalProperties": False,
}


def collect_names() -> dict[str, dict[str, str]]:
    """Printed name -> {text, kind, context}, first occurrence wins."""
    entries: dict[str, dict[str, str]] = {}

    def add(node: dict, kind: str, context: str) -> None:
        text = node.get("name_fr") or node.get("name_ar")
        if text and text not in entries:
            entries[text] = {"text": text, "kind": kind, "context": context}

    def walk(chapters: list[dict], context: str, parents: list[str]) -> None:
        for c in chapters:
            under = f" | under: {' > '.join(parents)}" if parents else ""
            add(c, "theme" if c.get("children") else "chapter", context + under)
            walk(c.get("children", []), context, parents + [c.get("name_fr") or c.get("name_ar")])

    for path in sorted(CURRICULUM_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        add(data["level"], "level", "school year")
        add(data["section"], "section", f"stream / specialty of {path.stem}")
        for s in data["subjects"]:
            add(s["subject"], "subject", "school subject")
            subject = s["subject"].get("name_fr") or s["subject"].get("name_ar")
            walk(s["chapters"], f"{path.stem} / {subject}", [])
    return entries


def translate(client: anthropic.Anthropic, items: list[dict[str, str]]) -> dict[str, str]:
    message = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
        system=[{"type": "text", "text": RULES_FILE.read_text(encoding="utf-8"),
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": "Translate these items:\n\n" + json.dumps(items, ensure_ascii=False)}],
    )
    if message.stop_reason in ("refusal", "max_tokens"):
        raise RuntimeError(f"stopped with {message.stop_reason}")
    text = next(b.text for b in message.content if b.type == "text")
    result = Translations.model_validate_json(text)
    wanted = {i["text"] for i in items}
    return {t.text: t.en.strip() for t in result.translations if t.text in wanted and t.en.strip()}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="only count the names still to translate")
    args = parser.parse_args(argv)

    known: dict[str, Any] = json.loads(TRANSLATIONS_EN.read_text(encoding="utf-8")) if TRANSLATIONS_EN.exists() else {}
    missing = [e for text, e in collect_names().items() if text not in known]
    print(f"{len(known)} names already translated, {len(missing)} to translate")
    if args.dry_run or not missing:
        return 0

    client = anthropic.Anthropic()
    failures = 0
    for start in range(0, len(missing), CHUNK):
        chunk = missing[start:start + CHUNK]
        try:
            new = translate(client, chunk)
        except (anthropic.APIError, RuntimeError, ValueError) as exc:
            print(f"names {start}-{start + len(chunk)}: {exc}")
            failures += 1
            continue
        known.update(new)
        TRANSLATIONS_EN.parent.mkdir(parents=True, exist_ok=True)
        TRANSLATIONS_EN.write_text(json.dumps(dict(sorted(known.items())), ensure_ascii=False, indent=1) + "\n",
                                   encoding="utf-8")
        print(f"names {start}-{start + len(chunk)}: {len(new)} translated")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
