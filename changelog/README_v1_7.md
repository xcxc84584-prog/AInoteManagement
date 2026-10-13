# AInoteManagement v1.7 — 批量存檔與快速定位

## 功能
- 編輯模式：同一工作區所有區塊連續排列，不再分成展開框。
- 批量儲存工作區：一次儲存正文、文字區塊及表格，逐項確認 Supabase 更新回傳的資料列，並顯示成功數量、失敗數量及各項錯誤。
- 圖片：保留專用貼上、拖曳、上傳及「儲存圖片」按鈕，儲存成功提示可跨頁面重新執行顯示。
- 瀏覽模式：以 GROUP 組別為單位，新增「快速定位目錄」，點選子文件名稱跳至對應章節。
- 修正 requirements.txt 中不正確的字面 `\n`，補上 pandas 依賴；將舊版 use_container_width 更新為 width。

## 部署
1. 先備份重要筆記及資料庫。
2. 解壓縮覆蓋原專案，保留 `.git` 和部署 Secrets。
3. 執行 `git add .`、`git commit -m "AInoteManagement v1.7 batch save and TOC"`、`git push origin main`。
4. 在 Streamlit Cloud 確認部署完成，再測試新增文字／表格、批量儲存、重新載入驗證內容、快速定位與圖片儲存。

## 注意
- 批量儲存不是資料庫原子交易；部分失敗時，已成功的區塊不會自動回滾，失敗項目可修正後重試。
- 圖片上傳需另按「儲存圖片」，不會在批量儲存時自動上傳尚未提交的剪貼簿資料。
- 尚未在實際 Supabase / Streamlit Cloud 進行端到端測試。
