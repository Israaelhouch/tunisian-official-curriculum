# Curriculum notes

Generated 2026-10-09 by `scripts/export_curriculum.py` from `data/curriculum/*.json`; data in `curriculum.json`.
30 classes · 442 class subjects · 289 with chapters · 2892 chapters. Subjects: decrees 2019-1085 / 2021-143. Chapters: official CNP textbooks, names as printed, never inferred.

## Subjects without chapters (no CNP textbook)
- **Lycée (secondaire):** ALGO (3eme-informatique, bac-informatique); ARTPL (12 classes); CIVIQ (3eme-sport); ECO (2eme-economie-services, 3eme-economie-gestion, bac-economie-gestion); EPS (21 classes); GEO (2eme-sport, 3eme-sport, bac-sport); HIST (2eme-sport, 3eme-sport, bac-sport); INFO (19 classes); ISLAM (3eme-sport); MUSIQ (12 classes); PHYS (2eme-sport, 3eme-sport, bac-sport); PORT (12 classes); RUSSE (6 classes); SPORTSPEC (4 classes); STI (3eme-informatique, bac-informatique)
- **Collège (enseignement de base):** ARTPL (7eme-base, 8eme-base, 9eme-base); EPS (7eme-base, 8eme-base, 9eme-base); MUSIQ (7eme-base, 8eme-base, 9eme-base); THEATRE (7eme-base, 8eme-base, 9eme-base)
- **Primaire:** ANGL (4eme-primaire, 6eme-primaire); ARTPL (6 classes); CIVIQ (6eme-primaire); EPS (6 classes); EVEIL (1ere-primaire, 2eme-primaire); FRAN (2eme-primaire, 3eme-primaire); ISLAM (6 classes); MUSIQ (6 classes); TECHNO (6 classes)

## Chapters missing (title unreadable in the textbook, not guessed)
- **Lycée (secondaire):** 1ere-sport ARAB (2), 1ere-secondaire ARAB (2), 2eme-technologie-informatique ISLAM (1), 2eme-technologie-informatique ARAB (1), 2eme-technologie-informatique ANGL (1), 2eme-sport ISLAM (1), 2eme-sport ANGL (1), 2eme-sciences ISLAM (1), 2eme-sciences ARAB (1), 2eme-sciences ANGL (1), 2eme-lettres ISLAM (1), 2eme-lettres HIST (1), 2eme-lettres ARAB (1), 2eme-lettres ANGL (1), 2eme-economie-services ISLAM (1), 2eme-economie-services HIST (1), 2eme-economie-services ARAB (1), 2eme-economie-services ANGL (1)
- **Collège (enseignement de base):** 8eme-base FRAN (6), 8eme-base ARAB (4), 9eme-base ARAB (2), 9eme-base PHYS (1), 9eme-base ISLAM (1), 8eme-base ISLAM (1), 7eme-base PHYS (1), 7eme-base ISLAM (1), 7eme-base CIVIQ (1), 7eme-base ARAB (1)
- **Primaire:** 5eme-primaire ARAB (34), 3eme-primaire ARAB (33), 6eme-primaire MATH (16), 3eme-primaire MATH (16), 6eme-primaire ARAB (9), 4eme-primaire ARAB (7), 4eme-primaire MATH (5), 6eme-primaire EVEIL (2), 5eme-primaire MATH (1), 3eme-primaire EVEIL (1)

## Learning objectives (official programmes)
- 13 class subjects so far (847 objectives): bac-economie-gestion MATH, bac-informatique MATH, bac-informatique PHYS, bac-lettres MATH, bac-lettres SVT, bac-mathematiques MATH, bac-mathematiques PHYS, bac-mathematiques SVT, bac-sciences-experimentales SVT, bac-sciences-experimentales PHYS, bac-sciences-experimentales MATH, bac-techniques MATH, bac-techniques PHYS.
- 71 of 164 programme topics are linked to a chapter (near-identical names only); the 2011 programmes often word topics differently from the textbooks, so the others are left unlinked.

## Untitled groupings kept (their chapters are named)
- 1ere-primaire MATH (6), 2eme-primaire MATH (6), 5eme-primaire MATH (5), 6eme-primaire ARAB (1), 7eme-base ANGL (5), 8eme-base ANGL (5), 8eme-base TECHNO (3)

## To check
- Chinese and Russian titles were decoded from a broken font encoding.
- Borderline chapter levels: `data/cnp/chapter_depth.json`. Per-book sources and doubts: `data/cnp/books/<code>.json` (`notes`).
