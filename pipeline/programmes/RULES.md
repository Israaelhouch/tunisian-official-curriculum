# Extract learning objectives from an official Tunisian programme

Rules given to Claude (and used for review) when turning one programme PDF into `data/programmes/<class>__<SUBJECT>.json`.

Input folder `pages/<class>__<SUBJECT>/`: the pages of the official Ministry programme for ONE class and subject:
- `text.txt`: the text layer of each page (`[pN]` markers) — use it for exact wording;
- `pNNN.png`: the page images — use them for the table layout (which cell belongs to which column/row),
  because the text layer of multi-column tables is often interleaved.

Output `data/programmes/<class>__<SUBJECT>.json` (the final file also carries `source`: document, issuer, url, pages; `blocks` are stored as `units`):
```json
{
  "class": "bac-informatique",
  "subject": "MATH",
  "blocks": [
    {"domain": "Analyse", "topic": "Limites et continuité",
     "contents": ["Opérations sur les limites, limites et ordre, ..."],
     "objectives": ["..."]}
  ],
  "notes": "how the programme is organised, pages used, anything unclear"
}
```

Rules
1. **Verbatim.** Copy every item exactly as printed (same language, same words). Never paraphrase, summarise,
   translate, merge or complete an item. Fix only obvious extraction artefacts (broken hyphenation, stray line
   breaks, a formula lost in extraction may be written in plain notation or marked "[formula]").
2. **Follow the programme's own organisation**, in page order:
   - `domain`: the large division if the programme has one (e.g. "Analyse", "Géométrie", "Thème II. ..."),
     otherwise null.
   - `topic`: the unit inside it (e.g. "Limites et continuité", a chapter/theme title), or null if the
     objectives are given for the whole domain.
   - `contents`: the "Contenus" / "Contenu disciplinaire" items for that unit ([] if none).
   - `objectives`: the items listed as objectives / skills: columns or headings such as "Objectifs",
     "Aptitudes à développer", "Compétences", "Capacités", "L'élève doit être capable de ..." ([] if none).
3. **Exclude**: suggested activities ("Activités envisageables"), durations/weeks, general introductions,
   pedagogical recommendations, comments to teachers, evaluation guidelines.
4. If objectives are given once for a whole domain (not per topic), make one block with `topic: null` holding
   them, and keep the per-topic blocks with their contents and empty objectives.
5. Never invent an objective. If a cell is unreadable, skip it and say so in notes.
6. Validate the JSON with a small Python check (parses; every block has the 4 keys). Don't touch other files.
7. When objectives are printed in one cell for a whole theme (SVT), keep them at theme level (`topic: null`);
   never split them between units by position.
