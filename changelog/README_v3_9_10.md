# BV-Text v3.9.10 — ChatGPT 富文本貼上

在 Markdown 區塊編輯畫面展開「ChatGPT 富文本貼上」，點擊貼上區按 Ctrl+V，按「套用貼上內容」，確認 Markdown 草稿後按原本的「儲存文件」。

支援剪貼簿 HTML 轉 Markdown：標題、粗斜體、超連結、清單、引用、程式碼與表格。支援剪貼簿直接提供的圖片，轉為 asset://UUID 並上傳原有 note-images Storage。沿用既有 .md/.ainote 格式，無需資料庫 migration。

限制：ChatGPT 自訂互動 UI、Canvas、SVG 圖、無法從剪貼簿取得的遠端圖片不保證完整複製；遠端圖片 URL 仍可能失效。複雜巢狀表格與部分 HTML CSS 不能像素級還原。圖片需確認已成功匯入；圖片上傳與文件儲存是兩個步驟。

部署：沿用原 requirements.txt 與 Streamlit 啟動方式。建議先備份既有資料，再以測試 Markdown 區塊測試貼上。
