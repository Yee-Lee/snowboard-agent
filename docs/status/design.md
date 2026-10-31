# Current design status

- Updated: 2026-10-31
- Owner: Designer
- Scope: M6 Look 的 Camera／YOLO 產品路徑；VLM 為獨立 POC
- State: **M6 Design POC D1–D5 complete — Test Spec entry open**。M5 MQTT 已 Pi Verify PASS（Accepted）；M6 產品 Verify 尚未執行。

## M6 設計目標與待固定項

- [M6 §1–§2](../milestones/M6.md) 已定 look-only 流程：原對話選 Look 並播放「我看一下。」後，Look worker 取像、執行 YOLO、整理本次觀察，再由原 Conversation 根據 facts 回答並回 listen；不等待新語音。
- [M6 §2.2.1](../milestones/M6.md) 固定 object detection 與四欄 Look wrapper，facts 包含名稱、合計數量、逐區位置與較明確／不確定層級；同一 Conversation 的 Look 回答用當輪 schema 限制 `intent=speak`。專屬 instruction 已經 Pi 原 Conversation 探針確認。
- 整理 function 使用模型實際 class、confidence、bounding box，依部署政策篩選與排序，形成有界 facts。空偵測不等於物件不存在；未提供的顏色、文字、身分等屬性不可補造。
- [model_spec.md §7](../model_spec.md#7-m6-look--yolo26s-design-selection-2026-10-31) 固定 YOLO26s、CPU runtime、80 類範圍、影像邊界、相機 fixture、選框／計數、啟動／Look timeout 與正常等待預算；真相機與完整語音路徑待 V1–V4。
- Pi 驗收聚焦本次影像與回答的關聯、自動接續、Camera／YOLO 和 Audio／Gemma 共存、capture／inference error、timeout、中斷與 stop 的相關資源釋放。
- [M6 §3](../milestones/M6.md) 的 Camera＋VLM 描述→原對話 LLM 是獨立、非阻擋 POC；研究結果不自動替換 YOLO 主線。
- [M6 §5](../milestones/M6.md) 列出 Design 與產品 Verify 分界；D1–D5 完成後交 Tester 撰寫 V1–V4，Developer entry 仍關閉。

## 選型 POC 進度

- `m6-yolo-poc` topic worktree 保留可重跑的 diagnostic 腳本；照片、人工標記、模型權重、逐張判讀、原始輸出及量測紀錄均置於 Git 忽略的本機 `tests/fixtures/m6_yolo/`。可提交文件不保存 fixture 細節。
- D1／D2 工作站判讀及 D3–D5 Pi 探針完成，選定 YOLO26s 為 M6 實作 baseline。門檻沿用 USER 的 0.75／0.5 與最多三個實體，先選框後彙總，排除低信心與省略內容不代表物件不存在。
- Pi 已完成真實 Gemma Conversation 接續、12 張照片的 standalone／Audio 共存推論、formatter 邊界與類別表、停止／重新推論檢查；另以全新 process 確認 startup 單次固定影像 warm-up 可把首次 prediction 的 lazy initialization 移到 READY 前，第一張真實照片回到穩態範圍。未見 OOM 或節流。修正過的 instruction／schema 已重跑受影響案例。這是 Design POC，不是產品 Verify。
- USER 決定 M6 先維持現行循序 startup 與 READY 前 YOLO warm-up；整體 READY 可能過長列為 BETA 收斂議題，屆時以正式 App 實測比較循序、受控平行與 App／Vision 分離 readiness，不在 M6 偷改 lifecycle。
- USER 用途是個人研究／實驗，Ultralytics 依官方 AGPL-3.0 路徑評估；用途改變時再確認授權。

## 跨工作站接續

下一位 Tester 依 `current.md` 進入後，讀 M6 §1–§2、§5、model_spec.md §7 及既有 Look
接面，建立新增功能與受影響回歸的 V1–V4 Test Spec；不能把 POC 當產品 PASS。
需要重用本機診斷時，資料位置如下：

- Core checkout 的 Git 忽略目錄 `tests/fixtures/m6_yolo/`：12 張照片、人工標記、YOLO26s
  權重、工作站原始輸出與逐張判讀。
- sibling `m6-yolo-poc` worktree：未提交的
  `scripts/m6_yolo_poc.py`、`m6_yolo_compare.py`、`m6_yolo_facts.py`。

Pi 私有診斷程式與結果留在 operator-local POC 目錄；工作站已收回結果至 Git 忽略目錄
`tests/fixtures/m6_yolo/runs/pi-20261031/`。早期失敗嘗試保留，
最終 D3 為 `conversation-final-private.json`，D4 為 `conversation-private.json` 與 `coexist.json`，
formatter／停止結果分別為 `formatter-private.json`／`stop-private.json`，warm-up 比較結果為
`warmup-private.json`。這些檔案不經 Git 同步，需從目前工作站安全複製；若改用其他素材，
重新判讀直接受影響的場景。
