# Official programmes (learning objectives)

The Ministry of Education publishes the official programme of each subject (education.gov.tn → Programmes,
PDFs on edunet.tn). For each class subject it lists the contents to teach and the learning objectives
("Objectifs", "Aptitudes à développer"…). This layer adds them to the dataset, verbatim.

1. **Extract** (Claude, per programme PDF, rules in [RULES.md](RULES.md)): page text for the exact wording,
   page images for the table layout → `data/programmes/<class>__<SUBJECT>.json`, with its source
   (document, URL, pages) and review notes. Every file is checked against the PDF.
2. **Merge**: `python -m pipeline.programmes.merge_programmes` writes a `programme` into each class subject of
   `data/curriculum/` (run after `pipeline.cnp.merge_chapters`), then `python scripts/export_curriculum.py`.

A programme unit is linked to a chapter only when the names are near-identical (accents, numbering and
articles ignored). The 2011 programmes often word things differently from the textbooks ("Dérivation" vs
"Dérivabilité"), so many units stay unlinked rather than being matched by guess.

Coverage so far: the Bac pilot (Mathématiques, Sciences physiques, SVT; 13 class subjects, 847 objectives).
