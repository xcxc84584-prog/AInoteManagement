# v6.16
- 修正雲端載入時對已建立的 main_page radio widget 直接寫入 session_state 的例外，改為下次 rerun 前設定。
- 選取 FILE/GRAPH/HANDWRITE/COMPOSITE 僅下載本身與引用圖片；選取 GROUP/SUBFILE/FOLD 則下載全部子孫節點。
- 側邊 Explorer「功能」視窗新增對選取文件的雲端化按鈕；原右鍵「雲端化」保留。
- Cloud Explorer 子資料夾沿用資料夾圖示。
- 仍需真實 Supabase、IndexedDB 與手機端整合測試。
