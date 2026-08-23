# Audio POC Reviewer Report — M2 Progress

**審查日期**：2026-08-23  
**審查角色**：Reviewer（依 `audio_poc_workflow.md` §7 定義）  
**審查依據 SHA**：TTS risk scope `8a2ce01e2fdb120cff3be6a416ca6021ddb57fed`；quality packet `cfba8165ca379d0bbb04e345c198f6f67886c601`
**資料來源**：`docs/milestone/README.md`、`docs/audio_poc_workflow.md`、`docs/milestone/m2_candidate_evaluation.md`、`docs/specs/audio_poc_delivery_checklist.md`

---

## 一、POC 最終目標

| 交付項目 | 說明 |
|---|---|
| 唯一獲准 baseline | VAD、ASR、TTS 各一個，或有證據的 no-go |
| 可重現環境 | lockfile、fixture、harness、schema 全部固定 |
| Raspberry Pi 5 實機證據 | 品質、latency、RTF、RSS、thermal，pinned M3 HAL |
| 20-session 組合驗證 | 三模型同時常駐，failure injection、離線驗證、資源無殘留 |
| 可升格 wrapper | POC / 產品邊界明確，rejected candidates 保留 |

提交完整 SHA 只代表「Ready for internal review」。需 Tester/Reviewer 關閉所有 blocking findings，且 Designer 核准 winner/no-go 後，才算 **POC Accepted**。

---

## 二、Milestone 進度總覽

```
M0  ██████████  COMPLETE    Pi worktree、SSH、環境、timeout/cancel/cleanup 全通過
M1  ██████████  COMPLETE    Option A 基準、100-item fixture、VAD timing labels 已凍結
M2  ████████░░  IN_PROGRESS ← 目前 active
M3  ░░░░░░░░░░  NOT_STARTED
M4  ░░░░░░░░░░  NOT_STARTED
```

**最終交付可達性：`AT_RISK`**

---

## 三、M2 各子軌狀態

| 軌道 | 狀態 | 關鍵事實 |
|---|---|---|
| M2A ASR Baseline Survey | COMPLETE / REVIEWED | 6 required rows 完成；shortlist：small Q8、base Q5、medium Q5 |
| M2B ASR Optimization | GATE_REVIEW | base Q8 primary + small Q8 fallback；24-item blind audit（23 confirmed / 1 erratum）；等待 Core/User review |
| Matcha TTS Qualification | GATE_REVIEW / M3 FINALIST | Lifecycle、network-disabled P12、material resource risk、User 10-prompt quality 均通過；legal limitation 保留 |
| VAD Candidate Evaluation | CHANGE_REQUESTED | ACK-003 未授權 real VAD engine row；目前無關閉路徑 |

---

## 四、已完成的實質成果

### ASR（M2A/M2B）

- Common Voice 26.0 `zh-TW` CC0-1.0 exact 12 clips 取得，source lock 完整（SHA-256 逐檔）
- Internal 8 + Common Voice 12 → 20 筆 16 kHz mono S16_LE WAV 全部 checksum 鎖定
- 6 required rows bounded execution 完成；2 optional rows 以 resource/scope 理由省略（符合規範）
- M2B C dev/holdout 12+12 fixture split（與 M2A 無重疊）；Pi exact SHA 已建立
- P0 + greedy + 固定 domain prompt recipe 提出；prompt 改善 Internal 但 Common Voice +1 edit regression 已揭露（未隱藏）
- Erratum append-only 套用（frozen reference mismatch），原始 results 未改寫

### TTS（Matcha）

- 重用 reviewed 20-prompt performance/resource evidence，不重跑微量 resource matrix
- Bounded lifecycle 覆蓋 error、timeout、cancel、force-abort 與五次 reopen，cleanup 全為零
- True network-disabled P12 inference 成功，network syscall 與 cleanup residue 均為零
- User 固定十段品質評分為九個 5 分、一個 4 分，中位數 5，無 critical misread
- `tts-013` 的 `start` 發音瑕疵保留至 M3/M4 full finalist review，不觸發本輪 tuning

### 流程遵守

- 歷史 evidence（SenseVoice REJECT、Matcha performance、small Q8 diagnostic）均保留原 disposition，未回溯重標
- Candidate SHA 以 immutable commits 固定；`audio` 單一永久分支維持
- ACK-003 intake 已記錄，正確取代 ACK-001/002 的 ASR execution order 與 elimination gates

---

## 五、Blocking Findings

以下任一項未關閉，M2 Exit Gate 均不得通過，M3 亦不得開始。

### BLK-001：VAD 無關閉路徑

- ACK-003 未授權 real VAD engine row，只能以 frozen labels 比較 endpoint/padding
- M2 Exit Gate 明確要求「VAD 有已授權 finalist/no-go 路徑」，現況不滿足
- **需要**：Core/User 另立書面授權（或 evidence-backed no-go 決策）
- 若持續未決，最終交付可達性將從 `AT_RISK` 降為 `NOT_REACHABLE`

---

## 六、活躍風險

| 風險 | 描述 |
|---|---|
| RISK-01 | VAD scope 持續未授權，M2 延誤擠壓 M3/M4 時程 |
| RISK-02 | M2B Common Voice prompt regression（+1 edit）是否影響 provisional selection |
| RISK-03 | Vosk wheel license `UNKNOWN`，legal review 未完成，若進 shortlist 須先解決 |
| RISK-04 | 2 optional rows 省略，material capability gap 未知 |
| RISK-05 | M4 三模型同時常駐的 Pi resource 能否支撐，仍無實機數據 |
| RISK-06 | Matcha training-data lineage 與 archive notice 未關閉，阻擋 redistribution、product adoption 與 final-winner approval |

---

## 七、Reviewer 觀察

### 正面

- M2A/M2B ASR 嚴格遵守「事前固定、單一 scorecard、不下 PASS/FAIL/winner」原則
- Erratum 處理 append-only，evidence integrity 維持
- Bounded execution 與 budget 紀律良好
- Git workflow 符合規範（單一 `audio` branch、immutable SHA、無 force-push）

### 待決策

1. **VAD**：需 Core/User 給出書面決策（最高優先）
2. **M2B**：Core/User 的正式 comparative review 決策尚待完成
3. **M3 entry conditions**：Pi/HAL SHA、target device scope 應在 M2 gate review 時一併確認

---

## 八、最終交付可達性評估

| 交付領域 | 目前狀態 | 到最終關閉的路徑 |
|---|---|---|
| ASR baseline | 有路徑 | M2B gate review → M3 實機 → M4 combined |
| TTS baseline | M3 FINALIST | Matcha 通過 M2 risk-focused screen；M3/M4 full validation 與 final legal decision 尚待完成 |
| VAD baseline | AT_RISK / 目前無授權路徑 | 需獨立書面授權才可繼續 |
| Pi 5 + M3 HAL | NOT_STARTED | 等 M2 close → M3 |
| 20-session combined | NOT_STARTED | 等 M3 close → M4 |

---

*本報告依 `audio_poc_workflow.md` §7（Reviewer 角色）產出，不代替 Designer 做 winner/no-go 核准決策。*
