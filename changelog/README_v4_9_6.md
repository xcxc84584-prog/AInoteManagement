# v4.9.6 HRC Pipeline stabilization

- 單一 HRC 模式，保留既有 Explorer、分割、目錄、編輯與提交流程。
- PC / 手機的表格強制採用原生 table display；外層捲動容器負責橫向捲動。
- 數學式解析改為明確檢查結束符號，未閉合公式顯示診斷訊息。
- KaTeX 無法載入時保留 LaTeX 與警告，不會靜默遺失。
- 編輯器的 HTML 貼上空殼會回退剪貼簿文字；遠端圖片載入失敗會顯示警告。
- 成功提交關閉後清理 submitRequest，避免下次開啟重複觸發。

限制：剪貼簿未包含的 SVG 無法重建；手機實機和 Supabase 端對端尚未驗證。
