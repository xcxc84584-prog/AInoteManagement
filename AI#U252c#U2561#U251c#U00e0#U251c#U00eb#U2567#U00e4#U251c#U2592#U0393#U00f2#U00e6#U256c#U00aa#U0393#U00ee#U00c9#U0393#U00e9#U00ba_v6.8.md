# AI提示詞｜AINOTE 單一圖文文件封包規格

請將你接下來的對話文本打包成能載入 ainote 的 ZIP 文件，並且只能由一個圖文文件組成。對話內容需要有圖片說明，減少 SVG 圖的使用，數學公式必須使用 $$數學式$$。

## ZIP 結構（版本 1）

```text
conversation.ainote （ZIP 格式）
├── manifest.json
├── structure.json
├── documents/
│   └── <document-uuid>.md
└── assets/               # 有圖片時才需要
    └── <asset-uuid>.png
```

`manifest.json` 範例（使用實際 UUID，不可照抄示意值）：

```json
{"format":"ainote","version":1,"root_id":"<document-uuid>","name":"對話筆記"}
```

`structure.json` 必須是陣列，而且**只能有一個節點**，例如：

```json
[{"id":"<document-uuid>","parent_id":null,"kind":"COMPOSITE","title":"對話筆記","content":"# 對話筆記\n內容…","has_page":true,"position":1}]
```

根節點就是這個 `COMPOSITE` 文件，不需要建立 GROUP 或 FOLD。`manifest.root_id` 必須與文件 `id` 一致。`documents/<document-uuid>.md` 存放同一份完整 Markdown 內容。所有 JSON 必須是 UTF-8。

## 文字與圖片要求
- 完整保留對話順序、標題、段落、清單、表格、程式碼及文字說明。
- 只能有一個圖文文件；不得拆成多份文件或額外建立資料夾節點。
- 優先使用 PNG、JPG、WebP 圖片；圖片應放在 `assets/`，並在內容以 `asset://<asset-uuid>` 引用。不要僅使用失效的外部圖片 URL。
- 減少 SVG 圖，盡可能以一般圖片與文字說明呈現。
- 所有獨立數學公式使用 `$$數學式$$`，例如：

$$E=mc^2$$

- 封包完成後，確認 ZIP 能解壓、UUID 關聯正確、圖片確實存在、文件內容完整，並提供 ZIP。
