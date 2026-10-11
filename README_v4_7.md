# BV-Text v4.7
- 修正雲端 notes_kind_check 不支援 COMPOSITE 的部署問題：先於 Supabase SQL Editor 執行 sql/migration_v4_7.sql。
- 手機 Markdown 表格允許橫向捲動，避免欄位遭擠壓。
- Explorer 增加 ← Previous，記錄工作階段內導覽歷史。
- 以 URL query params 保存目前選取文件與單一閱讀／編輯區，重新整理後恢復。
- 注意：雲端資料庫的 migration 需要手動執行；頁面內精確捲動座標尚未持久化。
