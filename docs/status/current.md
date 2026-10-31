# Current handoff

- Updated: 2026-10-31
- Writer: Designer only
- Current milestone: M6 Look
- Current stage: **M6 Design D1–D5 complete — Test Spec entry open**。M5 MQTT Verify PASS（Accepted）；證據見 [`test_spec_M5_mqtt.md` §9](../test_spec/test_spec_M5_mqtt.md)。
- Next owner: Tester（M6 V1–V4 Test Spec）
- Developer entry: **M6 尚未開啟**；Design 已完成，待 Test Spec 完成。
- Verified baseline: `8a64165b142942219679960277e03989cc99657b` 加上 Pi checkout `m5mqtt-formal-verify-20261027-01` 驗收的 M5 MQTT 變更。

## Exact routing

| Owner | 下一步 | 最小讀取範圍 |
| :--- | :--- | :--- |
| Tester | 依已定 YOLO26s 設計撰寫 V1–V4 Test Spec；真相機、完整語音路徑與正常等待預算由產品 Verify 確認 | [design.md](design.md)、[M6 §1–§2、§5](../milestones/M6.md)、[model_spec.md §7](../model_spec.md)、[既有 Look 接面](../implement/ch_m5_tool.md#4-look-投影與原問題接續) |

## Scope boundary

M6 主線是 Camera → YOLO → 確定性結果整理 → 原 Conversation 接續回答；真相機、YOLO runtime
與 Audio／Gemma 在 Pi 共存須實測。成功空偵測與 capture／inference 失敗分開處理，只根據本次
提供的 facts 回答。VLM 兩段式描述是獨立、非阻擋 POC；Wake 與 read／Look 交錯不在本輪。

跨工作站接續時，先讀 `design.md`；它列出 POC 本機資料位置與產品 Verify 待驗範圍。照片、
模型權重、原始結果、逐張判讀及 diagnostic 腳本均未提交，目標工作站必須先取得這些
本機檔案或由同一來源重新準備，不能假定 `git pull` 會帶入它們。
