# AInoteManagement v1.7.1 — 儲存與快速定位修復

## 已修正
- 修正瀏覽模式 `NameError: name html is not defined`：新增 `import html`。
- 批量存檔逐筆執行 UPDATE，並再 SELECT 核對 Supabase 儲存的 Markdown / 表格內容；只有核對相同才算成功。
- 儲存結果列出成功數、失敗數、UTC 時間與每個失敗區塊的錯誤訊息。
- 保留同層連續式工作區、圖片貼上與上傳、表格編輯、GROUP 快速定位、登入記憶。

## 部署
解壓縮覆蓋原專案（保留 `.git`），執行：

```powershell
git add .
git commit -m "Fix TOC NameError and verify batch save"
git push origin main
```

## 測試
1. 開啟 GROUP 瀏覽模式，確認快速定位目錄不再產生 NameError。
2. 切換編輯模式，在工作區正文輸入測試文字，按「批量儲存工作區」。
3. 檢查成功提示（含 UTC 時間），重新整理網頁，確認內容仍存在。
4. 新增 Markdown 與表格區塊後重複測試；失敗時將畫面上的錯誤類型與 Manage app → Logs 貼回。
5. 圖片須透過圖片區的「儲存圖片」獨立上傳。

**注意：** 本版未連線至你的 Supabase 進行端到端測試。若 RLS、資料庫欄位或 Storage 權限有問題，仍會失敗，但現在會提供具體錯誤。
