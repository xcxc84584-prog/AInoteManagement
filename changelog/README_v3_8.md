# BV-Text v3.8

1. 行程可勾選「無指定時間」；資料儲存於 `schedule_date`，`scheduled_at` 設為 NULL。
2. 有指定時間的行程按時間升序；無時間的行程排在後方並按 `created_at` 升序（同時建立則以 id 排序）。
3. 月曆可切換顯示日期或待處理數；待處理數為當天尚未標記「已完成」的行程卡數量。
4. 行程卡新增「已完成」勾選，可在右側直接更新狀態。
5. **必須先在 Supabase SQL Editor 執行 `migrations/20261011_schedule_cards_v3_8.sql`，再部署新程式。**
