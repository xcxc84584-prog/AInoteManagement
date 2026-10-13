# BV-Text v6.6 — 雲端與局域網

基於使用者上傳的 v6.4.4（非 v6.5 P2P）。不含 WebRTC。

## 本地 LAN 使用

1. 在局域網內的電腦執行 `python lan_exchange.py --token <自訂長密鑰>`。
2. 在同一網路中的兩台裝置**各自本地執行** BV-Text Streamlit，並登入相同帳號。
3. 進入「雲端與局域網」，輸入服務電腦的 LAN IP（例如 `http://192.168.1.10:8765`）及相同密鑰。
4. 來源端點「傳送本地資料至 LAN」；接收端勾選確認後點「從 LAN 接收並重新載入」。
5. 成功接收或從雲端下載後會執行 `st.rerun()` 重新執行頁面。

## 重要限制

- Streamlit Cloud 上執行的 Python 無法直接連接使用者家庭或校園 LAN IP。**本功能需要 Streamlit 伺服器本地部署在局域網**，而非僅用手機瀏覽雲端網站。
- LAN 傳輸不呼叫 Supabase Database 或 Storage，但目前同帳號登入仍使用 Supabase Auth；如開啟雲端即時更新，其他編輯仍可能上傳雲端。
- LAN relay 使用 HTTP + 配對密鑰，僅適合可信任的私人網路；敏感資料建議使用受保護的 VPN/TLS。不要開放到公網。
- LAN relay 暫存最近一次快照；下一次傳送會覆蓋前一份。接收端採取完整覆蓋，請先備份。
- `st.rerun()` 是 Streamlit 應用重新執行，不等於瀏覽器硬重新整理。實際部署前請確認瀏覽器 IndexedDB 的持久化流程。
- 本版僅做語法與打包驗證，未進行真實雙機測試。
