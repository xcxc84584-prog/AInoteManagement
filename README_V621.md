# BV-Text v6.2.1

- 瀏覽模式右鍵原有選單直接新增「標註起始修正點」「標註末尾修正點」，避免 v6.2.0 的獨立選單與原選單競爭。
- 右鍵開啟時先保存選取區間，點擊選單不會遺失框選。
- HTML `<img loading="lazy" src="data:image/svg+xml,...">` 以受限制的 HTML 圖片節點顯示，支援 data\: 跳脫。
- Markdown SVG Data URI 改用 eager 載入，避免嵌入式捲動容器延遲載入。
- 僅通過靜態語法驗證，請在 PC/手機測試實際載入。
