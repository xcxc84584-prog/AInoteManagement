# BV-Text v3.3

## Explorer 操作
- Ctrl+C 複製、Ctrl+X 剪下、Ctrl+V 貼上。選中內容區塊時，貼上目標是其父資料夾。
- 右鍵 MOVE 先選擇來源，再選擇目的資料夾後貼上；拖曳到資料夾亦可移動。
- 同組別移動；跨組別可複製。禁止根組別移動與循環嵌套。
- 貼上後會選取複製／移動後的文件；操作失敗顯示錯誤。

## 導入本地文件做為子文件
- 在 GROUP 或 SUBFILE 右鍵選擇導入。
- 支援 UTF-8 `.md` / `.markdown` / `.txt`，每個文字檔建立一個 SUBFILE 與其 MARKDOWN 子節點。
- 支援 `.ainote` / `.zip`（需符合 v1 manifest/structure 格式），原 GROUP 轉為目標下的 SUBFILE，保留其子樹。
- 每次最多 20 份；若部分匯入失敗，已完成的子文件會保留，請手動檢查。
- `.ainote` 匯入不是交易式操作；圖片上傳失敗可能導致媒體缺失。請先備份再匯入。

## 示範文件
- 新建範例組別時，提示詞位於使用說明書最前段。
- 詳述 ZIP/ainote、manifest.json、structure.json、documents、assets、節點種類、UUID 與父子關係。
- 使用 `#` 章節、`##` 小節、`**` 重點，包含表格與圖片範例。

## 測試範圍
- Python 編譯與 Explorer JavaScript 語法檢查。
- 尚未連接真實 Supabase / Streamlit Cloud 進行端對端驗證。
