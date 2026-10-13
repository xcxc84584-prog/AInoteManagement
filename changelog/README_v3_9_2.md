# BV-Text v3.9.2 — 圖片及手寫稿儲存修正

修正 `LocalDB.storage` 必須是 property 而非方法的相容性問題。新增圖片、手寫稿上傳/下載/刪除回歸測試，並在 app 啟動時檢查 storage 介面，避免在儲存途中才失敗。

## 部署
1. 備份目前本地 SQLite 資料夾或瀏覽器工作區。
2. 解壓縮覆蓋全部專案檔案（特別是 `local_backend.py`、`app.py`）。
3. git add . && git commit -m "Fix local media storage v3.9.2" && git push origin main
4. Streamlit Cloud 重新啟動 App 並重新整理瀏覽器。
5. 測試新增圖片與手寫稿、重新整理後讀取。

注意：若部署後仍有 `function object has no attribute from_`，請確認 Streamlit Cloud 部署分支與目前程式碼一致，並查看 traceback 中的實際檔案位置。

先前失敗的圖片儲存通常不會產生附件：因為 `from_` 在上傳前就拋出例外。若另有其他上傳失敗情境，才可能產生孤兒檔案，請勿直接清空 Storage bucket。
