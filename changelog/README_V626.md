# BV-Text v6.2.6 圖片資產修復
- 修正 HTML <img src="asset://UUID"> 被當成文字顯示的問題。
- 保留 Markdown 內 asset://UUID，渲染時使用現有 Supabase asset_image -> data URI 對應。
- 新增以 UUID 為鍵的 IndexedDB Blob 快取，重開同站同瀏覽器優先讀取快取。
- 支援一般 HTTPS 圖片與 SVG data URI；下載失敗（CORS/過期）不保證保存。
- 保留本地資料夾按鈕；需瀏覽器授權，資料夾保存不是離線恢復來源。
- 尚未執行實際瀏覽器端到端測試。
