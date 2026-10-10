# AInoteManagement v1.2

更新：Explorer 固定高度與內部捲動；在文件樹中直接輸入新增/重新命名；中央僅保留 Markdown 編輯器；刪除及還原逐筆檢查資料庫結果，錯誤詳情寫入 Streamlit Logs。

## 部署

將 ZIP 內所有檔案覆蓋原 GitHub 專案（保留 .git），執行 `git add . && git commit -m "Fix Explorer UI and delete" && git push origin main`。

請先確認已執行 `sql/migration_v1_1.sql`。若刪除仍失敗，從 Streamlit Cloud Logs 擷取 `Explorer action failed` 後的 traceback，勿公開金鑰。

注意：此版本未經線上 Supabase 實測。刪除仍為軟刪除，需 UPDATE 權限及對應 RLS policy。
