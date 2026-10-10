# AInoteManagement v1.0

Streamlit + Supabase 雲端筆記管理系統。支援註冊登入、組別與子文件混合模式、Markdown、圖文件、表格文件、圖片上傳/貼上、樹狀管理、匯入匯出、暗色/亮色主題（Streamlit 設定）。

## 1. Supabase 設定
1. 建立 Supabase 專案。
2. 開啟 SQL Editor，執行 `sql/schema.sql` 全部內容（建立資料表、RLS、私有圖片儲存 bucket 與政策）。
3. 在 Authentication > Providers 啟用 Email；依需求設定信箱確認及 Site URL。
4. 在 Project Settings / API Keys 取得 Project URL 與 publishable/anon key。**絕對不要放 service_role / secret key**。
5. 將 `.streamlit/secrets.toml.example` 複製為 `.streamlit/secrets.toml`，填入 URL 與 anon key。不要提交 secrets.toml 至 Git。

## 2. 本地啟動
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```
Linux/macOS 使用 `source .venv/bin/activate` 後執行 `pip install -r requirements.txt` 與 `streamlit run app.py`。

## 3. Streamlit Community Cloud 部署
1. 將本專案上傳至 GitHub（**勿上傳 secrets.toml**）。
2. Streamlit Community Cloud > Create app，選擇 Repository、Branch、`app.py`。
3. 在 Advanced settings / Secrets 貼上 `.streamlit/secrets.toml.example` 的兩個鍵及實際值。
4. Deploy，完成後註冊帳號並驗證信箱。
5. 圖片與 Markdown 永久資料儲存在 Supabase；Streamlit 容器內的資料不作為永久儲存。

## 4. 使用方式
- 左上功能選單：新增組別、匯入 `.ainote` / ZIP、下載組別備份。
- Explorer：點選文件切換頁面；子文件可啟用自身 Markdown 頁面，且不會顯示更深層子文件內容。
- 子文件直接子節點中的 MARKDOWN/GRAPH/TABLE 依 `position` 顯示為頁面區塊。
- GRAPH：選本地圖片，或點擊剪貼簿區域後 Ctrl+V，再按「儲存圖片並插入 Markdown」。
- 網頁無法自行寫入任意使用者本地路徑；請透過瀏覽器下載目錄管理匯出檔。
- Theme：右上 Streamlit 設定選單切換 Dark / Light。

## 5. 已知限制 / 後續改進
- 此版為可部署的初版，不包含 AI 模型 API、完整 VS Code 拖曳檔案樹、右鍵選單或即時協作。
- 圖片貼上需要瀏覽器允許剪貼簿事件；若不可用請改用本地上傳。
- 頁面內 Markdown 的 `asset://` 圖片引用以獨立 GRAPH 區塊為主要支援路徑。
- 匯入 `.ainote` 若中途失敗可能留下部分節點，建議先在測試帳號匯入。
- 刪除目前是**永久刪除**，尚未實作資源回收區；刪除前務必匯出備份。
- 刪除文件不會立即清除 Storage 中的孤立圖片；正式商用前應增加引用追蹤與清理排程。
- 多個使用者使用時需評估 Supabase 免費額度、備份策略與資安測試。
- Streamlit 互動造成 rerun，與原生 SPA 的編輯體驗不同。

## 6. 安全說明
- 使用 Supabase Auth + RLS，每位使用者只能讀寫自己的 notes/assets。
- 圖片使用私有 bucket 與時效性簽署 URL；使用 Pillow 驗證與轉檔。
- 不要將 Supabase service_role key 放在 Streamlit Cloud Secrets 作為此應用的資料存取金鑰。
- 此版未完成正式滲透測試，不應宣稱已達生產環境完整安全保證。
