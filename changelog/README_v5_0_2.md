# BV-Text v5.0.2 — SVG Data URI Recovery

基於 v5.0.1，修復舊 HRC 文件中 `![](data\:image/svg+xml;...)` 解析失敗。

- 編輯器與閱讀器共用相同圖片 token 解析邏輯。
- 相容 Markdown 跳脫的 `data\:image`、`\(`、`\)`。
- 支援大型、跨行 SVG Data URI。
- 保留既有表格及 KaTeX 處理。
- `HRC-SVG-008`：偵測並還原被跳脫的 data URI 冒號。
- `HRC-SVG-009`：找不到 SVG 圖片語法結束符號。
- `HRC-ASSET-002`：圖片載入失敗（沿用既有診斷）。

注意：此版本修復解析器，不會自動恢復已從資料庫永久刪除的 SVG，也未經手機實機驗證。
