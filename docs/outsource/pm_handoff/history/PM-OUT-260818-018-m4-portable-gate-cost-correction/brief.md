# M4 candidate gate 簡化與執行成本修正

- Handoff ID : `PM-OUT-260818-018-m4-portable-gate-cost-correction`
- Status : `Resolved — implemented at f87c5e6`
- Finding ID : `OUT-PROCESS-2026-001`
- Related handoff : `PM-OUT-260817-014-local-hardware-test-gate-reform`
- Reviewed Core candidate : branch `dev_agent_m4`, HEAD `71b2c97e2ab2e4e632131f2775de7e75746f0a82`

## 結論

014 的目標是避免錯誤candidate上Pi後才發現問題，不是建立通用的硬體驗收framework。現有實作已把人工觀察、READY handshake、nonce / producer PID、debug授權與多層evidence chain做成M4開發前的共用Blocking gate，範圍與維護成本過高。

請將candidate gate縮回下列最小必要範圍。這是一次性流程修正，不重開M3、不重跑M3硬體evidence，也不得繼續擴張gate功能。

## 保留的最小檢查

| 檢查 | 保留理由 | 最小完成方式 |
| :--- | :--- | :--- |
| Exact candidate SHA | 防止測試結果對到錯誤程式版本；這是避免修碼後沿用舊證據的核心 | runner比對外部指定的完整SHA與目前HEAD，不符即停止 |
| Protected paths clean | HEAD SHA無法涵蓋未commit的source / test / runner修改 | 只檢查會影響結果的code、tests、dependency、config contract與runner；不擴張到無關文件 |
| Portable / Pi scope分離 | Ubuntu沒有Pi硬體，誤跑 `rpi` 測項只會浪費CI並產生假問題 | portable command明確不收集 `rpi` marker；Pi command只在實機執行Pi scope |
| Candidate三版本matrix | 目前正式宣告支援Python 3.11 ~ 3.13，candidate freeze前必需確認語意相容 | 只在準備 / 更新frozen candidate或正式候選合併gate時平行跑一次；日常開發只跑主要版本與affected tests |
| Bounded timeout | 已發生過Python 3.12 async / process hang；沒有timeout會無限占用CI或人工測試 | subprocess / suite設定單一明確上限，逾時停止並保留stdout / stderr；不建立額外timeout orchestration framework |
| Run output不可覆寫 | 防止本輪結果覆蓋舊run或把兩輪證據混成一次 | output目錄或run ID已存在就拒絕；不需要跨多層JSON做複雜reconciliation |
| External artifact / config checksum | 模型、native library與Pi-local config不一定在Git；只記SHA不足以重現實測內容 | preflight記錄實際使用的artifact / config checksum；不要求每個中間JSON做複雜建立checksum chain |
| Result與raw log | 需要知道實際命令、平台、Python、exit code與失敗原因 | 每次正式命令保存一份簡單result及stdout / stderr即可 |

## 移除或降級的項目

- 移除通用READY / producer handshake、nonce、producer PID、suite-start record及其相關等待 / 驗證邏輯，不把它們列為portable、preflight或M4開始條件。
- 移除「manual observation缺失 / wrong nonce / prefill」的自動dry-run要求及相關通用framework tests。
- 移除debug必須先驗證正式acceptance FAIL bundle才能執行的限制。Debug是診斷活動，只要結果不能被標記或合併為正式PASS即可。
- 移除為每個failure階段建立完整identity / checksum chain的要求；保留候選SHA、必要artifact / config checksum、run output不可覆寫及原始log即可。
- 取消六項command-level dry run作為M4入口gate。對保留的SHA、dirty、scope、matrix、timeout與run-output檢查提供直接unit / workflow regression即可；只有相關gate程式再次修改時才跑受影響的regression。
- Branch名稱只作診斷資訊；只要完整SHA一致，不得因branch名稱不同拒絕候選。

## 人工操作與紀錄

需要聽、看或操作硬體時，Tester可在現場以口頭方式要求operator執行動作，不需要Core產品runner提供live handshake。

正式驗收仍需由Tester在既有test report / card留下最小結果紀錄：run ID、Test ID、operator、時間與Pass / Fail。這是驗收紀錄，不是自動handshake；不要求nonce、PID、READY檔、獨立record command或額外重錄流程。沒有人工測項的M4 card完全不需要這套機制。

## GitHub Actions portable matrix

`.github/workflows/candidate-portable.yml` 是GitHub Actions CI：GitHub提供Ubuntu runner，分別安裝Python 3.11、3.12、3.13並執行portable tests。它不能驗證Raspberry Pi硬體、Audio device、GPIO、camera、thermal或人工可聽 / 可視結果。

請修正為：
- 不得以整個未過濾的 `tests/` 誤收集Pi-only測項。
- 一般development push不得無條件啟動三版本完整matrix。
- Core可使用candidate branch、manual dispatch、受控PR / merge事件等等效方式；但建立frozen candidate前必須有一次三版本同SHA的portable結果。
- 三版本job平行執行；Pi只跑產品部署runtime，不乘上三個Python minor。

## 完成條件

1. 日常fast loop只需一個主要Python版本與affected tests；每位Developer不需安裝3.11 ~ 3.13。
2. Candidate portable matrix在3.11 / 3.12 / 3.13平行通過，且沒有收集Pi-only node，也沒有用Skip / XFail掩蓋誤收集。
3. Timeout regression證明hang會在上限內終止並留下可讀raw log。
4. Exact SHA、protected-path clean、matrix完整性及run output不可覆寫均有直接且小型的regression。
5. 通用人工handshake、manual dry-run、debug FAIL-bundle授權與多層checksum chain不再是M4 Blocking gate；相關不必要runner、tests與runbook要求已移除或簡化。
6. M3 Accepted SHA與既有20-card硬體證據不變，不要求任何M3重測。

## 不要求回覆

本handoff是單向修正要求。Core Team不需新增或更新 `docs/outsource/responses/`、delivery、說明報告或額外evidence package；只需將必要的workflow、runner、tests與既有流程文件簡化後正常commit / push。

PM拉回最新Core repo並提供branch與完整HEAD SHA後，Designer直接檢查變更範圍；必要的驗證由內部在隔離環境執行，不等待外包文字回覆。

## PM動作

PM只交付本 `brief.md` 給Core Team。不得要求Core重寫014 response、重新解釋既有開發過程、建立人工handshake認證，或重跑M3實體驗收。
