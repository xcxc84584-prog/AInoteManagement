# BV-Text v5.0.0 HRC 穩定化與診斷版

## 修正
- HRC 單一模式維持不變，閱讀模式不提供插入圖片。
- SVG 保留原生 DOM 至儲存階段；避免 TOC 更新時重複執行具有副作用的 SVG 序列化。
- 移除 HTML 已包含 SVG 時重複附加原始 SVG 的問題。
- 儲存時只上傳文件實際引用的圖片，使用 SHA-256 去除單次提交的重複上傳。
- 編輯器、閱讀器加入可展開診斷報告與複製按鈕；不紀錄剪貼簿文字內容。
- 數學式與資源錯誤有固定 ID，表格分隔列辨識較寬容。

## 錯誤 ID
HRC-JS-001 JS runtime error；HRC-JS-002 未處理的 Promise 錯誤；HRC-CLIP-001 剪貼簿解析失敗；HRC-SVG-001 SVG 序列化失敗；HRC-SVG-002 SVG XML 驗證失敗；HRC-MATH-001 KaTeX CDN 載入失敗；HRC-MATH-002 公式渲染錯誤；HRC-ASSET-001 資源不存在；HRC-ASSET-002 圖片顯示失敗；HRC-SAVE-001~007 儲存驗證或上傳失敗。

## 注意
此版通過靜態語法與 ZIP 驗證，尚未進行手機實機與 Supabase 端到端驗證。SVG 內容若從來源未被複製到剪貼簿，程式無法重建。舊文件依舊使用 Markdown 中介格式，尚非完整無損的 HTML AST 儲存模型。
