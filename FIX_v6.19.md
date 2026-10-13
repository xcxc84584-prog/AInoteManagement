# v6.19 Cloud Explorer 元件載入修正
- 移除元件內嵌第二層 iframe 與跨層 postMessage，改為 Streamlit Component v1 的單層通訊。
- 使用 DOMParser 解析樹狀預覽、直接綁定節點點擊與展開事件。
- 保留點擊 Cloud Explorer 節點同步下方選擇框的功能。
- 如部署仍顯示舊版，請重啟 Streamlit Cloud 並清除瀏覽器快取。
