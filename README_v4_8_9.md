# v4.8.9 — Paste Range Fix
修正貼上 DocumentFragment 時 `setStartAfter` 針對已清空的 fragment 呼叫造成 InvalidNodeTypeError。插入前保存最後一個子節點，插入後定位游標至該節點之後。保留 v4.8.8 其他功能。
