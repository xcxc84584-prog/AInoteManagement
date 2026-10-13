# BV-Text v6.1.8 — SVG Data URI 修正

修正 `hrcImageTokens()` 在已辨識 SVG Data URI 結尾後，仍錯誤進入一般 Markdown 括號掃描的控制流程。原本 `else` 綁定到 `if(isData && end<0)`，導致 SVG 結尾定位被後續掃描覆寫，特別是 `%3C/svg%3E` 的 URI。改為僅在 `!isData && end<0` 時執行一般圖片括號解析。同步修正 editor 與 reader。

已完成 JavaScript 語法檢查與 SVG token 測試；未在實際手機瀏覽器驗收。
