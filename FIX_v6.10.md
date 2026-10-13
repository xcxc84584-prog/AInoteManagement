# BV-Text v6.10｜Explorer 跨組別剪貼

- 允許 Explorer 單筆「移動／剪下貼上」跨組別，保留原節點 ID、內容及子節點。
- 允許多選批次剪下貼上跨組別，維持禁止移入自身後代及禁止剪下根組別的防護。
- 跨組別複製沿用原有遞迴複製流程，建立新 ID。
- 移動 GROUP 至其他容器時轉換為 SUBFILE，避免 GROUP 巢狀結構違規。
- 不變更雲端權限或資料庫 schema。

驗證：Python 語法編譯、ZIP CRC 完整性；尚未於 Streamlit / Supabase 實測。
