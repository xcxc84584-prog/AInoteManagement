# BV-Text v4.9.1

- 完全單一編輯「提交」改為要求前端送出最新圖文與圖片，只有資料庫儲存成功才退出。
- 瀏覽模式右鍵「插入圖檔」，以瀏覽器檔案選擇器選擇 PNG/JPEG/GIF/WebP/SVG，插入選取行下一行並保存。
- 編輯工具列新增 HRC / COM / MD 模式。HRC 優先 text/html；COM 採純文字與圖片處理；MD 強制純 Markdown 原始碼。
- HRC/MD 模式使用文件首行隱藏標記保存，COM 不加標記；原始內容仍是 Markdown。
- SVG 經驗證後以 .svg 獨立上傳 Storage，正文使用 asset://UUID。
- 未完成實際 Streamlit Cloud 端到端測試；請先備份後部署。
