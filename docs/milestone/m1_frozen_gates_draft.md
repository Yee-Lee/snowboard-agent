# M1 Frozen-Gate Decision Record — Draft

狀態：`DESIGNER_APPROVED / NOT FROZEN`
最後更新：2026-08-08  
決策者（Designer）：User
驗證者（Tester）：Assistant / Test Controller

本文件推進 final delivery checklist 的「可重現程式」、「功能與品質證據」、
「Pi 5 與 M3 HAL 驗證」三項。它是 M1 的 gate 草案，不是候選測試結果，
也不把 M1 狀態改為開始。

## 1. 凍結規則

- Designer 核准本文件的版本、fixture 與數值後，才可執行真實 VAD、ASR、TTS
  candidate run。
- 核准後的規則只可透過 change request 變更；不得因某候選結果不佳而放寬。
- 凍結前只允許 deterministic fake、harness 與硬體 capability 測試。這些結果
  不得用來宣告任何 candidate winner 或 reject。
- Tester 必須先以指定 commit SHA 重跑一次，確認命令、schema 與 cleanup proof
  可執行，才可標記為 `FROZEN`。

## 2. 目標硬體假設與待確認事項

目標拓撲已由 User/Designer 確認為「INMP441 mic + MAX98357A speaker amplifier，
共用 I2S BCLK/LRCK，使用 `googlevoicehat-soundcard` overlay」。這是
`demo_audio` 分支 `hw/audio/` 的接線與診斷腳本所描述的配置，而不是硬體
capability 的通過證據。

M1 entry 前，User/Tester 必須在 test packet 記錄且確認：

- 實際接上的 mic、amp/speaker、供電、GPIO 接線和外殼狀態。
- card/device 名稱及 input/output PCM capability。
- 是否使用 `hw:`；若使用 `plughw:`，必須列出 ALSA 自動 conversion 的格式與
  位置，不能把它當成原生 capability。

注意：舊診斷腳本以 `plughw:` 進行 44.1 kHz、2-channel、S16_LE capture，並
註記 INMP441 可能需要 44.1/48 kHz、S32_LE。這與 M3 所需的 16 kHz、mono、
20 ms、S16_LE input contract 有潛在差距。M1 必須先以 `hw:` 量測；若 HAL
無法明確、可測地提供該 contract，應提出 change request，而非在 Listen
wrapper 隱式 resample。

## 3. 不可協商的有效性 gate（建議直接凍結）

| Gate | 初版規則 | 通過證據 |
| --- | --- | --- |
| 可重現 baseline | 每輪有完整 source SHA、lockfile、candidate manifest、fixture catalog、命令及 result schema。 | test packet 與 sanitized result index |
| Candidate 可進場 | aarch64 可安裝；engine/model/voice 版本、來源、checksum、license 與離線使用方式均可固定。 | manifest；任一項不明即不進場 |
| 離線 | 安裝及 artifact 預先完成後，停用網路的 run 不得存取網路。 | network-disabled evidence |
| 取消與清理 | success、timeout、error、cancel、force-abort 每條路徑均有 terminal result；process、thread、iterator、stream、device owner 均為 0。 | lifecycle test 與 cleanup proof |
| 比較公平 | 同一 Pi、同一完整 SHA、固定 threads/參數、固定 fixture、相同 cold/hot 定義與 repetitions。 | packet 中的 baseline fields |
| 資料安全 | 不提交模型、大型 raw result、私人音檔、敏感 transcript、credential 或 endpoint。 | Git review 與受控 artifact index |

## 4. 候選 advance gate（初版數值提案，待 Designer 核准）

以下是為了讓第一輪比較可以開始而提出的保守初值，並非已凍結的產品承諾。
數值以指定 fixture 的 aggregate 結果判定；任一 hard gate 失敗即 reject，
不可用平均值掩蓋 cleanup、offline 或 license 問題。

| 領域 | Proposed advance gate | 測量集合與理由 |
| --- | --- | --- |
| VAD | speech-start recall >= 95%、speech-end recall >= 90%、start boundary p95 <= 300 ms、end boundary p95 <= 700 ms、silence/noise false start <= 1 per 10 min。 | 100 個已標注片段：clear speech、pause、silence、noise 各至少 25。保留首尾音節與 endpoint 風險。 |
| ASR | 台灣華語 core-set CER <= 20%，整句正確率 >= 70%；數字/日期與中英混說另外逐項報告，不以 core CER 掩蓋。 | 測試範圍已確認為台灣華語、中英混說、數字與日期。至少 50 個授權、去識別化 utterances；normalization 規則與 reference text 在 run 前固定。 |
| TTS | User/Designer 在 20 個固定 prompts 的可懂度中位數 >= 4/5，且無未記錄的關鍵誤讀；first PCM chunk hot p95 <= 1.5 s、generation RTF p95 <= 1.0。 | User/Designer 是指定品質核准者。prompts 必含數字、日期、產品詞彙與中英混說；評分規則先記錄，TTS text 不含敏感內容。 |
| 資源與熱 | 各 candidate 連續 20 hot runs 不得 thermal throttle、crash 或資源遞增；peak RSS 建議上限：VAD 250 MiB、ASR 1,250 MiB、TTS 1,000 MiB。 | Pi 5 上記錄 RSS、CPU、disk、temperature、throttle 與 run-to-run delta。此項為第一輪篩選，M4 仍須量測三者同時常駐。 |

若指定產品語言、產品詞彙、Pi RAM 或 UX latency expectation 與上述初值不同，
應在凍結前調整本表，而不是待 candidate 結果出現後再調整。

## 5. 固定量測方法（初版提案）

- 每個 candidate 先進行 3 次不計分 warm-up；之後量測 3 次 cold 與 20 次 hot。
  cold/hot 的 process、model cache 與 artifact cache 狀態必須在 packet 定義。
- 報告 p50、p95、minimum、maximum、RTF、peak RSS、CPU、disk、temperature、
  throttling、xrun，以及所有 individual failure，不只報平均值。
- threads、governor、buffer size、PCM format、driver/device、engine options、
  model/voice/checksum 在同一比較集不得改變；需要不同設定即視為另一 candidate
  variant。
- fixture 必須有 ID、授權/來源、語言、expected output 或 label、duration、
  checksum 與敏感性標記。raw audio 與完整 sensitive transcript 不進 Git。
- latency 使用 monotonic clock；VAD boundary、ASR final result、TTS first PCM
  chunk 與 completion 的起訖點必須由 harness 固定定義。

## 6. M1 硬體 capability gate

這是 capability 證據，不是 VAD/ASR/TTS candidate gate。Tester 須以指定 Pi
worktree SHA 完成下列項目：

1. `hw:` input/output 的 device、rate、channel、sample format capability matrix。
2. 各自 input/output 的 start、stop、reopen；無效 device 的錯誤與 cleanup。
3. sequential rate/format 的 reopen，以及 shared-clock concurrent capability。
4. 16 kHz mono 20 ms S16_LE M3 input contract 的可行性與 conversion location。
5. xrun/overflow/underrun、device owner 與 orphan cleanup proof。

任何一項環境不足或證據缺失應標為 `INCONCLUSIVE`；格式或 lifecycle 與 M3
contract 衝突則標為 `FAIL` 並提出 change request。

## 7. M3 dependency record（M1 entry 所需）

M1 結束前至少要填入下表；branch 名稱不是完成交付的替代品。

| 欄位 | 目前值 |
| --- | --- |
| Core product repository | this repository (`snowboard-agent`); product Audio HAL source is under `src/sbd/core/audio/` |
| Responsible owner (person or team) | Core Team Designer |
| Development branch / PR / tracking issue | `dev_agent_m3` reported by `DELIVERY-AUDIO-POC-M3-ACK-001`; full delivery SHA is `PENDING` |
| Expected delivery date or milestone | Not scheduled |
| Required final artifact | source, tests, authoritative docs and full 40-character commit SHA |
| Known API / hardware risks | 16 kHz input contract vs actual I2S capability; ownership and lifecycle contract pending |

## 8. Approval record

| Decision | Approver | Date | Evidence / commit SHA |
| --- | --- | --- | --- |
| Target hardware topology is correct | User / Designer | 2026-08-08 | INMP441 + MAX98357A + shared I2S + VoiceHAT overlay |
| Fixture sets and metric definitions are accepted | `PENDING` | `PENDING` | `PENDING` |
| Numeric advance gates are approved | User / Designer | 2026-08-08 | Adopt the initial values in section 4 |
| Tester reproduced harness and cleanup checks | Assistant / Test Controller | 2026-08-08 | `334825330d8a5a66bddf1a2c64ae80c737aa552a`; [M1-FAKE-001](../../poc_audio/evidence/m1/M1-FAKE-001.md) `PASS` |

完成四項核准、M1 entry conditions 與 deterministic fake baseline 後，才可把本
文件改為 `FROZEN`，並由 milestone index 明確將 M1 改為 `IN_PROGRESS`。
