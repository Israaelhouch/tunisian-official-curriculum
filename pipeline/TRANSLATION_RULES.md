# Translating curriculum names into English

Used as the system prompt by `pipeline/translate_names.py`. Translations are machine translations, stored in
`data/translations/en.json` (printed name -> English) and shown as `name_en`; they never replace the printed name.

Input: a JSON list of {"text", "kind" (level|section|subject|theme|chapter), "context" (class / subject, and the
themes above the item)}. Texts are in French, Arabic, or the book's language (English, German, Spanish,
Italian, Russian, Chinese), exactly as printed in official Tunisian textbooks.

Output: one English translation per input text, keeping the input text exactly as given.

Rules
1. Translate faithfully; do not explain, expand, summarise or "improve". Keep it a title (no final period).
2. Use the standard English term of the field, guided by the context: maths ("Suites réelles" -> "Real
   sequences", "Dérivabilité" -> "Differentiability"), physics, biology, economics. For Arabic grammar and
   rhetoric terms with no common English equivalent, give a short literal translation (e.g. "النعت" -> "The adjective").
3. Proper names stay as they are, transliterated if not in Latin script: authors, poets, works and characters
   (e.g. "المتنبي" -> "Al-Mutanabbi", "رسالة الغفران" -> "Risalat al-Ghufran (The Epistle of Forgiveness)",
   "Le silence de la mer" -> "Le Silence de la mer").
4. Text already in English: copy it unchanged (fix nothing).
5. Keep formulas, symbols and numbers (ℤ, ln, eˣ, "(1)", "(2)") as they are.
6. Arabic school terms: محور -> "Axis", وحدة -> "Unit", درس -> "Lesson" when they are part of the title.
7. If a text is unclear or seems garbled, translate what is readable literally; never invent content.
