# AInoteManagement v1.5｜工作區編輯修正

## 本版變更
1. 恢復工作區正文「💾 儲存工作區正文」按鈕，保留各文字區塊的獨立儲存按鈕。
2. 瀏覽模式以 GROUP 組別為單位，遞迴呈現子文件與其文字、圖片、表格。
3. 編輯模式保留同一父層的共用工作區；GRAPH 區塊不顯示 Markdown 輸入框，改為圖片預覽、從本地上傳／拖曳、剪貼簿圖片貼上、儲存圖片。
4. TABLE 區塊不顯示 Markdown 輸入框，改用 Streamlit `st.data_editor` 類試算表介面，提供儲存表格按鈕。資料庫繼續儲存 Markdown 表格，維持原始資料相容性。
5. 建立表格時輸入 M×N（M=1–50 資料列，N=1–30 欄），建立後即可在表格編輯器填寫。
6. 沿用上一版「記住此裝置」及帳號註銷功能。

## 部署
備份 `.ainote` 與資料庫後，將 ZIP 內容覆蓋 GitHub 專案，保留 `.git` 與 Streamlit Secrets。
`git add . && git commit -m "AInoteManagement v1.5 editor fixes" && git push origin main`

## 限制與注意
- 需要 Streamlit 版本支援 `st.data_editor`、`st.radio`。
- 瀏覽模式切換組別時顯示整組筆記；編輯模式選取文件可編輯該層內容。
- 圖片貼上需在貼上元件內聚焦後按 Ctrl+V；若 Storage RLS 未授權，圖片仍會上傳失敗。
- 圖片存入 Supabase 私人 Storage，表格內容以 Markdown 儲存。
- 本版已通過 Python 語法與 ZIP 完整性檢查，但未連接你的 Supabase 或在 Streamlit Cloud 進行端到端測試。
