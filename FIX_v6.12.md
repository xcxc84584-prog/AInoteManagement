# BV-Text v6.12｜雲端 Explorer 樹狀檢視優化

- 雲端 Explorer 與側邊 Explorer 對齊節點圖示：FOLD/GROUP 資料夾、FILE/MARKDOWN 文件、GRAPH 圖片、HANDWRITE 手寫稿、COMPOSITE 圖文、TABLE 表格。
- 加入父子結構連接線，初始只顯示 ROOT 層，點擊三角形展開下一層；支援收合。
- 保留右鍵選單「載入／刪除」，並提供觸控長按。
- 雲端清單載入增加進度提示；單節點載入及刪除使用既有 manual_sync 進度回報函式，修復其在操作前尚未定義的問題。
- 注意：iframe 透過父頁網址參數傳遞操作，仍需在實際 Streamlit Cloud 環境測試瀏覽器安全限制；刪除前仍需確認。
