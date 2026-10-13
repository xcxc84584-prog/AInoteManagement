# BV-Text v4.8.8 — HTML Rich Clipboard
- 圖文編輯器 Ctrl+V 優先讀取 text/html，缺少 HTML 時回退 text/plain。
- 保留 HTML 表格，辨識 SVG 元素、SVG Data URI、PNG/JPEG/GIF/WebP，轉成待儲存圖片。
- SVG 以原始 SVG 位元組儲存到 Supabase Storage `note-images`，資料庫僅記錄 `asset://UUID` 參照。
- 辨識 MathML 的 TeX annotation、data-math / data-tex / data-latex，轉為可儲存 LaTeX。
- 缺少來源的圖片顯示紅色 ❗；不捏造或刪除其缺失提示。
- 支援在 Markdown 原始碼模式貼上富文本，轉成 Markdown。
- 貼上後請按「儲存圖文文件」，再重新開啟驗證。
- 限制：ChatGPT 剪貼簿若不包含圖片位元組或 SVG，無法從文字推回原圖；遠端 URL 可能失效。HTML/CSS 複雜排版及互動圖表不能保證逐像素一致。
- 本次僅通過語法驗證，未進行 Streamlit Cloud 端到端測試。
