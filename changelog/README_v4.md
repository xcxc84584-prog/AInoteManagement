# BV-Text v4 — Focus / Incremental Save / Composite

- Explorer 右鍵新增圖文文件（COMPOSITE），可對 FOLD/FILE 使用「完全單一編輯」。
- 編輯模式增加「完全單一編輯」入口，專注編輯時隱藏側邊欄及其他工作臺。
- Markdown、圖文文件、表格支援在專注編輯模式儲存；圖片/手寫稿仍使用既有專用編輯器。
- 工作臺「儲存變更文件」僅更新已修改文件，不再強制下載完整 ZIP；完整備份仍可手動匯出。
- 圖文編輯器貼上時嘗試將內嵌 SVG 轉換為 PNG 資源；一般 HTML/CSS 排版及互動元件無法保證像素級還原。
- Escape 受 Streamlit 與 iframe 焦點限制，請使用 Return 按鈕退出專注模式。
- 未執行瀏覽器端及 Supabase 整合測試。請先備份現有資料再升級。
