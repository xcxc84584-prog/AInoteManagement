# BV-Text v4.7.1
修復圖文文件儲存失敗：完全單一編輯使用 a,b,c=st.columns(...) 時，在 Python 模組全域覆寫原本指向 LocalDB 的 c，導致 update_note 中的 c.table('notes') 誤呼叫 Streamlit 的 table 元件並產生 pandas.DataFrame 型別錯誤。
已將三個 UI 欄位變數重新命名，避免覆寫資料庫連線。
本版保留 v4.7 的其他功能。尚未完成線上瀏覽器端測試。
