# BV-Text v3.4

- GROUP 根組別可 COPY、CUT、MOVE、PASTE、拖曳至另一容器；移入後轉為 SUBFILE，以維持 GROUP 僅作根節點的文件結構限制。
- 根組別複製至目標容器時，副本根節點亦轉為 SUBFILE；來源不變。
- 防止循環移動（自身／子節點）。一般文件仍限制同組別移動。
- 「導入本地文件做為子文件」改為頁面中央 Streamlit dialog，可多選文件並確認／取消。
- 未改動 Supabase schema。
