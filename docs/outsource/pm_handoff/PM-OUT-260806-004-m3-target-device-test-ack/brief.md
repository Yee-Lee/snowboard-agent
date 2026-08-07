# M3 目標裝置測試方式確認

* **Handoff ID** : `PM-OUT-260806-004-m3-target-device-test-ack`
* **Status** : `Ready for PM`
* **Feedback ID** : `OUT-M3-TEST-2026-001`
* **Related handoff** : `PM-OUT-260805-002-m3-m4-poc-planning`
* **Reference candidate** : `af890249d8634df11b1a30a27aaee1720f5a8b67`

## 結論

M3 是 Raspberry Pi 5 真實 HAL 與硬體 bring-up，正式驗收必須包含內部指定 Pi 的人工操作，但人工只負責接線、按鍵、插拔、觀察與回傳產物；可自動判定的環境、行為與結果應由固定命令收集。本輪只要求外包確認此測試分工與證據原則，不要求修改 code、test、架構或 milestone。

## 必須 ACK 的共識

外包須在正式 repo response 中逐項明確確認；若有異議，須在同一項下列出原因與建議替代方式，不得以未回覆視為同意。

1. M3 依 Hardware readiness、Audio、Display、Camera、GPIO、integration/fallback 分段驗證，不以一次大型人工 smoke 取代分段結果。
2. 每個需操作實體 Pi 的項目使用有 ID 的 test card，至少列前置硬體 / 接線、被測完整 SHA、config hash、命令、使用者動作、預期結果與回傳產物。
3. 測試工具自動保存 Pi 型號、OS/kernel、Python/dependency、device discovery、config hash、命令、時間、exit code、log 與 machine-readable result；人工結果不取代可自動驗證的契約。
4. 使用者隻對喇叭聲音、OLED 可讀性、接線 / 按鍵 / 插拔等不可自動完成項目回覆 checklist，聊天或口頭的「看起來正常」不作 acceptance evidence。
5. 外包 Pi 自驗與內部指定 Pi 的獨立 confirmation 是兩層證據；外包自驗不能取代內部 Tester 對 delivery exact SHA 的正式硬體驗收。
6. 未來 M3 delivery 的大型資訊、影像或影片可落在受控位置，但 repo 內必須提交版本 / checksum、metadata、結果摘要與可定位索引，且不得含 credential 或不必要的個資內容。

## 本輪範圍

* 只要求 consensus ACK 或逐項異議。
* 不要求本輪建立 test harness、test card、M3 code、測試 evidence 或 estimates。
* 具體命令、門檻、硬體清單與 test card 將在後續 M3 Task / test spec 固定；本 ACK 不代表 M3 entry 或 milestone Accepted。
* **Architecture change** : `No`

## 回覆方式

* **Response** : `docs/outsource/responses/OUT-M3-TEST-2026-001.md`
* **Delivery / Evidence** : 本輪不要求。
* Response 須列本 handoff ID、六點逐項 ACK / 異議、尚待內部決策，以及承載 response 的完整 repo commit SHA；PM 拉回後另通知 branch / 完整 HEAD SHA 供 Designer intake。
