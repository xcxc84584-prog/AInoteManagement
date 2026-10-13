# BV-Text v6.11

- 雲端服務主頁提供 Explorer 樹狀檢視，只下載文件節點 metadata，不預先下載正文。
- 對節點按右鍵選擇「載入」或「刪除」。選擇後於主頁確認；刪除包含子節點、關聯資產及儲存圖片。
- 局部載入沿用既有的父節點與圖片匯入流程，完成後重載工作區。
- 手動雲端上傳加入 `daily_tasks`、`daily_task_checks`，先寫任務，再寫每日勾選。
- 下載原本已包含這兩個資料表。

## 注意
- Supabase 需先設定 `daily_tasks` 與 `daily_task_checks` 的 authenticated CRUD 授權和使用者專屬 RLS。
- Explorer 右鍵動作透過 iframe 跳轉頁面 query string，需於部署後確認瀏覽器 iframe 導航權限；如受限，操作可能無法送達主頁。
- 刪除是不可復原操作，請先備份；跨資料表及 Storage 刪除不是單一交易，失敗可能造成部分刪除。
- 尚未完成實際 Supabase / Streamlit Cloud / 行動裝置整合測試。
