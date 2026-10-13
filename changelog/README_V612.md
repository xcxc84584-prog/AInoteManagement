# BV-Text v6.1.2 development preview

- Mouse-click confirmation for TOC; removed Ctrl+T in editor and reader.
- Added multi-line $$...$$ display LaTeX rendering through KaTeX.
- Explorer reads TOC entries from the same IndexedDB table; BroadcastChannel refreshes branches.
- Explorer navigation passes TOC UUID to editor and reader; both resolve via BV61TOC.locate.
- Ctrl+D deletes a selected TOC entry in Explorer, not a file.

Limitations: browser-local TOC cannot sync across devices or unrelated browser origins; rich text source conversion and line-to-rendered-block mapping may not be exact for complex tables/code blocks; browser end-to-end testing not performed.
