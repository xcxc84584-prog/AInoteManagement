# BV-Text v3.9 — Local-first 雙模式

## 模式

- **SQLite**：設定 `BV_TEXT_STORAGE_MODE=sqlite`，使用 `BV_TEXT_DATA_DIR` 指定固定資料夾；預設為使用者主目錄下 `BV-Text-Data/bvtext.sqlite3`。筆記、行程與圖片存 SQLite。
- **IndexedDB**：設定 `BV_TEXT_STORAGE_MODE=browser`，網站在目前瀏覽器 IndexedDB 儲存快照，Python 僅於目前 Streamlit session 中保留工作資料。瀏覽器資料不會因 Supabase 同步自動更新。
- **Supabase**：仍提供登入和 Token 更新。只有使用者明確按「手動上傳雲端」才將筆記、圖片與行程資料上傳；「手動下載雲端」會覆蓋本地資料。

## 本機 Windows 啟動

```powershell
$env:BV_TEXT_STORAGE_MODE="sqlite"
$env:BV_TEXT_DATA_DIR="D:\BV-Text-Data"
streamlit run app.py
```

資料庫位置為 `D:\BV-Text-Data\bvtext.sqlite3`。請備份該檔案。**固定路徑位於執行 Streamlit 的電腦**。

## Streamlit Cloud Secrets

```toml
BV_TEXT_STORAGE_MODE = "browser"
SUPABASE_URL = "https://...supabase.co"
SUPABASE_ANON_KEY = "..."
```

瀏覽器 IndexedDB 的資料只屬於目前網站來源、瀏覽器及登入使用者。清除網站資料、使用無痕視窗或更換瀏覽器都可能導致資料遺失。請定期下載 `.ainote` 或「本地快照 JSON」備份。

## 手動同步

登入後在左側功能區展開「手動雲端同步」，勾選確認才可按「上傳」或「下載」。上傳採 ID 合併，不刪除雲端多出的資料；下載會取代本地資料。請避免多裝置並行編輯造成衝突。第一次使用新版，舊有雲端文件需**手動下載雲端**，不會自動下載。

## 已知限制

- 仍需要 Supabase 登入，因此尚不支援完全離線登入。
- IndexedDB 透過 Streamlit 自訂元件傳送 JSON 快照，圖片較多時可能遇到瀏覽器配額、元件訊息大小或延遲限制。大量資料建議使用 SQLite 模式。
- IndexedDB 資料同步到瀏覽器可能需要等待元件確認；離開頁面前請確認「正在寫入」提示消失。
- 雲端同步不是交易式多表原子提交；若部分上傳失敗，需重新同步並檢查資料。
- 本次完成本地 SQLite 測試、Python 語法檢查；未執行實際 Supabase／Streamlit Cloud 端對端測試。
