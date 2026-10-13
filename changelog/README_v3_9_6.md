# BV-Text v3.9.6

- 初始教學提示詞：每次 AI 回應僅允許一個根 GROUP/FOLD；禁止 SUBFILE、巢狀 FOLD，所有 FILE 直接屬於根 FOLD。
- 教學用 structure.json 範例同步改為單層。
- 空工作臺：新增文件時可選「空 FOLD」或「教學 FOLD」，並可輸入名稱；教學 FOLD 內只有一個直接子 FILE「使用說明書」。
- 手機本地備份：對 createWritable 的 NotAllowedError/SecurityError/NotSupportedError 退回一般下載；不將下載視為可驗證的資料夾寫入。

部署：解壓覆蓋原專案，git add .; git commit -m "BV-Text v3.9.6"; git push origin main

注意：尚未於實際手機或 Streamlit Cloud 執行端對端驗證。
