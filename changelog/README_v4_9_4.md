# BV-Text v4.9.4 — ChatGPT Clipboard Pipeline Refactor

## 目標
保留既有 Explorer、分割、目錄化、HRC/COM/MD、圖文瀏覽、圖片上傳、提交儲存後關閉等功能，重構 HRC/COM 貼上路徑，優先處理 ChatGPT 複製內容。

## 變更
- 將富文本貼上流程集中於 `pasteChatGPT()`，與 Markdown 顯示/導覽分離。
- 優先解析 `text/html`；缺少時使用 `text/plain`。
- HTML 內 `<svg>` 先序列化為 SVG 原始位元組（Data URI 僅為上傳前的暫存格式），上傳時保存為 `.svg`，正文保存 `asset://UUID`。
- 支援 `<img src="data:image/...">`、`<object>/<embed>` 內嵌 SVG、CSS `background-image` 中 SVG Data URI，以及剪貼簿圖片檔案回退。
- HTML 表格沿用現有表格 Markdown 序列化，MathML 的 LaTeX annotation 沿用 `cleanMathNodes()`。
- HRC/COM 在 Markdown 原始碼編輯區也使用富文本貼上；MD 模式仍為純文字。
- 缺失媒體顯示 ❗，並於貼上狀態列顯示剪貼簿型別，方便定位 ChatGPT 複製問題。
- 修正上傳圖片參照替換時 `clipboard-image://1` 意外匹配 `clipboard-image://10` 的風險。

## 尚未解決或限制
- ChatGPT 自訂 UI、Canvas 圖表或 `<canvas>` 若未提供 SVG/影像位元組，無法無損還原。
- 複雜 CSS/HTML 的完整視覺排版尚未封存為原始 HTML sidecar；目前仍以 Markdown 為主儲存格式。
- 遠端 URL 圖片仍依賴來源存活，不能保證長期可用。
- 本版已通過 Python/JavaScript 語法檢查，未在 Streamlit Cloud 與真實手機完成端到端測試。
