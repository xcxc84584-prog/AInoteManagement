# v6.4.4 雲端同步功能
- 手動上傳與下載：顯示階段進度（非網路位元組進度）。
- 即時更新：先明確確認下載雲端資料，之後在 Streamlit rerun 時同步本地變更；非跨裝置即時訂閱。
- 重製雲端：只刪除目前登入使用者資料，先刪關聯紀錄，再刪 Storage 圖片；失敗可能部分完成。
- 去重：只自動刪除 schedule_cards、daily_task_checks 中內容完全相同的舊紀錄；有外鍵風險的 notes、daily_tasks、assets 不刪除。
- 403 Storage RLS：請檢查 storage.objects 的 note-images bucket INSERT/UPDATE/SELECT 權限；不建議停用 RLS。
- 注意：即時同步為後續頁面 rerun 才執行；網路失敗時本地資料保留。
