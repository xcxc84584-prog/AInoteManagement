# v6.18 Cloud Explorer 點選同步

- Cloud Explorer 單擊文件節點時，透過 Streamlit component value 回傳 ID。
- 在 selectbox 建立之前更新 `cloud_tree_selected`，下方「選擇雲端 Explorer 節點」自動對應。
- 展開三角形不會改變目前選取節點。
- 保留原有載入／刪除、資料夾展開及進度條。
- 尚未於真實 Streamlit Cloud 瀏覽器驗證。
