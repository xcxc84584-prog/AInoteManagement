# BV-Text v6.17 修正

- 修復 Cloud Explorer 載入時 `cannot import name cloud_selection_ids from manual_sync`。
- 節點選取範圍改由 `app.py` 本地函式計算，不再依賴 `manual_sync.cloud_selection_ids` 匯出。
- FILE/GRAPH/HANDWRITE/COMPOSITE 僅載入所選文件；GROUP/FOLD/SUBFILE 載入其所有後代。
- `manual_sync.py` 仍保留原有函式，避免其他呼叫路徑失效。
- 部署時必須整份更新 app.py 和 manual_sync.py 並重啟應用，避免混用版本。
