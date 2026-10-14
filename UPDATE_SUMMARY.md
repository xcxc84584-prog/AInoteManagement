# BV-Text 歷次更新總結

本文件由舊版更新紀錄彙整，依原始檔名保留版本來源與主要修正內容；不代表每項功能都已完成端到端測試。

## v6.25.2｜Explorer-Local 互動與刪除
- Explorer-Local 文件樹支援點擊選取，自動定位下方「下載 Explorer-Local 文件」選單及預覽。
- 增加確認後刪除選取文件與子文件；僅作用於獨立本地庫，不會修改工作區。
- 移除分散的歷史更新 log，整合為此總結。

## v6.25.1｜修正 db_root
- 修正儲存模式切換時 db_root 未定義導致 NameError。

## v6.25｜獨立 Explorer-Local
- 新增獨立本地庫，與工作區僅透過上傳及下載交換文件；提供預覽、ZIP 備份與行程表交換。

## 歷史更新紀錄彙整

### FIX_v6.10.md

# BV-Text v6.10｜Explorer 跨組別剪貼

- 允許 Explorer 單筆「移動／剪下貼上」跨組別，保留原節點 ID、內容及子節點。
- 允許多選批次剪下貼上跨組別，維持禁止移入自身後代及禁止剪下根組別的防護。
- 跨組別複製沿用原有遞迴複製流程，建立新 ID。
- 移動 GROUP 至其他容器時轉換為 SUBFILE，避免 GROUP 巢狀結構違規。
- 不變更雲端權限或資料庫 schema。

驗證：Python 語法編譯、ZIP CRC 完整性；尚未於 Streamlit / Supabase 實測。

### FIX_v6.11.md

# BV-Text v6.11

- 雲端服務主頁提供 Explorer 樹狀檢視，只下載文件節點 metadata，不預先下載正文。
- 對節點按右鍵選擇「載入」或「刪除」。選擇後於主頁確認；刪除包含子節點、關聯資產及儲存圖片。
- 局部載入沿用既有的父節點與圖片匯入流程，完成後重載工作區。
- 手動雲端上傳加入 `daily_tasks`、`daily_task_checks`，先寫任務，再寫每日勾選。
- 下載原本已包含這兩個資料表。

## 注意
- Supabase 需先設定 `daily_tasks` 與 `daily_task_checks` 的 authenticated CRUD 授權和使用者專屬 RLS。
- Explorer 右鍵動作透過 iframe 跳轉頁面 query string，需於部署後確認瀏覽器 iframe 導航權限；如受限，操作可能無法送達主頁。
- 刪除是不可復原操作，請先備份；跨資料表及 Storage 刪除不是單一交易，失敗可能造成部分刪除。
- 尚未完成實際 Supabase / Streamlit Cloud / 行動裝置整合測試。

### FIX_v6.12.md

# BV-Text v6.12｜雲端 Explorer 樹狀檢視優化

- 雲端 Explorer 與側邊 Explorer 對齊節點圖示：FOLD/GROUP 資料夾、FILE/MARKDOWN 文件、GRAPH 圖片、HANDWRITE 手寫稿、COMPOSITE 圖文、TABLE 表格。
- 加入父子結構連接線，初始只顯示 ROOT 層，點擊三角形展開下一層；支援收合。
- 保留右鍵選單「載入／刪除」，並提供觸控長按。
- 雲端清單載入增加進度提示；單節點載入及刪除使用既有 manual_sync 進度回報函式，修復其在操作前尚未定義的問題。
- 注意：iframe 透過父頁網址參數傳遞操作，仍需在實際 Streamlit Cloud 環境測試瀏覽器安全限制；刪除前仍需確認。

### FIX_v6.14.md

# BV-Text v6.14 修正
- Cloud Explorer 局部載入後切換至筆記工作區、選取目標節點並更新側邊 Explorer；不再透過重新從 IndexedDB 讀取舊快照來覆蓋新載入文件。
- 側邊 Explorer 右鍵新增「雲端化」：僅上傳所選文件、必要祖先節點及其直接關聯圖片，不上傳其他文件。
- 筆記 content 以 BVZ1:zlib: 標記 + base64 zlib 格式存入雲端，僅在有節省儲存字元時啟用。雲端完整下載及局部載入時自動解壓；舊資料維持相容。
- 雲端操作進度條沿用既有同步進度 UI。
## 注意
- 圖片檔案不另外壓縮（常見圖片格式已壓縮）。
- 尚未在真實 Supabase、IndexedDB、Streamlit Cloud 環境測試；建議先備份。
- 本版本的雲端化僅上傳所選節點本身及其父節點，不會自動包含所選資料夾的全部後代。

### FIX_v6.15.md

# v6.15 更新

- Explorer 頂部「操作」對應選單加入「雲端化」，單獨上傳所選節點與必要父節點。
- 雲端局部載入預設僅下載選取文件，缺少的父節點在本地解除父子連結；不會下載整個 ROOT。
- Cloud Explorer 的 SUBFILE/FOLD 均使用資料夾圖示。
- 圖片文件及手寫稿的 asset 關聯同時依 note_id 與 asset:// 引用尋找，下載實際 Storage 圖片位元組。
- 保留原有壓縮筆記文字的解碼。

注意：本地匯入時若父節點不存在，單一文件成為獨立根節點。雲端化圖片時若本地圖片資料缺失，將明確報錯。尚未進行線上 Supabase 整合測試。

### FIX_v6.16.md

# v6.16
- 修正雲端載入時對已建立的 main_page radio widget 直接寫入 session_state 的例外，改為下次 rerun 前設定。
- 選取 FILE/GRAPH/HANDWRITE/COMPOSITE 僅下載本身與引用圖片；選取 GROUP/SUBFILE/FOLD 則下載全部子孫節點。
- 側邊 Explorer「功能」視窗新增對選取文件的雲端化按鈕；原右鍵「雲端化」保留。
- Cloud Explorer 子資料夾沿用資料夾圖示。
- 仍需真實 Supabase、IndexedDB 與手機端整合測試。

### FIX_v6.17.md

# BV-Text v6.17 修正

- 修復 Cloud Explorer 載入時 `cannot import name cloud_selection_ids from manual_sync`。
- 節點選取範圍改由 `app.py` 本地函式計算，不再依賴 `manual_sync.cloud_selection_ids` 匯出。
- FILE/GRAPH/HANDWRITE/COMPOSITE 僅載入所選文件；GROUP/FOLD/SUBFILE 載入其所有後代。
- `manual_sync.py` 仍保留原有函式，避免其他呼叫路徑失效。
- 部署時必須整份更新 app.py 和 manual_sync.py 並重啟應用，避免混用版本。

### FIX_v6.18.md

# v6.18 Cloud Explorer 點選同步

- Cloud Explorer 單擊文件節點時，透過 Streamlit component value 回傳 ID。
- 在 selectbox 建立之前更新 `cloud_tree_selected`，下方「選擇雲端 Explorer 節點」自動對應。
- 展開三角形不會改變目前選取節點。
- 保留原有載入／刪除、資料夾展開及進度條。
- 尚未於真實 Streamlit Cloud 瀏覽器驗證。

### FIX_v6.19.md

# v6.19 Cloud Explorer 元件載入修正
- 移除元件內嵌第二層 iframe 與跨層 postMessage，改為 Streamlit Component v1 的單層通訊。
- 使用 DOMParser 解析樹狀預覽、直接綁定節點點擊與展開事件。
- 保留點擊 Cloud Explorer 節點同步下方選擇框的功能。
- 如部署仍顯示舊版，請重啟 Streamlit Cloud 並清除瀏覽器快取。

### FIX_v6.20.md

# BV-Text v6.20 — Cloud 下載後 Explorer 不顯示

- 局部下載後檢查選取節點是否確實寫入本地資料庫；未寫入時顯示錯誤，而非虛報成功。
- 保留已載入的本地工作區；IndexedDB 確認保存後不再立即清空載入狀態並重新匯入，避免舊快照覆蓋新資料。
- 雲端下載後切回筆記工作區、選取下載節點，並嘗試展開側邊 Explorer。
- 若瀏覽器封鎖側邊欄 DOM 操作，可手動點擊 Streamlit 原生側邊欄展開按鈕。

驗證：Python 編譯、ZIP 完整性；未進行實際 Streamlit Cloud / Supabase 整合測試。

### FIX_v6.21.md

# v6.21 修正

修正 sync_progress 僅定義在雲端服務頁面中而導致 Side Explorer NameError；提升為模組共用函式。

已檢查 Python 語法與 ZIP 完整性；尚未完成 Supabase 整合測試。

### FIX_v6.4.2.md

# BV-Text v6.4.2 — assets_note_id_fkey 修復

- 雲端同步先建立全部筆記，再逐筆確認 notes.id 確實存在。
- 若本地資產指向已不存在的筆記，保留資產但將雲端 `note_id` 設為 NULL（資料庫欄位原本允許 NULL）；上傳結果會顯示 `orphan_assets_detached` 數量。
- 不移除外鍵或 RLS，也不刪除本地筆記、圖片或雲端既有資料。
- 直接圖片上傳前檢查筆記是否存在，避免上傳孤立 Storage 物件。
- 注意：若孤立資產所屬筆記原本應存在，應先從本地備份復原筆記再同步；NULL 僅保留資產，無法恢復原筆記關聯。

### FIX_v6.4.3.md

# v6.4.3 修復說明

1. 快捷建立行程：開啟請求只消耗一次；Esc、X、點擊外側或取消不會在後續重跑重新彈出。
2. Explorer 功能：改為一次性開啟請求，關閉後不會被舊 session 狀態重新開啟。
3. daily_tasks / daily_task_checks：新增資料庫授權與 RLS SQL。

## 部署必做
請先在 Supabase SQL Editor 執行 `migrations/20261013_daily_tasks_permissions_v6_4_3.sql`，再重新部署。單純更新 ZIP 不會修改雲端資料庫權限。

## 驗證
測試視窗 Esc / 外側關閉後操作其他功能；重新上傳與下載雲端資料；確認不同帳號不能讀取彼此每日任務。

### FIX_v6.4.4.md

# v6.4.4 雲端同步功能
- 手動上傳與下載：顯示階段進度（非網路位元組進度）。
- 即時更新：先明確確認下載雲端資料，之後在 Streamlit rerun 時同步本地變更；非跨裝置即時訂閱。
- 重製雲端：只刪除目前登入使用者資料，先刪關聯紀錄，再刪 Storage 圖片；失敗可能部分完成。
- 去重：只自動刪除 schedule_cards、daily_task_checks 中內容完全相同的舊紀錄；有外鍵風險的 notes、daily_tasks、assets 不刪除。
- 403 Storage RLS：請檢查 storage.objects 的 note-images bucket INSERT/UPDATE/SELECT 權限；不建議停用 RLS。
- 注意：即時同步為後續頁面 rerun 才執行；網路失敗時本地資料保留。

### FIX_v6.8.md

# v6.8 變更紀錄
- 匯入器支援不包含 GROUP 根節點的單一 COMPOSITE 圖文文件；仍保留舊 GROUP 封包支援。
- 支援 structure.json 沒有 content 時從 documents/<id>.md 讀取。
- 瀏覽／編輯工作區以優先序為基礎，只渲染焦點節點與 ±1 節點，切換時顯示階段進度條。
- 擴充 AI 提示詞，列出 manifest.json、structure.json、documents、assets 的具體結構。
- 目前仍先載入節點中繼資料與部分資產索引；並非完整資料庫層級 lazy loading。
- 尚未在實際 Streamlit Cloud / 多裝置執行端到端測試。

### FIX_v6.9.md

# BV-Text v6.9 更新說明

1. 雲端服務移至主畫面獨立頁面，側欄僅保留頁面導覽。
2. 新增雲端文件清單與多選局部載入，保留本地其他資料；自動補父節點、資產與圖片，完成後重新載入。
3. 新增同父節點、同類型、同名筆記的 Markdown 標題段落合併：不同標題聯集，重複標題取 updated_at 較新文件。合併後重新指派子文件與資產的外鍵再刪除舊文件。無法安全合併的類型或重複標題將跳過。

注意：雲端同名合併會修改並刪除資料，必須先備份。若同一段內的不同文字未以 Markdown 標題分隔，無法識別為獨立區域；會採用較新段落覆蓋。資料庫更新不是跨多次 API 呼叫的單一交易，中途失敗可能需人工復原。尚未經過真實 Supabase 與 IndexedDB 整合測試。

### changelog/README_#U03a3#U2510#U00ab#U03c3#U255b#U2310#U03a6#U00ac#U00ac#U00b5#U00ff#U00c4.md

# AInoteManagement v1.0 修正版

## 修正
- `PGRST204`: `notes.deleted_at` 尚未建立時，刪除與還原會回退到 `is_deleted` 欄位；正式解法仍是執行 SQL migration。
- 調整 Streamlit 主工作區及側邊欄的寬度限制，避免水平溢出。
- 將上方多個檔案分頁按鈕改為響應式文件選擇器，避免按鈕超出畫面。
- 保留 Markdown 編輯器、Supabase Storage、登入、Explorer、資源回收區與匯入匯出。

## 部署前必要步驟
1. Supabase Dashboard → SQL Editor → 執行 `sql/migration_fix_deleted_at.sql`。
2. 確認 SQL 最後顯示 `is_deleted` 和 `deleted_at` 兩個欄位。
3. 解壓縮 ZIP 到原 Git 專案（保留 `.git` 與 Streamlit Cloud Secrets）。
4. `git add . && git commit -m "Fix layout and deleted_at" && git push origin main`
5. 在 Streamlit Cloud 重新整理網站並測試刪除／還原。

注意：未在實際 Supabase 帳號及瀏覽器完成端對端測試。

### changelog/README_V612.md

# BV-Text v6.1.2 development preview

- Mouse-click confirmation for TOC; removed Ctrl+T in editor and reader.
- Added multi-line $$...$$ display LaTeX rendering through KaTeX.
- Explorer reads TOC entries from the same IndexedDB table; BroadcastChannel refreshes branches.
- Explorer navigation passes TOC UUID to editor and reader; both resolve via BV61TOC.locate.
- Ctrl+D deletes a selected TOC entry in Explorer, not a file.

Limitations: browser-local TOC cannot sync across devices or unrelated browser origins; rich text source conversion and line-to-rendered-block mapping may not be exact for complex tables/code blocks; browser end-to-end testing not performed.

### changelog/README_V613_MATH_FIX.md

# BV-Text v6.1.3 — LaTeX 修正

- 編輯與瀏覽共用數學片段辨識邏輯，支援 `$$...$$`、`\(...\)`、`\[...\]`。
- 修復一般文字後緊接 `$$...$$` 及跨行公式的渲染。
- 使用 KaTeX `throwOnError: true` 讓無效 LaTeX 回到原始碼並產生診斷記錄。
- 保留舊版目錄系統與 IndexedDB 資料結構，未進行資料庫遷移。
- 仍需在真實 PC/手機瀏覽器驗收，且無法從缺失反斜線的原始資料自動恢復正確公式。

### changelog/README_V614_MATH_FIX.md

# BV-Text v6.1.4 — Nested LaTeX delimiter fix

修正 ChatGPT 貼上 `\[$$...$$\]` 和 `$$\[...\]$$` 的顯示問題。

- 修改 `components/composite_editor/index.html` 與 `components/composite_reader/index.html`：在 Markdown 渲染階段統一巢狀數學式定界符，避免內層 `$$` 被先行解析；保留原始 Markdown。
- 修改 `app.py` 的 `show_markdown()`，使 Streamlit 顯示路徑同樣支援。
- 避開三反引號及三波浪號程式碼區塊中的正規化。
- 新增 `tests/test_nested_math_v614.py`。

測試：Python 語法、編輯/閱讀 JavaScript 語法及 pytest（6 tests）通過。尚未在真實 PC/手機瀏覽器執行端到端測試。

測試輸入：

```text
\[$$CPI=1+0.2\times0.4\times3$$\]
\[$$CPI=\frac{\text{Total Clock Cycles}}{\text{Instruction Count}}$$\]
```

請先備份既有資料，再於測試環境解壓並部署。

### changelog/README_V615_SVG_MOBILE_FIX.md

# BV-Text v6.1.5 SVG / math coexistence fix

- Protect Markdown image tokens before LaTeX parsing, in both reader and editor.
- Locate closing SVG XML before looking for the Markdown image closing parenthesis; support escaped `data\:image/svg+xml`.
- Preserve raw SVG data URI whitespace rather than stripping meaningful SVG text spaces.
- Add secondary KaTeX CDN for devices that cannot reach jsDelivr.
- Preserve the original document source. No destructive normalization of saved Markdown.

## Manual verification still required
Test on real desktop and mobile browsers with raw and percent-encoded SVG data URLs, SVG containing parentheses and dollar signs, and `\[$$...$$\]` math in the same document. Browser connectivity and CSP can still prevent CDN loading.

### changelog/README_V616_MATH.md

# BV-Text v6.1.6 — Test 09 / Test 10 修正

- 編輯器與閱讀器的渲染前正規化統一：將 `\[$$...$$\]` 與 `$$\[...\]$$` 轉為單層 `\[...\]`，不改寫儲存的 Markdown。
- 新增完整單行 `$$...$$` 與 `\[...\]` 的優先辨識，保留原有跨行辨識。
- 正規化略過 fenced code，並在正規化時暫時保護 Markdown 圖片 URI，避免重新引入 SVG / 數學式互相干擾。
- 驗證：Python 6 項測試、JS 正規化 8 項檢查、兩個前端 JS 語法檢查通過。
- 限制：尚未進行實體 PC／手機瀏覽器驗收；請在測試環境檢查 Test 09、10 與 SVG 同頁顯示。

### changelog/README_V617.md

v6.1.7：保護 Markdown 標題不被未閉合數學式吞掉；支援遺失定界符的 P(...) = \frac... 公式恢復。實機仍需測試。

### changelog/README_V618_SVG_FIX.md

# BV-Text v6.1.8 — SVG Data URI 修正

修正 `hrcImageTokens()` 在已辨識 SVG Data URI 結尾後，仍錯誤進入一般 Markdown 括號掃描的控制流程。原本 `else` 綁定到 `if(isData && end<0)`，導致 SVG 結尾定位被後續掃描覆寫，特別是 `%3C/svg%3E` 的 URI。改為僅在 `!isData && end<0` 時執行一般圖片括號解析。同步修正 editor 與 reader。

已完成 JavaScript 語法檢查與 SVG token 測試；未在實際手機瀏覽器驗收。

### changelog/README_V61_STATUS.md

# BV-Text v6.1 開發預覽（非正式版）

以 v6.0 alpha 1 為基礎。新增獨立 IndexedDB 目錄資料表（document_id、行號、欄號、選取文字、上下文），移除編輯器的 `//[名稱]//` 目錄標記插入及完全單一編輯的「目錄基準快速定位」。瀏覽器與編輯器透過同一 `BV61TOC` 資料存取層管理目錄。Ctrl+T 在有選取文字時建立本地目錄。編輯元件顯示本地目錄清單與刪除按鈕。公式解析限定 `\\(...\\)` 和 `\\[...\\]`。

## 已知未完成項目

- Explorer 文件管理樹尚未接上 IndexedDB 目錄分支及 Ctrl+D 刪除。
- 閱讀模式尚未提供完整的目錄清單導航介面；編輯器目前定位到 Markdown 原始碼行。
- 富文字模式對重複選取文字會拒絕建立目錄，須在原始碼模式精確選取。
- 原有編輯器富文字往返轉換流程尚未全面替換，仍有資料完整性風險。
- IndexedDB 目錄只在同一瀏覽器／同一來源保存，不會跨裝置同步，也未建立匯出備份。
- 尚未執行真實 PC／手機瀏覽器端端測試；只做了 JS 語法檢查與 Python 單元測試。
- 舊文件中的 `//[名稱]//` 不會自動轉換為新目錄資料；它們現在只是一般文字。

**請勿以此版本覆蓋正式資料；先備份既有專案與 Supabase 資料。**

### changelog/README_V620.md

# BV-Text v6.2.0 手動文本修正（第一階段）

- 在圖文文件編輯／瀏覽中框選文字，右鍵標註唯一的起始／末尾修正點；框選起點取第一字，終點取最後一字。
- 兩點選定後彈出中央修正視窗，提供數學式修正、SVG 修正、替代文本。
- SVG 修正支援 HTML `<img loading="lazy" src="data:image/svg+xml,...">`、Markdown `data\:image`、Base64 與原生 SVG；修復預覽使用 eager，安全清理腳本與危險屬性。
- 替代文本採方案 A，建立 X-1／X-2／X-3，原文以 base64 JSON 記錄在 X-1 來源註解。
- 本地目錄在編輯時檢查原始選取文字是否已完全消失；消失即刪除錨點。

## 已知限制
- 圖文渲染模式的選取區間必須能在原始 Markdown 中唯一對應；重複文字請切換原始碼模式。
- 目前 SVG 修正後產生的是經安全清理的 HTML img Data URI，尚未加入獨立 IndexedDB Blob 資產庫。
- 三段式分割涉及多次資料庫操作，已盡力回滾新建節點，但不是資料庫原子交易。
- 需在實際 Streamlit PC／手機環境驗證，尤其是 SVG 的 CSP 與 lazy 行為。

### changelog/README_V621.md

# BV-Text v6.2.1

- 瀏覽模式右鍵原有選單直接新增「標註起始修正點」「標註末尾修正點」，避免 v6.2.0 的獨立選單與原選單競爭。
- 右鍵開啟時先保存選取區間，點擊選單不會遺失框選。
- HTML `<img loading="lazy" src="data:image/svg+xml,...">` 以受限制的 HTML 圖片節點顯示，支援 data\: 跳脫。
- Markdown SVG Data URI 改用 eager 載入，避免嵌入式捲動容器延遲載入。
- 僅通過靜態語法驗證，請在 PC/手機測試實際載入。

### changelog/README_V622.md

# v6.2.2 修正點視覺化

- 綠色箭頭顯示起點，紅色箭頭顯示終點。
- 選定雙點時增加黃色底線並自動開啟修正視窗。
- 修正或取消後清除標記。
- 注意：目前標記為畫面定位，長距離捲動後可能需要重新標註。

### changelog/README_V623.md

# BV-Text v6.2.3
- 移除起始／末尾修正點與箭頭、黃色定位線。
- 框選一段文字後，右鍵「修正框選文字」即可開啟中央修正模式。
- 保留數學式、SVG（含 lazy）修復與方案 A 替代文本分割。
- 重複文字或渲染內容無法唯一對應原始 Markdown 時，拒絕猜測位置，建議切換原始碼模式。
- 靜態 JS 語法檢查通過；尚未完成實際瀏覽器測試。

### changelog/README_V624.md

# BV-Text v6.2.4
- 恢復起始／末尾修正點（瀏覽與編輯模式）。
- 新增區塊刪除（確認後才執行）。
- 遠端 images.openai.com 圖片失敗時顯示診斷訊息，不保證代理網址永久有效。
- 畫面標記目前是定位提示，非精確逐字高亮；需後續瀏覽器測試。

### changelog/README_V625.md

# BV-Text v6.2.5｜圖片／SVG 本地保存
- 閱讀器、編輯器自動偵測 img，對可存取的圖片及 SVG 下載並儲存於瀏覽器 IndexedDB。
- 重新整理網頁時優先使用本地快取（同瀏覽器、同站點環境）；以 Blob URL 顯示。
- 提供「圖片本地資料夾」按鈕：在支援 File System Access API 的安全瀏覽器中，經使用者授權可將已快取及後續下載的圖片寫入本機資料夾。
- 不支援的瀏覽器／iframe 僅能使用 IndexedDB，無法無提示地寫入本機檔案。
- 遠端 URL 必須允許 CORS，且圖片當下仍可存取；否則無法由瀏覽器取得位元資料。已失效的來源無法自動復原。
- IndexedDB 不跨裝置、不等於雲端永久保存；清除網站資料後可能遺失。實際跨裝置持久化需要後端檔案儲存。
- SVG 儲存前移除 script、foreignObject、事件屬性及外部引用。
- 既有修正點與區塊刪除沿用 v6.2.4。
- JavaScript 語法檢查通過，尚未完成真實瀏覽器／跨裝置測試。

### changelog/README_V626.md

# BV-Text v6.2.6 圖片資產修復
- 修正 HTML <img src="asset://UUID"> 被當成文字顯示的問題。
- 保留 Markdown 內 asset://UUID，渲染時使用現有 Supabase asset_image -> data URI 對應。
- 新增以 UUID 為鍵的 IndexedDB Blob 快取，重開同站同瀏覽器優先讀取快取。
- 支援一般 HTTPS 圖片與 SVG data URI；下載失敗（CORS/過期）不保證保存。
- 保留本地資料夾按鈕；需瀏覽器授權，資料夾保存不是離線恢復來源。
- 尚未執行實際瀏覽器端到端測試。

### changelog/README_V628.md

# v6.2.8｜圖片資料夾授權整合

- 移除編輯器、瀏覽器畫面右下角「授權圖片資料夾」固定按鈕。
- 編輯器工具列「儲存圖文文件」在使用者直接點擊時嘗試授權圖片資料夾，然後同步既有圖片及 SVG。
- 外層「提交」透過訊息觸發編輯器儲存；只能重用已授權的資料夾，無法保證跨 iframe 保留使用者手勢而彈出選擇器。
- 授權失敗、取消或不支援時不阻止文件儲存，IndexedDB 圖片快取繼續運作。
- 快取命中時，如有可用資料夾也會同步檔案。
- 已通過 JS 語法檢查；尚未完成瀏覽器實測。

### changelog/README_V629.md

# v6.2.9 Reader clipping fix

- 移除閱讀器 iframe 高度 16000px 的硬上限。
- 依 document、body、editor 實際高度計算 iframe 高度。
- 使用 ResizeObserver 監測內容尺寸，處理表格、數學式、圖片、字型等延遲渲染。
- 加入 image load/error、window resize、font ready 高度更新。
- 高度訊息採 requestAnimationFrame 合併，避免過度重算。
- Python 與兩個元件 JavaScript 語法檢查通過；尚未進行真實 Streamlit 瀏覽器測試。

### changelog/README_V630.md

# BV-Text v6.3.0
- 新增與儲存路徑分離的自動 Load 資料夾設定；已授權時網頁重載檢查 .ainote/.zip/.md/.txt/.bvcalendar.json。
- 瀏覽器安全限制：首次及權限過期後仍須使用者點擊授權；無法在手機上保證資料夾存取。
- 根目錄允許建立無組別 MARKDOWN 純文件。
- 圖文文件可一次插入最多 30 張圖片/SVG，每張 10 MB。
- 閱讀器移除大量底部空白 padding，改依 editor 實際高度計算 iframe 高度。
- 自動匯入採非覆寫方式；請確認匯入結果避免重複資料。

### changelog/README_V631.md

# v6.3.1
- 可開關的自動 Load（瀏覽器 IndexedDB 設定）
- 行程卡標題與勾選，懸浮詳情、右鍵編輯／刪除
- 移除瀏覽器文件分割／還原分割，保留目錄化
- 既有舊分割文件保留原內容與元資料，不進行破壞性轉換。
- 注意：需要資料夾權限才能自動載入；未完成實機瀏覽器驗證。

### changelog/README_V632.md

# BV-Text v6.3.2
- Explorer 移除 Ctrl+D 功能與複製副本快捷選項。
- 文件操作新增批量選取；選取時右側優先權數字替換為勾選框。
- 頁面功能區新增取消選取、選取完成；完成後可刪除、剪下或複製，右鍵目標資料夾批量貼上。
- 批量刪除移入回收區；複製保留來源，剪下移動來源。
- 每日任務改用與行程卡相同的標題＋勾選 UI，懸浮顯示詳細資料，右鍵編輯與刪除。
- 驗證：Python 編譯及 Explorer JavaScript 語法；未完成瀏覽器端到端測試。

### changelog/README_V6_STATUS.md

# BV-Text v6 reconstruction status

This archive preserves the complete v5.1.1 project unchanged and adds a tested lossless Markdown document core in `v6_core/`.

## Verified
- Extract `//[name]//` TOC entries from source without changing Markdown.
- Preserve duplicate TOC names as separate entries.
- Preserve LaTeX source and calculate content SHA-256.
- Split documents at line boundaries without rewriting source.
- Revision counter only advances for actual changes.

Run: `python -m unittest discover -s tests -p test_v6_document.py`

## Not yet implemented / not verified
- Full editor integration with Streamlit, CodeMirror, KaTeX/MathJax fallback, safe SVG sanitization, GFM parsing, IndexedDB, Supabase revision syncing, migration and browser E2E testing.
- The legacy v5.1.1 components remain in use; do not deploy this as a completed v6 replacement.

The file is an incremental development baseline, NOT a finished v6 release.

### changelog/README_v1_2.md

# AInoteManagement v1.2

更新：Explorer 固定高度與內部捲動；在文件樹中直接輸入新增/重新命名；中央僅保留 Markdown 編輯器；刪除及還原逐筆檢查資料庫結果，錯誤詳情寫入 Streamlit Logs。

## 部署

將 ZIP 內所有檔案覆蓋原 GitHub 專案（保留 .git），執行 `git add . && git commit -m "Fix Explorer UI and delete" && git push origin main`。

請先確認已執行 `sql/migration_v1_1.sql`。若刪除仍失敗，從 Streamlit Cloud Logs 擷取 `Explorer action failed` 後的 traceback，勿公開金鑰。

注意：此版本未經線上 Supabase 實測。刪除仍為軟刪除，需 UPDATE 權限及對應 RLS policy。

### changelog/README_v1_4.md

# AInoteManagement v1.4｜圖片、表格、共用工作區、帳號註銷

## 功能
- GROUP/SUBFILE 各有自己的工作區，同一層的 MARKDOWN/GRAPH/TABLE 在同一網頁呈現。
- 「瀏覽」模式將 Markdown、表格及私人圖片呈現為筆記。
- 「編輯」模式提供 Markdown 內容、區塊編輯、圖片貼上/拖曳/本地上傳，以及 M×N Markdown 表格（M=1–50，N=1–30）。
- 圖片儲存在私人 `note-images` Bucket，以登入者 UID 為第一層路徑。
- 帳號設定新增「永久註銷帳號」：需要重新輸入密碼、輸入確認文字、勾選確認。由 Supabase Edge Function 驗證身份、刪除私人圖片，最後刪除 Auth 使用者；資料表以 ON DELETE CASCADE 清理。

## 必做部署
1. 先備份筆記與 Supabase 資料庫。
2. 如尚未執行，至 Supabase SQL Editor 執行 `sql/migration_fix_deleted_at.sql`。
3. 在 Supabase 專案部署 `supabase/functions/delete-account/index.ts`，函數名稱必須為 `delete-account`。
   - 建議用 Supabase CLI：`supabase login`、`supabase link --project-ref <你的專案 ref>`、`supabase functions deploy delete-account`。
   - 函數使用平台內建 `SUPABASE_URL`、`SUPABASE_ANON_KEY`、`SUPABASE_SERVICE_ROLE_KEY` 環境變數。
   - **不要**把 `SUPABASE_SERVICE_ROLE_KEY` 放在 Streamlit Secrets、GitHub 或前端。
   - Edge Function 的 JWT 驗證應保持啟用；程式也會透過 `auth.getUser(token)` 再驗證。
4. 用 ZIP 內檔案覆蓋 GitHub 專案，保留 `.git`。`git add . && git commit -m "AInoteManagement v1.4" && git push origin main`。
5. 測試上傳圖片、貼上截圖、插入表格、瀏覽/編輯切換；**最後**使用測試帳號驗證永久註銷。

## 注意
- 永久註銷不可復原，請先下載 .ainote。註銷功能只有 Edge Function 部署後才可用。
- Auth 刪除前會嘗試移除使用者 UID 目錄下的圖片；若刪除過程失敗，可能需要管理員人工清理殘留資料。
- 帳號刪除依賴 `public.notes` 和 `public.assets` 對 `auth.users` 的 ON DELETE CASCADE 外鍵；若資料庫已自行改過，請先確認。
- 目前沒有在實際 Supabase 與 Streamlit Cloud 上完成端到端測試。

### changelog/README_v1_4_1.md

# AInoteManagement v1.4.1 — 修正安裝與記住此裝置

## 已修正
- `requirements.txt` 原本誤含字面 `\n`，使 pip 無法解析 `requests` 依賴；已修正為正確的換行格式。
- 登入頁新增「記住此裝置（自動登入）」。勾選後，使用瀏覽器同來源 localStorage 儲存 Supabase refresh token，重新開啟同瀏覽器可恢復登入；不儲存密碼。
- 登出及帳號永久註銷後，要求清除瀏覽器儲存的登入資訊。
- 保留 v1.4 的圖片、表格、共用工作區、瀏覽/編輯模式及 Edge Function 帳號刪除功能。

## 安全提醒
- localStorage 不是 HttpOnly Cookie，惡意瀏覽器擴充功能或網站 XSS 可能讀取 token。只在信任的私人裝置勾選；公用裝置不要啟用。
- 若要更高安全性，未來應改用受保護的後端 Session 與 HttpOnly/Secure/SameSite Cookie。
- Supabase 的 refresh token 會輪替；本版在刷新後同步更新本機記憶，但網路中斷或多分頁同時刷新仍可能需要重新登入。
- 本版未在你的 Streamlit Cloud 完成實際安裝或端到端測試。

## 部署
1. 將 ZIP 全部檔案覆蓋原專案（保留 `.git` 及雲端 Secrets）。
2. `git add .`、`git commit -m "Fix pip requirements and remember device"`、`git push origin main`。
3. 若 Streamlit Cloud 仍失敗，提供 Manage app → Logs 中 pip 安裝失敗的完整前後 30 行。
4. 帳號永久註銷仍需另外部署 `supabase/functions/delete-account` Edge Function。

### changelog/README_v1_5.md

# AInoteManagement v1.5｜工作區編輯修正

## 本版變更
1. 恢復工作區正文「💾 儲存工作區正文」按鈕，保留各文字區塊的獨立儲存按鈕。
2. 瀏覽模式以 GROUP 組別為單位，遞迴呈現子文件與其文字、圖片、表格。
3. 編輯模式保留同一父層的共用工作區；GRAPH 區塊不顯示 Markdown 輸入框，改為圖片預覽、從本地上傳／拖曳、剪貼簿圖片貼上、儲存圖片。
4. TABLE 區塊不顯示 Markdown 輸入框，改用 Streamlit `st.data_editor` 類試算表介面，提供儲存表格按鈕。資料庫繼續儲存 Markdown 表格，維持原始資料相容性。
5. 建立表格時輸入 M×N（M=1–50 資料列，N=1–30 欄），建立後即可在表格編輯器填寫。
6. 沿用上一版「記住此裝置」及帳號註銷功能。

## 部署
備份 `.ainote` 與資料庫後，將 ZIP 內容覆蓋 GitHub 專案，保留 `.git` 與 Streamlit Secrets。
`git add . && git commit -m "AInoteManagement v1.5 editor fixes" && git push origin main`

## 限制與注意
- 需要 Streamlit 版本支援 `st.data_editor`、`st.radio`。
- 瀏覽模式切換組別時顯示整組筆記；編輯模式選取文件可編輯該層內容。
- 圖片貼上需在貼上元件內聚焦後按 Ctrl+V；若 Storage RLS 未授權，圖片仍會上傳失敗。
- 圖片存入 Supabase 私人 Storage，表格內容以 Markdown 儲存。
- 本版已通過 Python 語法與 ZIP 完整性檢查，但未連接你的 Supabase 或在 Streamlit Cloud 進行端到端測試。

### changelog/README_v1_7.md

# AInoteManagement v1.7 — 批量存檔與快速定位

## 功能
- 編輯模式：同一工作區所有區塊連續排列，不再分成展開框。
- 批量儲存工作區：一次儲存正文、文字區塊及表格，逐項確認 Supabase 更新回傳的資料列，並顯示成功數量、失敗數量及各項錯誤。
- 圖片：保留專用貼上、拖曳、上傳及「儲存圖片」按鈕，儲存成功提示可跨頁面重新執行顯示。
- 瀏覽模式：以 GROUP 組別為單位，新增「快速定位目錄」，點選子文件名稱跳至對應章節。
- 修正 requirements.txt 中不正確的字面 `\n`，補上 pandas 依賴；將舊版 use_container_width 更新為 width。

## 部署
1. 先備份重要筆記及資料庫。
2. 解壓縮覆蓋原專案，保留 `.git` 和部署 Secrets。
3. 執行 `git add .`、`git commit -m "AInoteManagement v1.7 batch save and TOC"`、`git push origin main`。
4. 在 Streamlit Cloud 確認部署完成，再測試新增文字／表格、批量儲存、重新載入驗證內容、快速定位與圖片儲存。

## 注意
- 批量儲存不是資料庫原子交易；部分失敗時，已成功的區塊不會自動回滾，失敗項目可修正後重試。
- 圖片上傳需另按「儲存圖片」，不會在批量儲存時自動上傳尚未提交的剪貼簿資料。
- 尚未在實際 Supabase / Streamlit Cloud 進行端到端測試。

### changelog/README_v1_7_1.md

# AInoteManagement v1.7.1 — 儲存與快速定位修復

## 已修正
- 修正瀏覽模式 `NameError: name html is not defined`：新增 `import html`。
- 批量存檔逐筆執行 UPDATE，並再 SELECT 核對 Supabase 儲存的 Markdown / 表格內容；只有核對相同才算成功。
- 儲存結果列出成功數、失敗數、UTC 時間與每個失敗區塊的錯誤訊息。
- 保留同層連續式工作區、圖片貼上與上傳、表格編輯、GROUP 快速定位、登入記憶。

## 部署
解壓縮覆蓋原專案（保留 `.git`），執行：

```powershell
git add .
git commit -m "Fix TOC NameError and verify batch save"
git push origin main
```

## 測試
1. 開啟 GROUP 瀏覽模式，確認快速定位目錄不再產生 NameError。
2. 切換編輯模式，在工作區正文輸入測試文字，按「批量儲存工作區」。
3. 檢查成功提示（含 UTC 時間），重新整理網頁，確認內容仍存在。
4. 新增 Markdown 與表格區塊後重複測試；失敗時將畫面上的錯誤類型與 Manage app → Logs 貼回。
5. 圖片須透過圖片區的「儲存圖片」獨立上傳。

**注意：** 本版未連線至你的 Supabase 進行端到端測試。若 RLS、資料庫欄位或 Storage 權限有問題，仍會失敗，但現在會提供具體錯誤。

### changelog/README_v1_7_2.md

# v1.7.2｜工作區存檔修正

- 增加「儲存此工作區正文」獨立按鈕。
- 批量存檔保留，成功與失敗訊息在瀏覽模式、編輯模式都會顯示。
- 每次 UPDATE 後 SELECT 核對資料庫內容；若未儲存會顯示錯誤而非虛報成功。
- 保留圖片、表格及 GROUP 瀏覽快速定位功能。

請備份資料後覆蓋專案並推送 main。
本地只驗證 Python 語法和 ZIP 完整性；沒有連接實際 Supabase。

### changelog/README_v1_7_3.md

# v1.7.3 儲存流程修正

- 移除容易誤導的「儲存此工作區正文」按鈕；它只儲存容器本身，不會儲存 T1 等同層文件。
- 編輯模式底部的「儲存全部變更（正文＋文字＋表格）」會儲存所有編輯區塊。
- 每一區塊寫入後都會從 Supabase 重新 SELECT 比對內容；回報列出成功的文件名稱及失敗原因。
- 圖片繼續透過各圖片區塊的「儲存圖片」上傳。
- 編輯完成後必須點「儲存全部變更」並看到成功提示，才切換瀏覽模式。
- 日誌沒有顯示 Supabase 寫入錯誤，無法單憑日誌判斷先前是否真的發出存檔操作。

部署：覆蓋 GitHub 專案，保留 .git 和 Secrets；git add . && git commit -m "Fix save all workflow" && git push origin main。

### changelog/README_v1_8.md

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

### changelog/README_v1_9.md

# AInoteManagement v1.9｜存檔及表格建立修正

## 變更
- 修正並強化工作區儲存：文字、表格皆有獨立「儲存」按鈕，保留「儲存全部變更」；每筆更新後重新向 Supabase 查詢內容核對。
- 每次儲存成功會顯示文件名稱、成功數量與時間；失敗會顯示例外名稱和訊息，並記錄至 Streamlit Logs。
- 左側 Explorer 右鍵「新增表格」：輸入檔名後先顯示建立表格表單，必須確認 M × N 和 X × Y 才建立文件。
- 編輯模式「新增表格」：同樣先填寫 M × N、X × Y，再確認建立。
- 預設 M=3 列、N=3 欄，X=120 px 寬、Y=40 px 高。寬度 60–600 px，高度 28–240 px。
- 表格的標頭和內容使用同一套固定寬高 CSS；手機版可水平捲動。
- 格子尺寸儲存在 Markdown 前綴 `<!-- ainote-cell:120x40 -->`，無須 Supabase migration；舊版小/中/大設定可讀取。
- 編輯表格使用固定列數（建立時的 M），避免動態新增列造成存檔維度不一致。

## 部署
1. 先備份 Supabase 資料與 `.ainote` 檔案。
2. 將 ZIP 解壓覆蓋原 GitHub 專案，保留 `.git` 及 Streamlit Secrets。
3. `git add .`、`git commit -m "Fix table creation and save v1.9"`、`git push origin main`。
4. 待 Streamlit Cloud 部署後重新整理頁面，使用測試帳號建立 3×3 表格並編輯儲存；切換瀏覽模式、重新整理確認資料仍在。

## 限制
- 無法在此環境連接你的 Supabase 專案，實際 RLS/權限/Cloud 存檔尚未完成端到端驗證。
- `st.data_editor` 編輯表格目前主要支援內容儲存，欄位名稱需透過程式建立時的預設欄名；後續可增加欄名修改。
- 批量儲存為逐筆更新，不是資料庫交易；部分成功時會分別回報。

### changelog/README_v2_0.md

# AInoteManagement v2.0｜圖片載入與切換效能

## 修正
- 圖片改由已登入的 Supabase Storage API 下載位元組，再交給 Streamlit 顯示；不再依賴可能是相對路徑或過期的 signed URL。
- 每個使用者的圖片在目前 Streamlit session 內快取五分鐘，避免瀏覽/編輯切換時重複下載；最多保留約 25 張圖片的快取項目。
- 圖片剪貼簿內容保存在 Streamlit session_state，避免重新執行後貼上資料消失；儲存成功後清除。
- 貼上監聽從指定元素擴展到文件，減少未聚焦造成的貼上失敗。
- 僅當存在圖片資產引用時讀取 assets metadata。
- Storage 下載失敗時寫入 Cloud Logs，並在介面顯示警告。

## 效能改善建議（尚未全部實作）
- 對 GROUP 的內容改用分頁/延遲載入，避免一次渲染所有圖片和表格。
- Explorer 建立文件採用 optimistic UI 並在背景確認，需另外設計衝突/回滾處理。
- 使用資料庫索引 `(owner_id,parent_id,position)`，並限制每次資料查詢的範圍。

## 部署
解壓縮覆蓋原專案，保留 `.git` 與 Secrets：`git add .`、`git commit -m "Fix image loading and improve switching v2.0"`、`git push origin main`。
若仍無法顯示圖片，請查看 Streamlit Cloud Logs 中 `Image download failed`，確認 Supabase Storage policy 允許登入使用者讀取 `note-images/<uid>/...`。

已做 Python 語法檢查與 ZIP 完整性檢查，未進行真實 Supabase 端到端測試。

### changelog/README_v2_1.md

# v2.1 本地優先儲存與圖片顯示切換

- 編輯模式「儲存全部變更」改由瀏覽器元件執行：先備份目前未儲存草稿為 .ainote，才提交 Supabase。
- 帳號設定 → 預設儲存路徑：支援 File System Access API 的瀏覽器可選擇本地資料夾，權限及資料夾 handle 儲存在該瀏覽器的 IndexedDB。非支援瀏覽器回退至一般下載。
- 編輯模式每個圖片區塊可獨立顯示／隱藏圖片。
- 注意：一般下載模式無法偵測使用者是否真的完成儲存，僅能確認已觸發下載；瀏覽器可能封鎖。選定資料夾模式可在寫入完成後才繼續雲端儲存。
- 單獨的圖片/文字/表格儲存按鈕仍沿用舊流程；若需要本地優先，請使用「儲存全部變更」。
- 未經實際 Supabase / Streamlit Cloud 瀏覽器整合測試。

### changelog/README_v2_2.md

# v2.2 圖片貼上與儲存進度修正

- 修正貼上元件的剪貼簿事件：只在貼上區域取得焦點時接收圖片，避免與其他文字編輯器的 Ctrl+V 衝突。
- 使用 UUID 辨識每次貼上，將圖片位元組保存在 Streamlit session_state，避免元件重新執行時遺失。
- 圖片儲存顯示處理、Storage 上傳、資料庫寫入與驗證的進度階段；進度百分比代表階段而非真實網路傳輸位元組。
- 工作區批量儲存依完成的文件數量更新進度條，保留本地優先的儲存順序。
- 圖片失敗時顯示例外詳細內容，方便從 Cloud Logs 定位問題。

## 測試
1. 在圖片區塊點擊貼上框，按 Ctrl+V，確認出現「待儲存」與儲存圖片按鈕。
2. 按「儲存圖片」，確認進度提示與成功訊息。
3. 切換瀏覽模式及重新整理頁面，確認圖片仍能讀取。
4. 編輯文字並按本地優先儲存，確認雲端儲存進度隨文件數更新。

注意：尚未在使用者的 Supabase / Streamlit Cloud 環境完成端對端驗證。

### changelog/README_v2_3.md

# v2.3 重構說明

- 將本地備份與 Supabase 雲端儲存拆分為兩個獨立操作。本地備份不會自動觸發雲端存檔。
- 雲端批次存檔會逐文件更新進度並進行資料庫讀回驗證；個別文字/表格存檔加入進度提示。
- 圖片鏈路：僅初始化一次貼上元件、接收剪貼簿資料後暫存、圖片壓縮、Storage 上傳、assets 建立、文件引用更新、Storage 下載核對。每個階段顯示進度。
- 圖片處理避免重複解碼驗證，WebP 壓縮改為較快的 method=3。
- 文件階層使用 children_index 減少重複掃描；建立表格在左側或工作區都先確認 M×N 與 X×Y。
- Explorer CRUD 操作、表格建立、組別建立及批次刪除/還原新增操作進度與成功/失敗訊息。

注意：進度為工作階段完成比例，非上傳網路位元組進度。File System Access API 的本地儲存仍依瀏覽器權限而定。

測試建議：先備份現有資料，分別測試本地備份、雲端儲存、圖片貼上、表格建立、移動/刪除/還原。尚未連線到使用者 Supabase 進行端對端測試。

### changelog/README_v2_4.md

# v2.4 儲存鏈路重構
- 圖片瀏覽使用 Storage 簽署網址直接在瀏覽器顯示，不再先從 Python 下載位元組。
- 表格由 Streamlit modal 設定列欄與尺寸。
- 裝置登入減少 refresh token 每次 rerun 旋轉的問題。
- 單鍵儲存流程：瀏覽器本地備份回報 → Supabase 寫入 → 資料庫讀回核對 → 成功提示。
- 注意：一般瀏覽器下載無法保證磁碟寫入完成；建議授權預設資料夾。
- 圖片獨立上傳按鈕仍走 Storage；不會隨文字存檔重新上傳圖片。

### changelog/README_v2_5.md

# AInoteManagement v2.5

## 部署前必要操作
1. Supabase Dashboard → SQL Editor → 執行 `sql/migration_v2_5.sql`，允許 `HANDWRITE` 文件類型。此操作不會刪除原有筆記。
2. 以本 ZIP 的檔案覆蓋 GitHub 專案（保留 `.git` 和 Streamlit Secrets），`git add . && git commit -m "Add handwriting and matrix table v2.5" && git push origin main`。
3. 已有帳號的永久註銷功能依賴原本的 `delete-account` Edge Function；刪除 Auth user 後可用相同 Gmail 再註冊，但可能需要重新驗證信箱，且先前筆記不會恢復。

## 更新
- 側欄「⚙️ 設定中心」統一管理回收區、儲存資料夾與帳號註銷。網站無權自行建立 D 槽目錄；先在電腦建立 `D:\\AInoteManagement`，再使用選擇資料夾授權。手機端使用一般下載。
- 新增 `HANDWRITE` 手寫稿：Explorer 右鍵或編輯區新增；觸控筆/滑鼠畫筆、橡皮擦、粗細、筆色、復原、清空、儲存；圖片存入私有 Supabase Storage 並在文件中加入 asset 引用。儲存每次會產生新快照；目前不是可編輯的向量筆跡格式。
- 表格改用可編輯格子，拖曳選取後**右鍵**開啟公式輸入框。支援 `f(row,column)=row*2+1` 及 `A[0,0][1,1]*A[0,2][1,2]`。座標從 0 開始，`*` 在兩個矩陣間表示標準矩陣乘法。選取區較小時截斷；較大時以 `NaN` 填充。輸入文字對齊：靠左/置中/靠右。**「套用函數」和「套用表格修改」會直接寫入 Supabase 並驗證**，不同於整個工作區的本地優先儲存流程。
- 文件標籤有 × 關閉（不刪除資料）；沒有組別時顯示「新建組別文件」，建立後附使用說明書。
- 延續 v2.4 圖片簽署網址直接顯示、本地→雲端→重新查詢存儲流程、主要操作進度提示。

## 限制
- Streamlit 前端的右鍵範圍選取在觸控裝置可用拖曳選取，但手機瀏覽器通常沒有右鍵；若要完整支援長按公式選單，需要後續針對觸控事件加強。
- 編輯表格時請按「套用表格修改」才會儲存；直接切換文件不會自動保存尚未提交的表格輸入。
- 本地儲存只能在支援 File System Access API 且獲得使用者授權的瀏覽器確認寫入；其他瀏覽器只能確認下載已啟動。
- 此版本經過語法與公式測試，尚未在你的 Supabase 和實際瀏覽器進行端對端測試。

### changelog/README_v2_6.md

# v2.6 更新

- 設定中心回收區：依 deleted_at（缺少時依 updated_at/created_at）由新到舊排序；預設僅顯示最近 3 項，允許輸入 N（1–100）及名稱搜尋。搜尋結果也遵守 N 項上限。
- 移除工作區上方的開啟文件標籤列及其 × 按鈕。
- 關閉文件：按「本地保存後關閉文件」，必須先在設定中心授權本地資料夾，並由瀏覽器確認 .ainote 寫入完成，才將選定文件軟刪除、移入回收區並離開工作區。無資料夾授權時不會關閉。備份為所屬組別快照，包含當前文字編輯暫存；尚未透過原有儲存鏈路上傳的圖片不保證包含在備份中，請先完成圖片儲存。
- 手寫稿新增建立對話框，可設定紙張 m × n（像素，200–6000），預設 1200 × 680；尺寸記錄於文件 content，開啟時傳入手寫畫布。
- 保留既有資料讀取、儲存進度條與雲端驗證流程。

部署：直接覆蓋專案並推送，無需新增 SQL 遷移。請在真實瀏覽器驗證 File System Access API 授權、備份與回收區操作。

### changelog/README_v2_7.md

# v2.7 表格互動更新

- 移除表格頂端的 ROW/COLUMN 數字標註列；資料欄位內部仍保留原有的欄名供 Markdown 儲存使用。
- 滑鼠懸停於格子時顯示 0-based `(row*column)` 座標。
- 矩陣公式失敗時立即停止寫入，透過瀏覽器 alert 彈出警告；保留原有 Streamlit 錯誤訊息與進度條。
- 計算成功時沿用原有更新與進度提示。

### changelog/README_v2_8.md

# v2.8 表格操作改進
- 瀏覽模式不再顯示「欄位 1、欄位 2…」的表頭。
- 編輯模式透過全域 pointermove + elementFromPoint 跟隨游標框選，並在邊緣自動捲動。
- 選取範圍後點選「選取範圍數值格式」，可指定小數位數（0–15）或有效數字（1–15）。
- 格式操作僅修改選取範圍內可解析的有限數值，保留非數值字串，成功後寫入資料庫。
- 數值格式寫入的是格式化後的字串，不是單純的前端顯示設定；重新計算時以此數值為準。

### changelog/README_v2_9.md

# v2.9 手寫稿與遞迴公式
- 手寫稿：編輯區只顯示單一畫布；儲存時替換目前圖片引用，不再追加圖片。
- 公式：`f(row,column)=(運算式)<精度>`；精度為小數位數 0–15。
- 遞迴：`f(row-1,column).stop(row<0)`，stop 在遞迴目標座標上判定，成立回傳 0；遞迴深度限制 64，超出立即報錯，整批不寫入。
- 比較：< <= = >= > !=，回傳 0/1；邏輯：&& ||；位元：& |。
- 使用者範例 `row/(column+1)+f(row-1,column-1).stop(row<0 && column<0)` 在部分格子可能因 column=-1 除以零，會顯示錯誤並停止，不會部分套用。
- 舊版手寫稿如含多個圖片引用，本版只編輯最後一張；下一次存檔時會清除所有舊版手寫稿圖片引用（Storage 中舊資產仍保留）。

### changelog/README_v3_0.md

# v3.0 簡化表格公式語法

以 v2.9 為基礎，**只修改表格公式解析器與公式輸入提示**，保留其他既有功能。

## 新規則

- 直接輸入運算式，不再強制使用 `f(row,column)=(...)<3>`。
- `row`、`column` 從 0 開始計數。
- `@N` 指定小數位數，N 為 0–15。例如 `row/3@2`。不指定時不額外四捨五入。
- `choose(條件,成立時,否則時)`：**只計算被選中的分支**，可安全定義遞迴初始條件。
- `f(列,欄)`：遞迴呼叫同一公式；最多 64 層，超過即報錯。
- `f(列,欄).stop(條件)`：條件在下一層座標成立時回傳 0。
- `f(列,欄).stop(條件,值)`：條件在下一層座標成立時回傳指定值。
- 支援 `< <= = == != >= >`、`&& ||`、位元 `& |`、加減乘除等原有運算。
- 矩陣仍用 `A[左上列,左上欄][右下列,右下欄]`，`*` 為矩陣乘法。
- 保留舊式 `f(row,column)=(row*2+column)<3>` 相容性。

## 複製即可測試

基本公式：`row*2+column@3`

Fibonacci（請框選第一欄至少 10 列）：

`choose(row<=1,row,f(row-1,column)+f(row-2,column))@0`

預期前十列：`0,1,1,2,3,5,8,13,21,34`

另一種 Fibonacci 寫法：

`f(row-1,column).stop(row<=1,row)+f(row-2,column).stop(row<=1,row)@0`

此種 stop 寫法應從 row>=2 的區間開始使用；建議優先採用 choose 寫法。

## 錯誤與儲存

公式先在記憶體中計算整個選取區間，計算失敗拋出錯誤，不回傳部分結果；前端沿用既有錯誤彈窗。保留既有的操作進度提示與 Supabase 儲存方式。

### changelog/README_v3_1.md

# v3.1 更新

- 新建範例組別時的「使用說明書」新增：公式語法範例、GROUP/SUBFILE/內容區塊的文件結構、本地 .ainote 與 Supabase 的儲存流程和限制。
- 圖片與手寫稿新增一次建立 1–20 份，逐份命名、獨立編輯。
- 批次建立顯示進度，遇錯時嘗試刪除已建立的批次項目；若清理失敗會顯示警告。
- 原有表格公式引擎不變。

注意：既有組別中的舊「使用說明書」不會自動覆寫；建立新範例組別才會看到新版內容。

### changelog/README_v3_2.md

# AI-NOTE v3.2

## 變更
- 網頁標題改為 AI-NOTE。
- 圖片：每個 GRAPH 組件可一次選取並上傳 1–20 張照片；照片共用同一個 note ID。
- 手寫稿：每個 HANDWRITE 組件可建立 1–20 頁，選頁後單獨編輯／儲存，儲存後預設鎖定觸控。
- 設定：從側欄展開面板改為獨立頁面。
- 表格：矩陣加法支援 `A[0,0][1,1]+A[2,0][3,1]`，維度需一致（原公式引擎已支援，新增文件範例）。
- 初始教學文件最前面增加 AI 提示詞、匯入 ZIP 注意事項、表格與圖片示例。

## 注意
- 本版本未在實際 Supabase／Streamlit Cloud 環境做端對端測試。
- 批次照片如果網路中途失敗，可能留下未引用的 Storage 資產；錯誤訊息會提醒清理。
- 已建立的舊版初始教學文件不會自動覆寫。
- 請先備份 `.ainote`，再部署更新。

### changelog/README_v3_2_1.md

# BV-Text v3.2.1 修復說明

- 修復手寫稿儲存後 Streamlit checkbox key (`hw_locked_<note_id>`) 已建立卻再次賦值的例外。
- 儲存成功時先記錄待鎖定旗標並 rerun，在下一次渲染 checkbox 前套用鎖定狀態。
- 更新瀏覽器分頁標題、登入頁、未設定 Supabase 畫面、首頁及主頁品牌標題為 BV-Text。
- 保留使用者自訂文件標題及既有 AI-NOTE 教學／封裝格式描述，避免改動匯入格式相容性。
- 未修改 Supabase 資料庫結構。

### changelog/README_v3_3.md

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

### changelog/README_v3_4.md

# BV-Text v3.4

- GROUP 根組別可 COPY、CUT、MOVE、PASTE、拖曳至另一容器；移入後轉為 SUBFILE，以維持 GROUP 僅作根節點的文件結構限制。
- 根組別複製至目標容器時，副本根節點亦轉為 SUBFILE；來源不變。
- 防止循環移動（自身／子節點）。一般文件仍限制同組別移動。
- 「導入本地文件做為子文件」改為頁面中央 Streamlit dialog，可多選文件並確認／取消。
- 未改動 Supabase schema。

### changelog/README_v3_5.md

# BV-Text v3.5

- 根文件（GROUP）右鍵選單允許移入回收區；原有子樹軟刪除機制不變。
- EXPLORER 快速定位改成中央對話框，選擇目標後定位或取消。
- 匯出及本地備份使用根文件名稱命名（移除 UUID／時間戳前綴）。
- 設定頁新增 `.ainote` / `.zip` 下載格式；兩者均為相同的 AINOTE ZIP 封裝內容。
- 已授權的本地資料夾中若存在同名檔案，儲存前詢問是否覆蓋；拒絕則不寫入，雲端存儲流程不繼續。
- 一般瀏覽器下載優先使用 `showSaveFilePicker` 顯示儲存位置／檔名確認（如支援）；否則使用瀏覽器預設下載機制，無法保證同名覆蓋詢問。

驗證：Python 編譯、JS 語法與 ZIP 完整性；尚未在 Supabase／Streamlit Cloud 做端對端測試。

### changelog/README_v3_6.md

# BV-Text v3.6

- 修正快速定位：確認後切回筆記工作區，並在內容頂部顯示選定文件的定位面板。
- 新增獨立「📅 行程表」頁面：目標月份、X 軸週次 / Y 軸星期、滑鼠懸浮日期查看按時間排序的行程摘要、點選日期定位、右側滑動行程卡、日期查詢、顯示前 N 張（預設 5）、建立與刪除行程。
- 行程卡資料存於 Supabase `schedule_cards`，由 RLS 限制僅擁有者可存取。
- **部署前必須先在 Supabase SQL Editor 執行 `migrations/20261011_schedule_cards.sql`。**
- 日期與時間以台灣 UTC+08:00 顯示與建立；目前尚未提供修改既有行程的表單。
- 已完成 Python 編譯與 ZIP 完整性檢查；尚未在真實 Streamlit Cloud / Supabase 進行整合測試。

### changelog/README_v3_7.md

# BV-Text v3.7
- 月曆改為橫軸星期、縱軸週次。
- 右鍵日期開啟中央快捷建立行程對話框。
- 左鍵日期切換當日行程卡。
- 日期懸浮顯示當日按時間排序的行程。
- 沿用 v3.6.1 Supabase schedule_cards 資料表。

### changelog/README_v3_8.md

# BV-Text v3.8

1. 行程可勾選「無指定時間」；資料儲存於 `schedule_date`，`scheduled_at` 設為 NULL。
2. 有指定時間的行程按時間升序；無時間的行程排在後方並按 `created_at` 升序（同時建立則以 id 排序）。
3. 月曆可切換顯示日期或待處理數；待處理數為當天尚未標記「已完成」的行程卡數量。
4. 行程卡新增「已完成」勾選，可在右側直接更新狀態。
5. **必須先在 Supabase SQL Editor 執行 `migrations/20261011_schedule_cards_v3_8.sql`，再部署新程式。**

### changelog/README_v3_9.md

# BV-Text v3.9 — Local-first 雙模式

## 模式

- **SQLite**：設定 `BV_TEXT_STORAGE_MODE=sqlite`，使用 `BV_TEXT_DATA_DIR` 指定固定資料夾；預設為使用者主目錄下 `BV-Text-Data/bvtext.sqlite3`。筆記、行程與圖片存 SQLite。
- **IndexedDB**：設定 `BV_TEXT_STORAGE_MODE=browser`，網站在目前瀏覽器 IndexedDB 儲存快照，Python 僅於目前 Streamlit session 中保留工作資料。瀏覽器資料不會因 Supabase 同步自動更新。
- **Supabase**：仍提供登入和 Token 更新。只有使用者明確按「手動上傳雲端」才將筆記、圖片與行程資料上傳；「手動下載雲端」會覆蓋本地資料。

## 本機 Windows 啟動

```powershell
$env:BV_TEXT_STORAGE_MODE="sqlite"
$env:BV_TEXT_DATA_DIR="D:\BV-Text-Data"
streamlit run app.py
```

資料庫位置為 `D:\BV-Text-Data\bvtext.sqlite3`。請備份該檔案。**固定路徑位於執行 Streamlit 的電腦**。

## Streamlit Cloud Secrets

```toml
BV_TEXT_STORAGE_MODE = "browser"
SUPABASE_URL = "https://...supabase.co"
SUPABASE_ANON_KEY = "..."
```

瀏覽器 IndexedDB 的資料只屬於目前網站來源、瀏覽器及登入使用者。清除網站資料、使用無痕視窗或更換瀏覽器都可能導致資料遺失。請定期下載 `.ainote` 或「本地快照 JSON」備份。

## 手動同步

登入後在左側功能區展開「手動雲端同步」，勾選確認才可按「上傳」或「下載」。上傳採 ID 合併，不刪除雲端多出的資料；下載會取代本地資料。請避免多裝置並行編輯造成衝突。第一次使用新版，舊有雲端文件需**手動下載雲端**，不會自動下載。

## 已知限制

- 仍需要 Supabase 登入，因此尚不支援完全離線登入。
- IndexedDB 透過 Streamlit 自訂元件傳送 JSON 快照，圖片較多時可能遇到瀏覽器配額、元件訊息大小或延遲限制。大量資料建議使用 SQLite 模式。
- IndexedDB 資料同步到瀏覽器可能需要等待元件確認；離開頁面前請確認「正在寫入」提示消失。
- 雲端同步不是交易式多表原子提交；若部分上傳失敗，需重新同步並檢查資料。
- 本次完成本地 SQLite 測試、Python 語法檢查；未執行實際 Supabase／Streamlit Cloud 端對端測試。

### changelog/README_v3_9_1.md

# BV-Text v3.9.1

修正 LocalDB.storage 缺少 @property，造成手寫稿、圖片操作時出現 function object has no attribute from_。不變更資料庫結構與同步規則。

### changelog/README_v3_9_10.md

# BV-Text v3.9.10 — ChatGPT 富文本貼上

在 Markdown 區塊編輯畫面展開「ChatGPT 富文本貼上」，點擊貼上區按 Ctrl+V，按「套用貼上內容」，確認 Markdown 草稿後按原本的「儲存文件」。

支援剪貼簿 HTML 轉 Markdown：標題、粗斜體、超連結、清單、引用、程式碼與表格。支援剪貼簿直接提供的圖片，轉為 asset://UUID 並上傳原有 note-images Storage。沿用既有 .md/.ainote 格式，無需資料庫 migration。

限制：ChatGPT 自訂互動 UI、Canvas、SVG 圖、無法從剪貼簿取得的遠端圖片不保證完整複製；遠端圖片 URL 仍可能失效。複雜巢狀表格與部分 HTML CSS 不能像素級還原。圖片需確認已成功匯入；圖片上傳與文件儲存是兩個步驟。

部署：沿用原 requirements.txt 與 Streamlit 啟動方式。建議先備份既有資料，再以測試 Markdown 區塊測試貼上。

### changelog/README_v3_9_2.md

# BV-Text v3.9.2 — 圖片及手寫稿儲存修正

修正 `LocalDB.storage` 必須是 property 而非方法的相容性問題。新增圖片、手寫稿上傳/下載/刪除回歸測試，並在 app 啟動時檢查 storage 介面，避免在儲存途中才失敗。

## 部署
1. 備份目前本地 SQLite 資料夾或瀏覽器工作區。
2. 解壓縮覆蓋全部專案檔案（特別是 `local_backend.py`、`app.py`）。
3. git add . && git commit -m "Fix local media storage v3.9.2" && git push origin main
4. Streamlit Cloud 重新啟動 App 並重新整理瀏覽器。
5. 測試新增圖片與手寫稿、重新整理後讀取。

注意：若部署後仍有 `function object has no attribute from_`，請確認 Streamlit Cloud 部署分支與目前程式碼一致，並查看 traceback 中的實際檔案位置。

先前失敗的圖片儲存通常不會產生附件：因為 `from_` 在上傳前就拋出例外。若另有其他上傳失敗情境，才可能產生孤兒檔案，請勿直接清空 Storage bucket。

### changelog/README_v3_9_4.md

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

### changelog/README_v3_9_6.md

# BV-Text v3.9.6

- 初始教學提示詞：每次 AI 回應僅允許一個根 GROUP/FOLD；禁止 SUBFILE、巢狀 FOLD，所有 FILE 直接屬於根 FOLD。
- 教學用 structure.json 範例同步改為單層。
- 空工作臺：新增文件時可選「空 FOLD」或「教學 FOLD」，並可輸入名稱；教學 FOLD 內只有一個直接子 FILE「使用說明書」。
- 手機本地備份：對 createWritable 的 NotAllowedError/SecurityError/NotSupportedError 退回一般下載；不將下載視為可驗證的資料夾寫入。

部署：解壓覆蓋原專案，git add .; git commit -m "BV-Text v3.9.6"; git push origin main

注意：尚未於實際手機或 Streamlit Cloud 執行端對端驗證。

### changelog/README_v3_9_8.md

# BV-Text v3.9.8 — 批量刪除行程卡

- 連續建立天數大於 1 時，自動將原始標題範本（含 `(10+d)`）寫入 `batch_tag`，並產生唯一 `batch_id`。
- 行程表右側 → 「⋯ 行程選項」→ 「批量刪除」→ 選擇原始標題，確認後刪除全部符合標籤的行程卡（跨日期、含後來改名者）。
- 不同批次使用相同標題範本，也會一起刪除；畫面提供筆數與確認框。
- 單筆建立及舊版既有行程卡不會自動獲得批量標籤，不能透過標籤批量刪除。
- SQLite 舊資料庫會自動新增欄位；Supabase 手動同步前請先執行 `migrations/20261011_schedule_batch_tags_v3_9_8.sql`。
- 手機 IndexedDB 的資料結構跟隨 SQLite snapshot。
- 跨多張刪除目前不是單一資料庫交易；若中途失敗，畫面會提示已刪除筆數。

### changelog/README_v3_9_9.md

# BV-Text v3.9.9｜行程表本地備份與載入

- 行程表可使用與筆記相同的本地資料夾授權／手機下載機制，匯出獨立 `.bvcalendar.json` 檔案。
- 可透過本地檔案選擇器上傳並載入行程表。
- 提供「合併行程（相同 ID 更新）」及「取代現有行程表」。
- 備份包含日期、時間、標題、說明、完成狀態、批次 tag、批次 ID。
- 匯入會先驗證格式、日期與唯一 ID，使用 SQLite 交易避免部分匯入。
- 不會因本地備份自動上傳 Supabase。
- 手機瀏覽器啟動下載後請確認檔案存在。

部署：git add . && git commit -m "BV-Text v3.9.9 schedule local backup and import" && git push origin main

尚未於手機實機與 Streamlit Cloud 進行端對端驗證。

### changelog/README_v4.md

# BV-Text v4 — Focus / Incremental Save / Composite

- Explorer 右鍵新增圖文文件（COMPOSITE），可對 FOLD/FILE 使用「完全單一編輯」。
- 編輯模式增加「完全單一編輯」入口，專注編輯時隱藏側邊欄及其他工作臺。
- Markdown、圖文文件、表格支援在專注編輯模式儲存；圖片/手寫稿仍使用既有專用編輯器。
- 工作臺「儲存變更文件」僅更新已修改文件，不再強制下載完整 ZIP；完整備份仍可手動匯出。
- 圖文編輯器貼上時嘗試將內嵌 SVG 轉換為 PNG 資源；一般 HTML/CSS 排版及互動元件無法保證像素級還原。
- Escape 受 Streamlit 與 iframe 焦點限制，請使用 Return 按鈕退出專注模式。
- 未執行瀏覽器端及 Supabase 整合測試。請先備份現有資料再升級。

### changelog/README_v4_1.md

# BV-Text v4.1

- 行程卡右側列表改為跨日期排序，以目前臺灣時間的絕對距離排序；無指定時間以當天 00:00 為排序時間，同距離時無時間者優先，再依建立順序。
- 月曆下方新增每日任務與每日任務設定，含標題、可選時間、內容及逐日完成狀態；每日任務不計入行程數。
- 修正編輯行程卡時間勾選狀態：每張卡使用獨立元件 key，時間輸入不再被 checkbox 的表單延遲狀態禁用；提交時依勾選狀態決定是否保存時間。
- 每日任務納入本地快照與行程表 JSON v2 匯出；支援舊版 v1 匯入。
- 若使用雲端 Supabase，先執行 migrations/20261011_daily_tasks_v4_1.sql。
- 尚未完成實際 Streamlit 瀏覽器端端對端測試，請先使用測試資料驗證。

### changelog/README_v4_3.md

# BV-Text v4.3

以 v4.1 上傳專案為基礎的 UI 重構。

- 單一編輯：頂部儲存／返回／更多操作；底部提交；返回未儲存內容時確認。
- Explorer 右鍵：新增文件與文件操作二層選單；在選單項目再次右鍵展開；新增文件左鍵開小型對話框。
- 新建文件僅支援圖文文件、圖片、手寫稿。舊 Markdown 保留相容讀取；TABLE 停用，備份後可手動永久清理。
- 完全單一閱讀：FILE 單頁、FOLD 遞迴連續閱讀。
- 使用者操作指南取代教學提示詞，教學 FOLD 改用圖文文件。
- 工作區的增量儲存移到 Explorer 右鍵選單。

## 部署
解壓覆蓋後執行：
```
git add .
git commit -m "BV-Text v4.3 editor reading and explorer redesign"
git push origin main
```

## 注意
- 先備份資料再使用舊 TABLE 清理。
- 右鍵二層選單需要實際瀏覽器測試；手機長按和完整編輯器圖文貼圖流程尚待端對端驗證。
- 這個版本保留原專案的行程表、同步和本地備份程式，但未進行線上部署驗收。

### changelog/README_v4_3_2.md

# BV-Text v4.3.2｜單一模式導覽與右鍵選單

- 單一閱讀及單一編輯時，Streamlit 左側功能區仍可展開並操作。
- Explorer 選取、單一閱讀／編輯切換、快速定位時，先儲存當前單一編輯文字，再進行跳轉。儲存失敗不會清除草稿。
- 左側切換筆記工作區／行程表／設定時，先提交單一編輯草稿，並離開單一閱讀。
- Explorer 右鍵選單在點擊其他位置（包括樹狀區空白處）時關閉；點擊主頁面使 iframe 失焦時也會關閉。
- 保留二次右鍵展開子選單的方式。

## 驗收注意
- Streamlit sidebar 可由左上角展開；小螢幕可能需要先展開導覽。
- 右鍵選單位於獨立 iframe，主頁點擊時使用 iframe blur 關閉；不同瀏覽器焦點行為需實機驗證。
- 圖片與手寫稿編輯器由其元件自行保存；單一編輯的文字草稿在跳轉前同步提交。
- 尚未在 Streamlit Cloud／手機完成端對端測試。

### changelog/README_v4_3_3.md

# BV-Text v4.3.3

- 完全單一編輯的圖文文件改用與一般編輯模式相同的圖文元件。
- 完全單一編輯頁面不再提供獨立的本地保存繼續／保存關閉操作。
- Explorer 展開圖文文件可看到 `//[章節]//` 目錄並點擊定位。
- 注意：圖文元件的變更需按其內部「儲存圖文文件」才會寫入；返回或跳轉前請先儲存。

### changelog/README_v4_6.md

# BV-Text v4.6

- Explorer 關閉：中央彈窗備份 ROOT，確認後從目前 Explorer 工作階段隱藏 ROOT；不刪除資料庫或本地檔案。
- 下載型備份需使用者確認落地後才關閉。
- 圖文目錄右鍵：編輯快速定位、瀏覽快速定位。
- 編輯定位：將游標定位到標記行；瀏覽定位：滾動到對應標記。
- 注意：未進行真實瀏覽器端到端測試。

### changelog/README_v4_6_1.md

# v4.6.1
- ROOT 備份確認後，將 ROOT 及其子節點移至回收桶，清理編輯草稿；重新整理後不再出現在 Explorer。
- Explorer 取得鍵盤焦點時：Ctrl+D 建立副本、Ctrl+C 複製、Ctrl+X 剪下、Ctrl+V 貼上。
- ROOT 的 Ctrl+D 不支援，請使用 ROOT 匯出/匯入。
- 下載確認前不會移除 ROOT。請先確認本地備份。

### changelog/README_v4_6_2.md

# BV-Text v4.6.2

圖文文件在瀏覽與完全單一閱讀時，將 `//[x]//` 呈現為 `x`，不顯示目錄控制符號。單獨成行的目錄標記仍以章節標題顯示。編輯原文及 Explorer 目錄解析保持不變。

### changelog/README_v4_7.md

# BV-Text v4.7
- 修正雲端 notes_kind_check 不支援 COMPOSITE 的部署問題：先於 Supabase SQL Editor 執行 sql/migration_v4_7.sql。
- 手機 Markdown 表格允許橫向捲動，避免欄位遭擠壓。
- Explorer 增加 ← Previous，記錄工作階段內導覽歷史。
- 以 URL query params 保存目前選取文件與單一閱讀／編輯區，重新整理後恢復。
- 注意：雲端資料庫的 migration 需要手動執行；頁面內精確捲動座標尚未持久化。

### changelog/README_v4_7_1.md

# BV-Text v4.7.1
修復圖文文件儲存失敗：完全單一編輯使用 a,b,c=st.columns(...) 時，在 Python 模組全域覆寫原本指向 LocalDB 的 c，導致 update_note 中的 c.table('notes') 誤呼叫 Streamlit 的 table 元件並產生 pandas.DataFrame 型別錯誤。
已將三個 UI 欄位變數重新命名，避免覆寫資料庫連線。
本版保留 v4.7 的其他功能。尚未完成線上瀏覽器端測試。

### changelog/README_v4_7_2.md

# BV-Text v4.7.2

- 圖文編輯器將 Markdown 管線表格轉換為可編輯 HTML 表格；切換回圖文模式、儲存及重新整理後不再直接顯示 `| ... |` 原始碼。
- 新增「插入圖片／圖表」，可選擇 PNG/JPEG/WebP/GIF，透過既有圖片資產保存流程上傳。
- 修正貼上 SVG 時的圖片重複登記，改進 SVG viewBox 尺寸判斷。
- ChatGPT 的互動式元件無法直接複製為可執行圖形；可用截圖或圖片檔匯入。Markdown 原始碼模式仍保留原始 Markdown。

### changelog/README_v4_7_3.md

# BV-Text v4.7.3

- 深色表格統一底色、文字、邊框及行動裝置橫向捲動。
- 圖文編輯器支援 LaTeX `$...$`、`$$...$$`、`\(...\)`、`\[...\]`，以 KaTeX 呈現並保存原始公式。
- KaTeX 資源透過 CDN 載入，需要網路連線；失敗時保留公式原始碼。
- 瀏覽模式將反斜線公式分隔符轉為 Streamlit 可渲染的美元符號分隔符。
- 請注意表格中的特殊色彩會被統一主題覆蓋。

### changelog/README_v4_7_4.md

# BV-Text v4.7.4

修復圖文文件已儲存圖片重新載入後消失：先將 `asset://UUID` 轉換為短效簽名 URL，供編輯器顯示；儲存時仍使用 `asset://UUID`，避免將簽名 URL 寫回筆記。

改善 SVG 貼上失敗時的備援（保留 SVG 資料）。若 ChatGPT 複製操作未提供 SVG/圖片資料，網站無法憑文字重建互動式圖形，請使用截圖或「複製圖片」後貼上。

尚未完成實際瀏覽器與雲端端對端測試。

### changelog/README_v4_7_5.md

# BV-Text v4.7.5

修復對話中的 SVG 流程圖或圖表貼入「圖文文件」後無法保存、重新載入的問題。系統現在會在上傳前檢查並清理 SVG，移除腳本、事件處理器與外部資源，再以 `image/svg+xml` 儲存；一般 PNG、JPEG、WebP、GIF 圖片仍使用原有處理方式。

SVG 檔案上限為 10 MB，畫布尺寸上限為 25,000,000 像素。儲存後會透過既有資產 URL 在圖文文件中重新載入。

驗證：Python 語法編譯與 SVG 清理／保存路徑測試通過；尚未進行實際瀏覽器及雲端 Storage 端對端測試。

### changelog/README_v4_8_1.md

# v4.8.1
- 目錄化/取消目錄同步寫入雲端內容及編輯快取。
- 閱讀模式右鍵新增插入圖片：本地檔案或 Ctrl+V，成功後插入下一行並儲存。
- Explorer Ctrl+D 改為刪除。
- Previous 定位恢復尚未實作；仍只恢復文件與模式。

### changelog/README_v4_8_8.md

# BV-Text v4.8.8 — HTML Rich Clipboard
- 圖文編輯器 Ctrl+V 優先讀取 text/html，缺少 HTML 時回退 text/plain。
- 保留 HTML 表格，辨識 SVG 元素、SVG Data URI、PNG/JPEG/GIF/WebP，轉成待儲存圖片。
- SVG 以原始 SVG 位元組儲存到 Supabase Storage `note-images`，資料庫僅記錄 `asset://UUID` 參照。
- 辨識 MathML 的 TeX annotation、data-math / data-tex / data-latex，轉為可儲存 LaTeX。
- 缺少來源的圖片顯示紅色 ❗；不捏造或刪除其缺失提示。
- 支援在 Markdown 原始碼模式貼上富文本，轉成 Markdown。
- 貼上後請按「儲存圖文文件」，再重新開啟驗證。
- 限制：ChatGPT 剪貼簿若不包含圖片位元組或 SVG，無法從文字推回原圖；遠端 URL 可能失效。HTML/CSS 複雜排版及互動圖表不能保證逐像素一致。
- 本次僅通過語法驗證，未進行 Streamlit Cloud 端到端測試。

### changelog/README_v4_8_9.md

# v4.8.9 — Paste Range Fix
修正貼上 DocumentFragment 時 `setStartAfter` 針對已清空的 fragment 呼叫造成 InvalidNodeTypeError。插入前保存最後一個子節點，插入後定位游標至該節點之後。保留 v4.8.8 其他功能。

### changelog/README_v4_9_0.md

# BV-Text v4.9.0 SVG parsing fix

- 修正 Markdown 圖片 URL 中 SVG CSS 括號造成的提前截斷。
- 同時更新圖文編輯器與瀏覽器解析器。
- SVG 仍保留為 Storage 獨立 .svg 檔案，Markdown 使用 asset://UUID。
- 無法取得的圖片維持紅色缺失標記。
- 已進行靜態語法檢查；尚未進行 Streamlit Cloud 端對端測試。

### changelog/README_v4_9_1.md

# BV-Text v4.9.1

- 完全單一編輯「提交」改為要求前端送出最新圖文與圖片，只有資料庫儲存成功才退出。
- 瀏覽模式右鍵「插入圖檔」，以瀏覽器檔案選擇器選擇 PNG/JPEG/GIF/WebP/SVG，插入選取行下一行並保存。
- 編輯工具列新增 HRC / COM / MD 模式。HRC 優先 text/html；COM 採純文字與圖片處理；MD 強制純 Markdown 原始碼。
- HRC/MD 模式使用文件首行隱藏標記保存，COM 不加標記；原始內容仍是 Markdown。
- SVG 經驗證後以 .svg 獨立上傳 Storage，正文使用 asset://UUID。
- 未完成實際 Streamlit Cloud 端到端測試；請先備份後部署。

### changelog/README_v4_9_2.md

# v4.9.2 行動裝置渲染修正候選版

- 改善無起始 | 的 GFM 表格解析與手機橫向捲動。
- 圖片載入失敗顯示 ❗，不再無聲消失。
- KaTeX CDN 載入失敗顯示 ❗，保留數學式原始碼。
- SVG 仍需確認貼上是否含原始資料、Storage 上傳是否成功。
- 未經實際手機／Streamlit Cloud 端到端驗證。

### changelog/README_v4_9_3.md

# BV-Text v4.9.3 — HRC mobile and submit hotfix

- 修復提交按鈕未觸發元件提交的問題：設定 submitRequest 後立即重新執行，等待前端回傳 save_close，後端成功寫入後才退出。
- COM 與 HRC 都優先處理剪貼簿 text/html；MD 保持純文字。
- 手機表格增加獨立橫向捲動容器，避免 table display:block 造成表格版面損壞。
- 修正讀取器 KaTeX 載入失敗時引用未宣告 status 的錯誤，保留原始 LaTeX 並顯示錯誤。
- SVG 仍須來源剪貼簿實際包含 SVG XML 或圖片資料，ChatGPT UI 自訂繪圖元件不一定可透過複製取得 SVG；未宣稱此情況已修復。
- 本版尚未進行 PC/手機實際瀏覽器端到端測試。

### changelog/README_v4_9_4.md

# BV-Text v4.9.4 — ChatGPT Clipboard Pipeline Refactor

## 目標
保留既有 Explorer、分割、目錄化、HRC/COM/MD、圖文瀏覽、圖片上傳、提交儲存後關閉等功能，重構 HRC/COM 貼上路徑，優先處理 ChatGPT 複製內容。

## 變更
- 將富文本貼上流程集中於 `pasteChatGPT()`，與 Markdown 顯示/導覽分離。
- 優先解析 `text/html`；缺少時使用 `text/plain`。
- HTML 內 `<svg>` 先序列化為 SVG 原始位元組（Data URI 僅為上傳前的暫存格式），上傳時保存為 `.svg`，正文保存 `asset://UUID`。
- 支援 `<img src="data:image/...">`、`<object>/<embed>` 內嵌 SVG、CSS `background-image` 中 SVG Data URI，以及剪貼簿圖片檔案回退。
- HTML 表格沿用現有表格 Markdown 序列化，MathML 的 LaTeX annotation 沿用 `cleanMathNodes()`。
- HRC/COM 在 Markdown 原始碼編輯區也使用富文本貼上；MD 模式仍為純文字。
- 缺失媒體顯示 ❗，並於貼上狀態列顯示剪貼簿型別，方便定位 ChatGPT 複製問題。
- 修正上傳圖片參照替換時 `clipboard-image://1` 意外匹配 `clipboard-image://10` 的風險。

## 尚未解決或限制
- ChatGPT 自訂 UI、Canvas 圖表或 `<canvas>` 若未提供 SVG/影像位元組，無法無損還原。
- 複雜 CSS/HTML 的完整視覺排版尚未封存為原始 HTML sidecar；目前仍以 Markdown 為主儲存格式。
- 遠端 URL 圖片仍依賴來源存活，不能保證長期可用。
- 本版已通過 Python/JavaScript 語法檢查，未在 Streamlit Cloud 與真實手機完成端到端測試。

### changelog/README_v4_9_5.md

# BV-Text v4.9.5 — 單一 HRC 編輯模式

- 移除 HRC / COM / MD 模式切換器；所有圖文文件使用 HRC 富文本剪貼簿處理。
- 保留「圖文編輯」與「Markdown 原始碼」兩種檢視／編輯工具，兩者不再是獨立文件模式。
- 舊版文件的 `<!-- bv-editor-mode:... -->` 標記會在下一次儲存時移除，既有內容仍可讀取。
- 移除瀏覽模式右鍵「插入圖檔」選項，編輯模式圖片插入不變。
- 未宣稱修復手機 SVG／數學式／表格渲染問題；仍需進行跨裝置驗證。

### changelog/README_v4_9_6.md

# v4.9.6 HRC Pipeline stabilization

- 單一 HRC 模式，保留既有 Explorer、分割、目錄、編輯與提交流程。
- PC / 手機的表格強制採用原生 table display；外層捲動容器負責橫向捲動。
- 數學式解析改為明確檢查結束符號，未閉合公式顯示診斷訊息。
- KaTeX 無法載入時保留 LaTeX 與警告，不會靜默遺失。
- 編輯器的 HTML 貼上空殼會回退剪貼簿文字；遠端圖片載入失敗會顯示警告。
- 成功提交關閉後清理 submitRequest，避免下次開啟重複觸發。

限制：剪貼簿未包含的 SVG 無法重建；手機實機和 Supabase 端對端尚未驗證。

### changelog/README_v4_9_7.md

# BV-Text v4.9.7 — HRC 資源診斷與一致性修正

- 保留單一 HRC 模式、Explorer、目錄化、分割、提交。
- 從 Python 瀏覽器移除殘留的插入圖片介面與檔案上傳流程。
- 以 SVG 檔案內容辨識 MIME，避免歷史紀錄錯誤 MIME 導致無法顯示。
- 貼上階段辨識 canvas 佔位物，標示無法取得影像像素，避免無聲消失。
- SVG 若意外留在富文本 DOM，在轉 Markdown 時也會註冊成獨立圖片資源。
- 閱讀器數學式渲染器未載入時，提供原始公式回退。

注意：這是針對可辨識 SVG 與失敗診斷的增量修正；ChatGPT 若未在剪貼簿提供圖形像素或 SVG，仍無法重建。手機端真實渲染需要實機驗證。

### changelog/README_v4_9_8.md

# BV-Text v4.9.8 — SVG regression compatibility

Compared v3.9.11 clipboard handling with v4.9.7. Earlier editor retained the pasted HTML/SVG DOM; newer versions eagerly replaced SVG with img at paste time. Restore native SVG DOM display during editing, and convert to stored SVG asset on save/source transition. Existing unified HRC and other features preserved. Syntax checks are not browser/Supabase tests.

### changelog/README_v5_0_0.md

# BV-Text v5.0.0 HRC 穩定化與診斷版

## 修正
- HRC 單一模式維持不變，閱讀模式不提供插入圖片。
- SVG 保留原生 DOM 至儲存階段；避免 TOC 更新時重複執行具有副作用的 SVG 序列化。
- 移除 HTML 已包含 SVG 時重複附加原始 SVG 的問題。
- 儲存時只上傳文件實際引用的圖片，使用 SHA-256 去除單次提交的重複上傳。
- 編輯器、閱讀器加入可展開診斷報告與複製按鈕；不紀錄剪貼簿文字內容。
- 數學式與資源錯誤有固定 ID，表格分隔列辨識較寬容。

## 錯誤 ID
HRC-JS-001 JS runtime error；HRC-JS-002 未處理的 Promise 錯誤；HRC-CLIP-001 剪貼簿解析失敗；HRC-SVG-001 SVG 序列化失敗；HRC-SVG-002 SVG XML 驗證失敗；HRC-MATH-001 KaTeX CDN 載入失敗；HRC-MATH-002 公式渲染錯誤；HRC-ASSET-001 資源不存在；HRC-ASSET-002 圖片顯示失敗；HRC-SAVE-001~007 儲存驗證或上傳失敗。

## 注意
此版通過靜態語法與 ZIP 驗證，尚未進行手機實機與 Supabase 端到端驗證。SVG 內容若從來源未被複製到剪貼簿，程式無法重建。舊文件依舊使用 Markdown 中介格式，尚非完整無損的 HTML AST 儲存模型。

### changelog/README_v5_0_1.md

# BV-Text v5.0.1 — HRC 跨裝置解析修復與診斷

## 修正
- 編輯器與閱讀器採用相同的 `hrcNormalizeSource`、`hrcImageTokens`、`hrcInline`、`renderMarkdown` 版本。
- SVG Data URI 圖片語法優先辨識，不讓 URL 編碼直接落入文字輸出。
- 針對舊文件中意外斷行的 SVG Data URI 增加有限度的合併修復。
- Markdown 表格列間空行容錯，避免手機顯示 `| ... |` 原始碼。
- 診斷報告即使 `errors=[]` 仍會記錄文件預期的表格、圖片、SVG、公式數量和已渲染的節點數。
- 新增 HRC-TABLE-002、HRC-SVG-006、HRC-MATH-003、HRC-MATH-004 錯誤碼。

## 注意
- 目前仍以 Markdown 作為文件中介格式；無法還原原始剪貼簿中不存在的 SVG。
- 未執行 Samsung Internet 與 Streamlit Cloud 實機測試，請先備份 Supabase 資料再部署。
- 診斷記錄僅包含數量和錯誤摘要，不保存完整文件內容。

### changelog/README_v5_0_2.md

# BV-Text v5.0.2 — SVG Data URI Recovery

基於 v5.0.1，修復舊 HRC 文件中 `![](data\:image/svg+xml;...)` 解析失敗。

- 編輯器與閱讀器共用相同圖片 token 解析邏輯。
- 相容 Markdown 跳脫的 `data\:image`、`\(`、`\)`。
- 支援大型、跨行 SVG Data URI。
- 保留既有表格及 KaTeX 處理。
- `HRC-SVG-008`：偵測並還原被跳脫的 data URI 冒號。
- `HRC-SVG-009`：找不到 SVG 圖片語法結束符號。
- `HRC-ASSET-002`：圖片載入失敗（沿用既有診斷）。

注意：此版本修復解析器，不會自動恢復已從資料庫永久刪除的 SVG，也未經手機實機驗證。

### changelog/README_v5_0_3.md

# BV-Text v5.0.3

獨立重寫圖文編輯器貼上入口 `pasteGPT503`，舊 `pasteChatGPT` 不再被事件呼叫。

- 優先 HTML：保留標題、表格、行內格式、LaTeX 註記，將內嵌 SVG 轉成可保存的圖片資產。
- 無 HTML 時：以 Markdown 渲染純文字（包含表格與數學式）。
- 支援剪貼簿圖片檔案作為備援。
- 保留原有儲存、目錄、分割、資產及閱讀器。

限制：ChatGPT 的 Canvas 或非剪貼簿圖形不能從純文字還原；跨裝置瀏覽器提供的剪貼簿 MIME 可能不同。尚未執行手機、平板實機驗證。

### changelog/README_v5_0_5.md

# BV-Text v5.0.5

- 儲存前使用與貼上時一致的手機 LaTeX 正規化，避免重複的可視文字與 TeX 原碼被存入文件。
- 閱讀器新增同一個正規化器，支援舊文件重新載入時的修復。
- 編輯器/閱讀器增加底部留白，避免最後一行被浮動控制元件或 iframe 截斷。
- 診斷面板改為一般文流定位，展開時觸發 iframe 高度重算。
- 編輯器 iframe 高度上限由 1000 提升到 16000。
- 保留 v5.0.4 SVG 缺失警告；PC SVG 渲染功能未在此版改動。

測試：手機貼上公式→儲存→重新載入→切換閱讀模式；診斷面板展開/收合；滾動到最後一行。

注意：尚未進行手機實機與 Streamlit 線上端對端測試。

### changelog/README_v5_0_7.md

BV-Text v5.0.7: mobile math recovery in editor and reader. Restores TeX-looking formula lines without delimiters; preserves fenced code. Requires device verification.

### changelog/README_v5_0_8.md

# BV-Text v5.0.8 — Mobile SVG and Math safety patch

- Synchronize reader SVG recovery with editor (encoded SVG, escaped colon, missing closing Markdown parenthesis).
- Rejoin wrapped SVG Data URIs before Markdown rendering.
- Stop destructive heuristic removal of formula-adjacent text.
- Limit delimiter-less TeX recovery to standalone formula lines.

Note: Existing stored duplicate math text may need source-level correction; this patch does not silently erase saved content. Device testing has not been performed.
