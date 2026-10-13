# AInoteManagement v1.4.1 — 修正安裝與記住此裝置

## 已修正
- `requirements.txt` 原本誤含字面 `\n`，使 pip 無法解析 `requests` 依賴；已修正為正確的換行格式。
- 登入頁新增「記住此裝置（自動登入）」。勾選後，使用瀏覽器同來源 localStorage 儲存 Supabase refresh token，重新開啟同瀏覽器可恢復登入；不儲存密碼。
- 登出及帳號永久註銷後，要求清除瀏覽器儲存的登入資訊。
- 保留 v1.4 的圖片、表格、共用工作區、瀏覽/編輯模式及 Edge Function 帳號刪除功能。

## 安全提醒
- localStorage 不是 HttpOnly Cookie，惡意瀏覽器擴充功能或網站 XSS 可能讀取 token。只在信任的私人裝置勾選；公用裝置不要啟用。
- 若要更高安全性，未來應改用受保護的後端 Session 與 HttpOnly/Secure/SameSite Cookie。
- Supabase 的 refresh token 會輪替；本版在刷新後同步更新本機記憶，但網路中斷或多分頁同時刷新仍可能需要重新登入。
- 本版未在你的 Streamlit Cloud 完成實際安裝或端到端測試。

## 部署
1. 將 ZIP 全部檔案覆蓋原專案（保留 `.git` 及雲端 Secrets）。
2. `git add .`、`git commit -m "Fix pip requirements and remember device"`、`git push origin main`。
3. 若 Streamlit Cloud 仍失敗，提供 Manage app → Logs 中 pip 安裝失敗的完整前後 30 行。
4. 帳號永久註銷仍需另外部署 `supabase/functions/delete-account` Edge Function。
