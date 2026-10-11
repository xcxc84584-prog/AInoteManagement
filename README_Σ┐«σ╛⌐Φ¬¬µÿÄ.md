# AInoteManagement v1.0 修正版

## 修正
- `PGRST204`: `notes.deleted_at` 尚未建立時，刪除與還原會回退到 `is_deleted` 欄位；正式解法仍是執行 SQL migration。
- 調整 Streamlit 主工作區及側邊欄的寬度限制，避免水平溢出。
- 將上方多個檔案分頁按鈕改為響應式文件選擇器，避免按鈕超出畫面。
- 保留 Markdown 編輯器、Supabase Storage、登入、Explorer、資源回收區與匯入匯出。

## 部署前必要步驟
1. Supabase Dashboard → SQL Editor → 執行 `sql/migration_fix_deleted_at.sql`。
2. 確認 SQL 最後顯示 `is_deleted` 和 `deleted_at` 兩個欄位。
3. 解壓縮 ZIP 到原 Git 專案（保留 `.git` 與 Streamlit Cloud Secrets）。
4. `git add . && git commit -m "Fix layout and deleted_at" && git push origin main`
5. 在 Streamlit Cloud 重新整理網站並測試刪除／還原。

注意：未在實際 Supabase 帳號及瀏覽器完成端對端測試。
