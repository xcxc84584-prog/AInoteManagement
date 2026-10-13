# BV-Text v4.9.3 — HRC mobile and submit hotfix

- 修復提交按鈕未觸發元件提交的問題：設定 submitRequest 後立即重新執行，等待前端回傳 save_close，後端成功寫入後才退出。
- COM 與 HRC 都優先處理剪貼簿 text/html；MD 保持純文字。
- 手機表格增加獨立橫向捲動容器，避免 table display:block 造成表格版面損壞。
- 修正讀取器 KaTeX 載入失敗時引用未宣告 status 的錯誤，保留原始 LaTeX 並顯示錯誤。
- SVG 仍須來源剪貼簿實際包含 SVG XML 或圖片資料，ChatGPT UI 自訂繪圖元件不一定可透過複製取得 SVG；未宣稱此情況已修復。
- 本版尚未進行 PC/手機實際瀏覽器端到端測試。
