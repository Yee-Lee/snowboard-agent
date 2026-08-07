# Audio POC 工作流程與合作方式

狀態：Authoritative working process  
最後更新：2026-08-07

## 1. 目的

本文件定義 Audio POC 從環境就緒到正式交付的完整工作方式。所有工作以
`docs/pm_handoff/audio_poc_delivery_checklist.md` 的最終交付為起點反推；每項工作都必須能回答：

1. 它推進哪一個最終交付項目？
2. 完成後產生什麼可重現證據？
3. 若結果失敗，最終目標是否仍可達？

無法回答以上問題的工作不進入目前範圍。

## 2. 最終交付目標

POC 最終必須交付：

- VAD、ASR、TTS 各一個唯一獲准 baseline；若沒有候選達標，提交明確且有證據的 no-go。
- 固定 engine、artifact、version、model/voice、quantization、checksum、license 與來源。
- Raspberry Pi 5 上的品質、cold/hot latency、p50/p95、RTF、RSS、disk、CPU、temperature 與 thermal 證據。
- 使用完整 SHA 固定的 M3 Audio HAL，在目標 I2S mic/speaker 上通過 start、stop、reopen、failure、cancel 與 cleanup。
- VAD、ASR、TTS 同時常駐，至少 20 個固定 pipeline sessions，且離線與 failure injection 後無資源殘留。
- 可升格的 winner wrapper、不可進產品的 POC code 邊界、rejected candidates 與產品化建議。
- 可重現 repo、lockfile、fixture catalog、result schema、sanitized evidence、delivery manifest 與完整 commit SHA。

提交完整 SHA 只代表 `Ready for internal review`。Tester/Reviewer 關閉 blocking findings，且 Designer 核准 winner 或 no-go 後，才是 `POC Accepted`。

## 3. 範圍與非目標

本 POC 只比較及驗證 VAD、ASR、TTS，並整合指定 SHA 的 M3 Audio HAL。

不在範圍內：

- 修改產品 composition root、Resource Manager 或 StateManager。
- Barge-in、AEC、wake word/KWS、跨 process mic handoff。
- 為了候選方便而改變產品事件語意。
- 在 Listen/Speak wrapper 隱式 resample。
- 未先通過 license、artifact、offline、aarch64 進場條件的效能優化。
- 與最終 delivery checklist 無關的泛用框架或產品功能。

## 4. Milestone 結構

M0 是遠端與證據鏈的 readiness gate；M1–M4 是四個正式交付 milestone。狀態及分檔入口見 `milestone/README.md`。

| 階段 | 核心問題 | 主要產出 |
| --- | --- | --- |
| M0 | 我們能否可靠操作 Pi 並收回可信證據？ | SSH、權限、控制、傳輸、環境盤點與 evidence chain |
| M1 | 比較基線與 co-I2S/M3 前置能力是否可信？ | frozen gates、harness、fake、fixtures、co-I2S capability |
| M2 | 哪些 VAD/ASR/TTS 候選值得進入真實硬體 finalist？ | 完整 candidate runs、advance/reject、finalists |
| M3 | Finalists 是否通過目標 Pi 5 與 pinned M3 HAL？ | hardware-qualified winners 或 no-go、Pi/HAL 證據 |
| M4 | Winners 同時常駐後是否仍能交付？ | 20-session/failure/offline 證據、delivery package |

後一個 milestone 不得默認開始。必須先確認前一 milestone 的 exit gate，或記錄獲准的調整請求。

## 5. 以始為終的控制循環

### 5.1 Milestone 進場

進入每個 milestone 前必須：

- 重讀最終 delivery checklist 及本 milestone 對應項目。
- 確認 entry conditions、硬體、人員、artifact、SHA 與前置決策已具備。
- 更新「最終交付可達性」：`ON_TRACK`、`AT_RISK` 或 `NOT_REACHABLE`。
- 只展開本 milestone 必要的測試案例、命令與實作細節。

### 5.2 執行中

每個工作項必須綁定 milestone exit gate 或最終 checklist。結果只允許：

- `PASS`：前提一致、證據完整且達 frozen gate。
- `FAIL`：證據完整且未達 gate。
- `INCONCLUSIVE`：環境、證據或測試方法不足，不能推論 pass/fail。

`INCONCLUSIVE` 不得包裝成 pass；`FAIL` 不得刪除。發現偏差時先判斷是否影響最終交付，再決定修正、重跑、淘汰或提出調整請求。

### 5.3 Milestone 收尾

Gate review 必須確認：

- Exit conditions 是否逐項有 evidence。
- 所有失敗、限制與 rejected paths 是否保留。
- 下個 milestone 的 entry conditions 是否可滿足。
- 最終 checklist 尚缺哪些項目，預估是否仍可完成。
- 是否需要 change request，而不是默默改門檻或擴張範圍。

完成後更新 `milestone/README.md` 的狀態、交付可達性與下一步。

## 6. 硬體測試與證據工作方式

Assistant 擔任 technical lead/test controller；User 擔任產品決策者與現場 hardware operator。若 SSH 可用，Assistant 可在授權範圍內直接執行遠端命令。

每次硬體測試先建立 test packet，至少包含：

```text
test_id
delivery_requirement
purpose
preconditions
repo_sha / baseline_sha
hardware_and_environment
commands
repeat_count
pass_fail_gate
required_evidence
cleanup_check
```

回傳 evidence 至少包含：

- 原始命令、時間與 exit code。
- Pi 型號/RAM、OS、kernel、driver、device、PCM format。
- stdout/stderr 與必要的 sanitized kernel/audio log。
- latency/resource/temperature/xrun 等原始量測及 summary。
- WAV/artifact metadata 與 checksum；敏感檔案只記受控位置。
- 結束後 process、thread、iterator、stream、device owner 的 cleanup proof。

口頭描述「有聲音」或單次 demo 只能當觀察，不能取代 pass evidence。

## 7. 分工與決策權

| 角色 | 責任與決策權 |
| --- | --- |
| Assistant | 規劃工作、撰寫/審查程式與 test packet、操作獲准的遠端環境、審查 evidence、標記技術 pass/fail、追蹤風險、提出 change request 與 winner/no-go 建議 |
| User | 提供目標硬體與存取、執行實體操作、核准有外部影響的動作、決定商用/license 取捨、確認 TTS 主觀品質、核准產品層 winner/no-go |
| Designer | 凍結契約、品質/資源 gate，核准 baseline 或 no-go；不得在看到結果後偏向候選調門檻 |
| Tester | 定義/確認量測可重現性、failure/cleanup 證據與正式 Test ID，關閉測試 findings |
| Reviewer | 審查 wrapper 邊界、lifecycle/cancel、產品升格介面及 blocking findings |

同一人可兼任多個角色，但 gate 所需的決策與證據責任不得省略。

## 8. 最終交付追蹤矩陣

| 最終交付領域 | 建立階段 | 最終關閉階段 |
| --- | --- | --- |
| Delivery manifest、repo/baseline SHA | M0/M1 建立規則 | M4 |
| Lockfile、harness、schema、fixtures、fake | M1 | M4 重現確認 |
| Candidate manifest、license、checksum、結果 | M2 | M4 索引確認 |
| VAD/ASR/TTS 功能與品質 | M2 | M3 真實硬體確認 |
| Pi 5 與 M3 HAL | M1 能力盤點 | M3 |
| 20 sessions、failure injection、offline | M4 | M4 |
| Winner/no-go、rejected candidates、產品化建議 | M2/M3 累積 | M4 |
| 資料安全與 sanitized evidence | M0 起持續執行 | M4 audit |

若矩陣中的任何最終項目沒有 owner、來源或可行關閉路徑，狀態至少標記為 `AT_RISK`。

## 9. 調整請求

以下情況不得自行繞過，必須提出 change request：

- M3 HAL 無法取得完整 SHA 或不符合既定 Audio 契約。
- co-I2S clock/device 限制使要求的 lifecycle 或 PCM format 無法成立。
- 所有候選因 license、artifact、offline、aarch64、品質或資源 gate 淘汰。
- frozen gate、fixture 或產品契約需要改變。
- 新需求會加入 barge-in、AEC、wake word 或其他既定非目標。
- 時間、硬體或人員限制使 delivery checklist 無法完整關閉。

Change request 至少記錄：觸發證據、受影響的最終交付、可選方案、成本/風險、建議與決策者。未獲核准前，不降低 gate、不替換驗收語意。

## 10. 文件與狀態維護

- `milestone/README.md`：唯一 milestone 狀態入口。
- `milestone/m0_*.md` 至 `m4_*.md`：階段大綱；進場時才展開細節。
- `poc_audio/evidence/`：預定 evidence 索引位置。
- `poc_audio/deliveries/`：預定 delivery manifest 位置。

模型、大型 raw results、私有語音、敏感 transcript、API key 或 secret 不進 Git。路徑若需調整，應在 M1 明確決定並同步 delivery checklist 對應方式。
