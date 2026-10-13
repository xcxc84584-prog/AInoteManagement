# BV-Text v6.1.5 SVG / math coexistence fix

- Protect Markdown image tokens before LaTeX parsing, in both reader and editor.
- Locate closing SVG XML before looking for the Markdown image closing parenthesis; support escaped `data\:image/svg+xml`.
- Preserve raw SVG data URI whitespace rather than stripping meaningful SVG text spaces.
- Add secondary KaTeX CDN for devices that cannot reach jsDelivr.
- Preserve the original document source. No destructive normalization of saved Markdown.

## Manual verification still required
Test on real desktop and mobile browsers with raw and percent-encoded SVG data URLs, SVG containing parentheses and dollar signs, and `\[$$...$$\]` math in the same document. Browser connectivity and CSP can still prevent CDN loading.
