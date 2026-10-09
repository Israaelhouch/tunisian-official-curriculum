"""Step 3 — turn extracted textbook material into a table of contents, with Claude.

Reads .cache/cnp/extract/<code>.json (sommaire pages, headings, markers, OCR pages) and asks Claude to
rebuild the book's table of contents under the rules in AI_STRUCTURING_RULES.md (book order, names
exactly as printed, never inferred). Structured outputs guarantee schema-valid JSON.

Results go to .cache/cnp/proposed/<code>.json for review; --apply writes them to data/cnp/books/
(the curated files) instead. Then run merge_chapters --all and scripts/export_curriculum.py.

Usage:
  python -m pipeline.cnp.structure_books 222472 223471            # one request per book
  python -m pipeline.cnp.structure_books --batch bac              # Batch API (50% cost), prints the batch id
  python -m pipeline.cnp.structure_books --collect msgbatch_...   # fetch a finished batch
  add --apply to write into data/cnp/books/ instead of the review folder

Credentials: ANTHROPIC_API_KEY, or a profile from `ant auth login`.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Optional

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from pydantic import BaseModel, Field

from pipeline.cnp.book_mapping import MAP, batch as batch_codes
from pipeline.cnp.paths import BOOKS_DIR, CACHE_DIR, CATALOGUE, EXTRACT_DIR

MODEL = "claude-opus-5-5"
EFFORT = "high"  # careful reading of noisy OCR; Opus 5.5 defaults to medium
MAX_TOKENS = 16000
RULES_FILE = Path(__file__).with_name("AI_STRUCTURING_RULES.md")
PROPOSED_DIR = CACHE_DIR / "proposed"
BATCHES_DIR = CACHE_DIR / "batches"


# --- Output schema (3 levels max; the API does not accept recursive schemas) -----------------------

class Leaf(BaseModel):
    name: str


class Level2(BaseModel):
    name: str
    children: list[Leaf] = Field(default_factory=list)


class Level1(BaseModel):
    name: str
    children: list[Level2] = Field(default_factory=list)


class SubjectToc(BaseModel):
    subject: str  # subject code from the book's targets, e.g. HIST
    toc: list[Level1]


class BookToc(BaseModel):
    toc: list[Level1]  # empty when by_subject is used
    by_subject: list[SubjectToc]  # only for books bundling several subjects (المواد الاجتماعية)
    notes: str


def _node(children: Optional[dict] = None) -> dict:
    props: dict[str, Any] = {"name": {"type": "string"}}
    if children:
        props["children"] = {"type": "array", "items": children}
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


TOC_SCHEMA = {"type": "array", "items": _node(_node(_node()))}
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "toc": TOC_SCHEMA,
        "by_subject": {"type": "array", "items": {
            "type": "object",
            "properties": {"subject": {"type": "string"}, "toc": TOC_SCHEMA},
            "required": ["subject", "toc"], "additionalProperties": False,
        }},
        "notes": {"type": "string"},
    },
    "required": ["toc", "by_subject", "notes"],
    "additionalProperties": False,
}


# --- Request -------------------------------------------------------------------------------------

SYSTEM_PREAMBLE = (
    "You rebuild the official table of contents of Tunisian CNP school textbooks from extracted page "
    "material. Follow these rules exactly; they override any intuition about what a chapter should be "
    "called. Return only the JSON described by the output schema: `toc` (or `by_subject` for books that "
    "bundle several subjects), and `notes` stating your sources (page numbers) and every doubt or "
    "positional label.\n\n"
)


def system_blocks() -> list[dict]:
    """Rules first and frozen, so every book after the first reads them from the cache."""
    return [{"type": "text", "text": SYSTEM_PREAMBLE + RULES_FILE.read_text(encoding="utf-8"),
             "cache_control": {"type": "ephemeral"}}]


def book_message(code: str) -> str:
    data = json.loads((EXTRACT_DIR / f"{code}.json").read_text(encoding="utf-8"))
    keep = ("code", "title", "targets", "pages", "front", "back", "headings", "markers", "opener_pages")
    payload = {k: data[k] for k in keep if k in data}
    size = len(json.dumps(payload, ensure_ascii=False))
    if size > 1_500_000:  # ~ the 1M-token context; never truncate silently
        raise ValueError(f"{code}: extract is {size:,} characters, too large for one request")
    return (f"Book {code}. Rebuild its table of contents from this extract:\n\n"
            + json.dumps(payload, ensure_ascii=False))


def request_params(code: str) -> dict:
    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "output_config": {"effort": EFFORT, "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
        "system": system_blocks(),
        "messages": [{"role": "user", "content": book_message(code)}],
    }


# --- Output --------------------------------------------------------------------------------------

def save(code: str, result: BookToc, apply: bool) -> Path:
    """Same file shape as data/cnp/books/<code>.json: title and used_for come from the catalogue/mapping."""
    titles = {b["code"]: b["title"] for b in json.loads(CATALOGUE.read_text(encoding="utf-8"))}
    out: dict[str, Any] = {"code": code, "title": titles.get(code, ""),
                           "used_for": [f"{c}/{s}" for c, s in MAP.get(code, [])]}
    if result.by_subject:
        out["by_subject"] = {s.subject: [n.model_dump() for n in s.toc] for s in result.by_subject}
    else:
        out["toc"] = [n.model_dump() for n in result.toc]
    out["notes"] = result.notes
    target_dir = BOOKS_DIR if apply else PROPOSED_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{code}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def parse_message(code: str, message: Any) -> Optional[BookToc]:
    if message.stop_reason == "refusal":
        print(f"{code}: refused ({getattr(message.stop_details, 'category', None)})")
        return None
    if message.stop_reason == "max_tokens":
        print(f"{code}: output cut at max_tokens ({MAX_TOKENS}); rerun alone with a higher limit")
        return None
    text = next((b.text for b in message.content if b.type == "text"), "")
    return BookToc.model_validate_json(text)


# --- Modes ---------------------------------------------------------------------------------------

def run_sync(client: anthropic.Anthropic, codes: list[str], apply: bool) -> int:
    failures = 0
    for code in codes:
        try:
            # Server-side fallback: if the model declines, the API reruns the request on another model.
            message = client.beta.messages.create(
                **request_params(code),
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            result = parse_message(code, message)
        except (ValueError, FileNotFoundError) as exc:
            print(f"{code}: {exc}")
            result = None
        except anthropic.RateLimitError:
            print(f"{code}: rate limited after retries; rerun later")
            result = None
        except anthropic.APIStatusError as exc:
            print(f"{code}: API error {exc.status_code}: {exc.message}")
            result = None
        if result is None:
            failures += 1
            continue
        usage = message.usage
        print(f"{code}: {len(result.toc) or len(result.by_subject)} top-level items -> {save(code, result, apply)} "
              f"(input {usage.input_tokens}, cached {usage.cache_read_input_tokens}, output {usage.output_tokens})")
    return failures


def submit_batch(client: anthropic.Anthropic, codes: list[str]) -> None:
    requests = [Request(custom_id=code, params=MessageCreateParamsNonStreaming(**request_params(code)))
                for code in codes]
    batch = client.messages.batches.create(requests=requests)
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)
    (BATCHES_DIR / f"{batch.id}.json").write_text(json.dumps(codes), encoding="utf-8")
    print(f"Submitted {len(codes)} books as {batch.id}. Collect with:\n"
          f"  python -m pipeline.cnp.structure_books --collect {batch.id}")


def collect_batch(client: anthropic.Anthropic, batch_id: str, apply: bool, wait: bool) -> int:
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended" or not wait:
            break
        print(f"{batch_id}: {batch.processing_status}, {batch.request_counts.processing} still processing")
        time.sleep(60)
    if batch.processing_status != "ended":
        print(f"{batch_id}: not finished yet ({batch.processing_status}); use --wait or retry later")
        return 1
    failures = 0
    for item in client.messages.batches.results(batch_id):  # results arrive in any order: key by custom_id
        code = item.custom_id
        if item.result.type != "succeeded":
            print(f"{code}: {item.result.type}")
            failures += 1
            continue
        result = parse_message(code, item.result.message)
        if result is None:
            failures += 1
            continue
        print(f"{code}: -> {save(code, result, apply)}")
    return failures


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("codes", nargs="*", help="book codes (CNP), e.g. 222472")
    parser.add_argument("--batch", metavar="NAME", help="submit a whole batch via the Batch API: "
                        "bac, 3eme, lycee12, college, primaire, all")
    parser.add_argument("--collect", metavar="BATCH_ID", help="fetch the results of a submitted batch")
    parser.add_argument("--wait", action="store_true", help="with --collect: poll until the batch ends")
    parser.add_argument("--apply", action="store_true",
                        help="write into data/cnp/books/ (curated files) instead of .cache/cnp/proposed/")
    args = parser.parse_args(argv)

    client = anthropic.Anthropic()
    if args.collect:
        return 1 if collect_batch(client, args.collect, args.apply, args.wait) else 0
    if args.batch:
        submit_batch(client, [c for c in batch_codes(args.batch) if (EXTRACT_DIR / f"{c}.json").exists()])
        return 0
    if not args.codes:
        parser.error("give book codes, --batch NAME or --collect BATCH_ID")
    return 1 if run_sync(client, args.codes, args.apply) else 0


if __name__ == "__main__":
    sys.exit(main())
