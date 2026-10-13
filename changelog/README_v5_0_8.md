# BV-Text v5.0.8 — Mobile SVG and Math safety patch

- Synchronize reader SVG recovery with editor (encoded SVG, escaped colon, missing closing Markdown parenthesis).
- Rejoin wrapped SVG Data URIs before Markdown rendering.
- Stop destructive heuristic removal of formula-adjacent text.
- Limit delimiter-less TeX recovery to standalone formula lines.

Note: Existing stored duplicate math text may need source-level correction; this patch does not silently erase saved content. Device testing has not been performed.
