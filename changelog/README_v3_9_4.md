# BV-Text v3.9.4 — 本地保存與節點優先權

## 更新
- 新增「保存本地後繼續編輯」：匯出目前組別備份，不移至回收區。
- 新增「快速授權／手機儲存說明」：支援的瀏覽器可授權資料夾；不支援的手機使用瀏覽器下載備份。手機無法強制取得資料夾存取權限。
- Explorer 右鍵「節點優先權」：輸入正整數，在同層資料夾內重新編號 1,2,3...。
- MOVE/拖曳 FILE1 到 FILE2：FILE1 插入 FILE2 後方，後續節點順延。MOVE 到資料夾則移入尾端。
- 既有節點依 position，建立時間、ID 穩定排序。優先權沿用 notes.position，不需 SQL migration。
- 一般下載備份不代表已驗證完成寫入，因此「保存後關閉」仍要求可確認的寫入結果。

## 驗收
1. 保存本地後繼續編輯，確認文件仍開啟。
2. 手機測試下載備份；下載後到系統下載資料夾確認檔案。
3. A,B,C,D → D 移到 B 上 → A,B,D,C。
4. 設 A 優先權 3 → B,D,A,C；重新整理後順序維持。

## 部署
```powershell
git add .
git commit -m "BV-Text v3.9.4 local save and priority"
git push origin main
```

Python 與 JavaScript 語法已檢查；未進行實際手機及 Streamlit Cloud 端對端測試。
