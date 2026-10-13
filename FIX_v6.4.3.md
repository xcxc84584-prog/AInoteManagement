# v6.4.3 修復說明

1. 快捷建立行程：開啟請求只消耗一次；Esc、X、點擊外側或取消不會在後續重跑重新彈出。
2. Explorer 功能：改為一次性開啟請求，關閉後不會被舊 session 狀態重新開啟。
3. daily_tasks / daily_task_checks：新增資料庫授權與 RLS SQL。

## 部署必做
請先在 Supabase SQL Editor 執行 `migrations/20261013_daily_tasks_permissions_v6_4_3.sql`，再重新部署。單純更新 ZIP 不會修改雲端資料庫權限。

## 驗證
測試視窗 Esc / 外側關閉後操作其他功能；重新上傳與下載雲端資料；確認不同帳號不能讀取彼此每日任務。
