# v6.2.9 Reader clipping fix

- 移除閱讀器 iframe 高度 16000px 的硬上限。
- 依 document、body、editor 實際高度計算 iframe 高度。
- 使用 ResizeObserver 監測內容尺寸，處理表格、數學式、圖片、字型等延遲渲染。
- 加入 image load/error、window resize、font ready 高度更新。
- 高度訊息採 requestAnimationFrame 合併，避免過度重算。
- Python 與兩個元件 JavaScript 語法檢查通過；尚未進行真實 Streamlit 瀏覽器測試。
