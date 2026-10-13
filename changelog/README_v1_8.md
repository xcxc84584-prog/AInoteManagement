# AInoteManagement v1.8 — 工作區、表格與快速定位

- GROUP/SUBFILE 只作為資料夾；編輯模式不再提供資料夾 Markdown 正文輸入框。舊資料夾正文不會自動刪除，仍可在瀏覽模式查看。
- 同一層文件的文字、圖片、表格直接排列於編輯工作區；文字與表格可透過「儲存全部變更」儲存並讀回驗證，圖片維持各自的「儲存圖片」。
- 瀏覽模式表格改為固定欄寬、等寬儲存格，窄螢幕時可水平捲動。
- 建立 TABLE 時可輸入 M 列（1–50）、N 欄（1–30）、格子大小（小／中／大）。
- Explorer 左側右鍵選單新增「快速定位」。瀏覽模式使用左側連結跳至章節錨點；編輯模式可選取文件並切換工作區。取消頁面中重複的快速定位目錄。
- 表格大小透過 Markdown HTML 註解記錄，不必新增 Supabase 資料表欄位；既有表格預設「中」。

## 更新
1. 備份資料並保留 Git 專案 `.git`、Streamlit Secrets。
2. 解壓縮覆蓋原專案。
3. `git add . && git commit -m "Update AInoteManagement v1.8" && git push origin main`
4. Streamlit Cloud 重新部署後，測試右鍵建立表格、表格儲存、手機橫向捲動、快速定位。

## 限制
- 本版通過 Python 語法編譯及 ZIP 完整性檢查，但尚未在真實 Supabase/Streamlit Cloud 端到端測試。
- 瀏覽模式的頁內錨點定位依賴 Streamlit/瀏覽器處理同頁 fragment，請於部署後確認。
- 快速定位切換文件前請先儲存未提交的編輯內容。
