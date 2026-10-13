# BV-Text v6.1.4 — Nested LaTeX delimiter fix

修正 ChatGPT 貼上 `\[$$...$$\]` 和 `$$\[...\]$$` 的顯示問題。

- 修改 `components/composite_editor/index.html` 與 `components/composite_reader/index.html`：在 Markdown 渲染階段統一巢狀數學式定界符，避免內層 `$$` 被先行解析；保留原始 Markdown。
- 修改 `app.py` 的 `show_markdown()`，使 Streamlit 顯示路徑同樣支援。
- 避開三反引號及三波浪號程式碼區塊中的正規化。
- 新增 `tests/test_nested_math_v614.py`。

測試：Python 語法、編輯/閱讀 JavaScript 語法及 pytest（6 tests）通過。尚未在真實 PC/手機瀏覽器執行端到端測試。

測試輸入：

```text
\[$$CPI=1+0.2\times0.4\times3$$\]
\[$$CPI=\frac{\text{Total Clock Cycles}}{\text{Instruction Count}}$$\]
```

請先備份既有資料，再於測試環境解壓並部署。
