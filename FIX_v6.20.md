# BV-Text v6.20 — Cloud 下載後 Explorer 不顯示

- 局部下載後檢查選取節點是否確實寫入本地資料庫；未寫入時顯示錯誤，而非虛報成功。
- 保留已載入的本地工作區；IndexedDB 確認保存後不再立即清空載入狀態並重新匯入，避免舊快照覆蓋新資料。
- 雲端下載後切回筆記工作區、選取下載節點，並嘗試展開側邊 Explorer。
- 若瀏覽器封鎖側邊欄 DOM 操作，可手動點擊 Streamlit 原生側邊欄展開按鈕。

驗證：Python 編譯、ZIP 完整性；未進行實際 Streamlit Cloud / Supabase 整合測試。
