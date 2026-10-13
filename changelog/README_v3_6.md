# BV-Text v3.6

- 修正快速定位：確認後切回筆記工作區，並在內容頂部顯示選定文件的定位面板。
- 新增獨立「📅 行程表」頁面：目標月份、X 軸週次 / Y 軸星期、滑鼠懸浮日期查看按時間排序的行程摘要、點選日期定位、右側滑動行程卡、日期查詢、顯示前 N 張（預設 5）、建立與刪除行程。
- 行程卡資料存於 Supabase `schedule_cards`，由 RLS 限制僅擁有者可存取。
- **部署前必須先在 Supabase SQL Editor 執行 `migrations/20261011_schedule_cards.sql`。**
- 日期與時間以台灣 UTC+08:00 顯示與建立；目前尚未提供修改既有行程的表單。
- 已完成 Python 編譯與 ZIP 完整性檢查；尚未在真實 Streamlit Cloud / Supabase 進行整合測試。
