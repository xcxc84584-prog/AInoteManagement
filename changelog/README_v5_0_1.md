# BV-Text v5.0.1 — HRC 跨裝置解析修復與診斷

## 修正
- 編輯器與閱讀器採用相同的 `hrcNormalizeSource`、`hrcImageTokens`、`hrcInline`、`renderMarkdown` 版本。
- SVG Data URI 圖片語法優先辨識，不讓 URL 編碼直接落入文字輸出。
- 針對舊文件中意外斷行的 SVG Data URI 增加有限度的合併修復。
- Markdown 表格列間空行容錯，避免手機顯示 `| ... |` 原始碼。
- 診斷報告即使 `errors=[]` 仍會記錄文件預期的表格、圖片、SVG、公式數量和已渲染的節點數。
- 新增 HRC-TABLE-002、HRC-SVG-006、HRC-MATH-003、HRC-MATH-004 錯誤碼。

## 注意
- 目前仍以 Markdown 作為文件中介格式；無法還原原始剪貼簿中不存在的 SVG。
- 未執行 Samsung Internet 與 Streamlit Cloud 實機測試，請先備份 Supabase 資料再部署。
- 診斷記錄僅包含數量和錯誤摘要，不保存完整文件內容。
