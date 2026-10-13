# BV-Text v6.2.7

Streamlit 應用。啟動：`streamlit run app.py`。

更新日誌：`changelog/`。資料庫遷移：`migrations/`。

## 本次更新
- Explorer 的 Previous 旁加入 CloseSidebar；收合後主畫面提供 OpenSidebar。
- 移除手動修正點與修正模式，保留目錄化與分割功能。
- 圖片（PNG/JPEG/WebP/GIF）與 SVG：成功取得後自動保存到瀏覽器 IndexedDB。
- 支援 `asset://UUID` 對應後端提供的圖片內容；已快取圖片可於相同站點、相同瀏覽器中重新載入。
- 使用者點擊「授權圖片資料夾」授權後，新圖片自動寫入資料夾；權限被收回時需重新授權。
- 遠端圖片若受 CORS、連結失效、iframe 限制，無法保證擷取。
- 目前不會從本地資料夾自動反向讀取圖片；離線恢復依賴 IndexedDB。
- 已做 Python 編譯及元件 JavaScript 語法檢查；尚未做手機／PC 端對端測試。
