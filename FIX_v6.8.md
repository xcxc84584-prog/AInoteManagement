# v6.8 變更紀錄
- 匯入器支援不包含 GROUP 根節點的單一 COMPOSITE 圖文文件；仍保留舊 GROUP 封包支援。
- 支援 structure.json 沒有 content 時從 documents/<id>.md 讀取。
- 瀏覽／編輯工作區以優先序為基礎，只渲染焦點節點與 ±1 節點，切換時顯示階段進度條。
- 擴充 AI 提示詞，列出 manifest.json、structure.json、documents、assets 的具體結構。
- 目前仍先載入節點中繼資料與部分資產索引；並非完整資料庫層級 lazy loading。
- 尚未在實際 Streamlit Cloud / 多裝置執行端到端測試。
