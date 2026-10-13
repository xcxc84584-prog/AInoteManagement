# v1.2.1 圖片上傳修正版

修正項目：
1. 以 `c.auth.set_session(access_token, refresh_token)` 建立帶使用者 JWT 的 Supabase Client，讓 PostgREST 和 Storage 共用認證狀態。
2. 修正貼圖元件 `postMessage` 的欄位結構（原先把 `apiVersion` 和 `value` 放在 `data` 內，Streamlit 無法辨識）。
3. 保留 `note-images` 私有 Bucket 與 `UID/UUID.webp` 路徑，避免放寬 RLS。
4. Storage 上傳失敗時在 Streamlit Logs 紀錄錯誤。

## 部署
將 ZIP 解壓覆蓋原專案，保留 `.git` 與 Streamlit Cloud Secrets；執行 `git add .`、`git commit -m "Fix Storage auth and paste component"`、`git push origin main`。
不需要執行新的修改性 SQL。若仍出現 403，請檢查 Streamlit Logs 與 Supabase Storage Logs。

注意：尚未在使用者的 Streamlit Cloud/Supabase 帳號進行端到端測試。


## v6.3.6
- 提高功能選單 popover 的疊放層級，優先於 Sidebar Explorer，兼容 portal 與 sidebar 內渲染。
- 手機瀏覽器仍需實際驗證 Streamlit DOM 結構。
