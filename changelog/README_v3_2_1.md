# BV-Text v3.2.1 修復說明

- 修復手寫稿儲存後 Streamlit checkbox key (`hw_locked_<note_id>`) 已建立卻再次賦值的例外。
- 儲存成功時先記錄待鎖定旗標並 rerun，在下一次渲染 checkbox 前套用鎖定狀態。
- 更新瀏覽器分頁標題、登入頁、未設定 Supabase 畫面、首頁及主頁品牌標題為 BV-Text。
- 保留使用者自訂文件標題及既有 AI-NOTE 教學／封裝格式描述，避免改動匯入格式相容性。
- 未修改 Supabase 資料庫結構。
