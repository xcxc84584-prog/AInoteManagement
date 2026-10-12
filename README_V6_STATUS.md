# BV-Text v6 reconstruction status

This archive preserves the complete v5.1.1 project unchanged and adds a tested lossless Markdown document core in `v6_core/`.

## Verified
- Extract `//[name]//` TOC entries from source without changing Markdown.
- Preserve duplicate TOC names as separate entries.
- Preserve LaTeX source and calculate content SHA-256.
- Split documents at line boundaries without rewriting source.
- Revision counter only advances for actual changes.

Run: `python -m unittest discover -s tests -p test_v6_document.py`

## Not yet implemented / not verified
- Full editor integration with Streamlit, CodeMirror, KaTeX/MathJax fallback, safe SVG sanitization, GFM parsing, IndexedDB, Supabase revision syncing, migration and browser E2E testing.
- The legacy v5.1.1 components remain in use; do not deploy this as a completed v6 replacement.

The file is an incremental development baseline, NOT a finished v6 release.
