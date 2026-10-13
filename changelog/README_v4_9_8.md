# BV-Text v4.9.8 — SVG regression compatibility

Compared v3.9.11 clipboard handling with v4.9.7. Earlier editor retained the pasted HTML/SVG DOM; newer versions eagerly replaced SVG with img at paste time. Restore native SVG DOM display during editing, and convert to stored SVG asset on save/source transition. Existing unified HRC and other features preserved. Syntax checks are not browser/Supabase tests.
