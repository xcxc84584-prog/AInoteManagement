# BV-Text v3.9.9｜行程表本地備份與載入

- 行程表可使用與筆記相同的本地資料夾授權／手機下載機制，匯出獨立 `.bvcalendar.json` 檔案。
- 可透過本地檔案選擇器上傳並載入行程表。
- 提供「合併行程（相同 ID 更新）」及「取代現有行程表」。
- 備份包含日期、時間、標題、說明、完成狀態、批次 tag、批次 ID。
- 匯入會先驗證格式、日期與唯一 ID，使用 SQLite 交易避免部分匯入。
- 不會因本地備份自動上傳 Supabase。
- 手機瀏覽器啟動下載後請確認檔案存在。

部署：git add . && git commit -m "BV-Text v3.9.9 schedule local backup and import" && git push origin main

尚未於手機實機與 Streamlit Cloud 進行端對端驗證。
