# BV-Text v4.9.0 SVG parsing fix

- 修正 Markdown 圖片 URL 中 SVG CSS 括號造成的提前截斷。
- 同時更新圖文編輯器與瀏覽器解析器。
- SVG 仍保留為 Storage 獨立 .svg 檔案，Markdown 使用 asset://UUID。
- 無法取得的圖片維持紅色缺失標記。
- 已進行靜態語法檢查；尚未進行 Streamlit Cloud 端對端測試。
