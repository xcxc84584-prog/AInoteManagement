# BV-Text v6.5

- 新增同帳號 WebRTC P2P 資料交換工作流程：本地快照 JSON（含媒體）、WebRTC DataChannel 傳輸、帳號 UID 驗證、匯入合併或取代、完成後 rerun。
- P2P 傳輸不讀寫 Supabase 資料表或 Storage；登入仍依賴原 Supabase Auth。需手動交換 SDP，不是配對碼。
- 雲端手動下載成功後，以及首次啟用即時更新的雲端下載成功後，呼叫 st.rerun() 重新載入工作區。
- 注意：P2P 使用 STUN，部分 NAT 需要 TURN；iframe 環境可能受瀏覽器安全政策限制。尚未實際雙裝置測試。
- 同帳號限制在匯入時核驗登入 UID；手動 SDP 配對本身不會自動驗證對方身分。請勿向不可信裝置傳送邀請或資料。
