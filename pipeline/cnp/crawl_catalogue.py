"""Step 1 — list the official CNP student textbooks.

Queries the CNP catalogue search (cnp.com.tn, "تحميل الكتب") for every class and
writes data/cnp/catalogue.json: [{cycle, classe, code, title, pdfs: [...]}, ...].
cycle 1 = enseignement de base (1ère–9ème), 2 = secondaire (1ère–4ème),
4 = collèges techniques (8ème–9ème; not used by the curriculum).

Usage: python -m pipeline.cnp.crawl_catalogue
"""

import html
import json
import re
import subprocess
import time

from pipeline.cnp.paths import CATALOGUE, CATALOGUE_PAGES_DIR

SEARCH_URL = "https://www.cnp.com.tn/CNP1/web/arabic/biblio/resultat_man.jsp"
PDF_BASE = "https://www.cnp.com.tn/arabic/PDF/"
QUERIES = [(1, c) for c in range(1, 10)] + [(2, c) for c in range(1, 5)] + [(4, c) for c in (8, 9)]


def fetch(cycle: int, classe: int) -> str:
    out = CATALOGUE_PAGES_DIR / f"q_{cycle}_{classe}.html"
    subprocess.run(["curl", "-sS", "-m", "60", "-A", "Mozilla/5.0", "-L", "-o", str(out), "-X", "POST",
                    SEARCH_URL, "--data", f"CYCLE={cycle}&CLASSE={classe}&MATIERE=__&type=eleve"], check=True)
    return out.read_bytes().decode("utf-8", "ignore")


def parse(page: str, cycle: int, classe: int) -> list[dict]:
    """Result rows: code | title | 'Partie 1' link; extra rows hold further PDF parts."""
    books, current = [], None
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S | re.I):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)]
        if len(cells) >= 3 and re.fullmatch(r"\d{5,7}", cells[0]):
            current = {"cycle": cycle, "classe": classe, "code": cells[0], "title": cells[1], "pdfs": []}
            books.append(current)
        if current is not None:
            for part in re.findall(r"PDF/([^\s\"'>]+\.pdf)", row, re.I):
                if PDF_BASE + part not in current["pdfs"]:
                    current["pdfs"].append(PDF_BASE + part)
    return books


def main() -> None:
    books = []
    for cycle, classe in QUERIES:
        found = parse(fetch(cycle, classe), cycle, classe)
        books += found
        print(f"cycle={cycle} classe={classe}: {len(found)} books", flush=True)
        time.sleep(2)
    CATALOGUE.write_text(json.dumps(books, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(books)} books, {sum(len(b['pdfs']) for b in books)} PDF parts -> {CATALOGUE}")


if __name__ == "__main__":
    main()
