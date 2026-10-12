# AInoteManagement v1.4｜圖片、表格、共用工作區、帳號註銷

## 功能
- GROUP/SUBFILE 各有自己的工作區，同一層的 MARKDOWN/GRAPH/TABLE 在同一網頁呈現。
- 「瀏覽」模式將 Markdown、表格及私人圖片呈現為筆記。
- 「編輯」模式提供 Markdown 內容、區塊編輯、圖片貼上/拖曳/本地上傳，以及 M×N Markdown 表格（M=1–50，N=1–30）。
- 圖片儲存在私人 `note-images` Bucket，以登入者 UID 為第一層路徑。
- 帳號設定新增「永久註銷帳號」：需要重新輸入密碼、輸入確認文字、勾選確認。由 Supabase Edge Function 驗證身份、刪除私人圖片，最後刪除 Auth 使用者；資料表以 ON DELETE CASCADE 清理。

## 必做部署
1. 先備份筆記與 Supabase 資料庫。
2. 如尚未執行，至 Supabase SQL Editor 執行 `sql/migration_fix_deleted_at.sql`。
3. 在 Supabase 專案部署 `supabase/functions/delete-account/index.ts`，函數名稱必須為 `delete-account`。
   - 建議用 Supabase CLI：`supabase login`、`supabase link --project-ref <你的專案 ref>`、`supabase functions deploy delete-account`。
   - 函數使用平台內建 `SUPABASE_URL`、`SUPABASE_ANON_KEY`、`SUPABASE_SERVICE_ROLE_KEY` 環境變數。
   - **不要**把 `SUPABASE_SERVICE_ROLE_KEY` 放在 Streamlit Secrets、GitHub 或前端。
   - Edge Function 的 JWT 驗證應保持啟用；程式也會透過 `auth.getUser(token)` 再驗證。
4. 用 ZIP 內檔案覆蓋 GitHub 專案，保留 `.git`。`git add . && git commit -m "AInoteManagement v1.4" && git push origin main`。
5. 測試上傳圖片、貼上截圖、插入表格、瀏覽/編輯切換；**最後**使用測試帳號驗證永久註銷。

## 注意
- 永久註銷不可復原，請先下載 .ainote。註銷功能只有 Edge Function 部署後才可用。
- Auth 刪除前會嘗試移除使用者 UID 目錄下的圖片；若刪除過程失敗，可能需要管理員人工清理殘留資料。
- 帳號刪除依賴 `public.notes` 和 `public.assets` 對 `auth.users` 的 ON DELETE CASCADE 外鍵；若資料庫已自行改過，請先確認。
- 目前沒有在實際 Supabase 與 Streamlit Cloud 上完成端到端測試。
