# AInoteManagement v2.0｜圖片載入與切換效能

## 修正
- 圖片改由已登入的 Supabase Storage API 下載位元組，再交給 Streamlit 顯示；不再依賴可能是相對路徑或過期的 signed URL。
- 每個使用者的圖片在目前 Streamlit session 內快取五分鐘，避免瀏覽/編輯切換時重複下載；最多保留約 25 張圖片的快取項目。
- 圖片剪貼簿內容保存在 Streamlit session_state，避免重新執行後貼上資料消失；儲存成功後清除。
- 貼上監聽從指定元素擴展到文件，減少未聚焦造成的貼上失敗。
- 僅當存在圖片資產引用時讀取 assets metadata。
- Storage 下載失敗時寫入 Cloud Logs，並在介面顯示警告。

## 效能改善建議（尚未全部實作）
- 對 GROUP 的內容改用分頁/延遲載入，避免一次渲染所有圖片和表格。
- Explorer 建立文件採用 optimistic UI 並在背景確認，需另外設計衝突/回滾處理。
- 使用資料庫索引 `(owner_id,parent_id,position)`，並限制每次資料查詢的範圍。

## 部署
解壓縮覆蓋原專案，保留 `.git` 與 Secrets：`git add .`、`git commit -m "Fix image loading and improve switching v2.0"`、`git push origin main`。
若仍無法顯示圖片，請查看 Streamlit Cloud Logs 中 `Image download failed`，確認 Supabase Storage policy 允許登入使用者讀取 `note-images/<uid>/...`。

已做 Python 語法檢查與 ZIP 完整性檢查，未進行真實 Supabase 端到端測試。
