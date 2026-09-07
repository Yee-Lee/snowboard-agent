# Core Team → POC Audio Team: M3 Option A Implementation Validation

- **Delivery ID**: `DELIVERY-AUDIO-POC-M3-VALIDATION-001`
- **Parent decision**: `DELIVERY-AUDIO-POC-M3-ACK-002`
- **References**: `CR-AUDIO-M3-PCM-001`、`M1-NATIVE-AUDIO-001`
- **Status**: `ACTION REQUIRED — BLOCKS CORE AUDIO REAL BACKEND`
- **Requester / decision owner**: Core Team Designer
- **Execution owner**: Audio POC Team
- **Date**: 2026-08-13
- **Deadline**: before Core M3 Audio real-backend package start

## 1. Objective

在target Raspberry Pi 5、INMP441、MAX98357A、`googlevoicehat-soundcard`與direct ALSA `hw:`環境，證明至少一組Option A implementation可重現地完成：

```text
48 kHz / stereo / S32_LE native capture
  -> wired-channel selection + verified valid-bit decode
  -> stateful streaming anti-alias 48→16 kHz conversion
  -> saturating mono S16_LE
  -> exact 320-sample / 640-byte / 20 ms delivery
```

POC負責技術探索、target build與evidence；不得修改Core production source或把POC harness當成Core implementation。Core保留最終dependency與design selection權。

## 2. Candidate rule

先驗證`pyalsaaudio==0.11.0`加`samplerate==0.2.4`這組候選。它們目前不是approved dependency：若任一項無法build、無法滿足async lifecycle、品質或資源要求，POC須記錄可重現的failure，並可提出替代direct ALSA binding或stateful resampler。

每個候選都須提供exact version、source archive SHA-256、transitive dependencies、system packages、license / notice、target build / install命令與runtime library identity。不得只提供套件名稱或branch HEAD。

## 3. Required validation

| ID | 驗證項目 | Required evidence / result |
| :--- | :--- | :--- |
| **P4-A01** | Direct native open | 只用`hw:`；列requested與realized device / rate / channels / format，必須為48 kHz / 2ch / S32_LE；不得由`plughw:`或其他plugin conversion代做 |
| **P4-A02** | Channel與valid bits | 以接線attestation、known signal與raw sample analysis確認mic位於channel 0或1，以及S32 container內有效位元數、alignment、sign與full-scale mapping；不得只由datasheet推論 |
| **P4-A03** | Streaming conversion | 非整齊input chunks持續跨chunk保存filter state；禁止sample dropping與每chunk重建converter；記錄ratio、filter / quality mode與flush semantics |
| **P4-A04** | Signal quality | deterministic 1 kHz / 12 kHz、silence、impulse與clipping fixtures；1 kHz pass-band誤差與12 kHz alias attenuation提供raw計算，alias attenuation至少40 dB；S16輸出不得wrap |
| **P4-A05** | Exact framing | steady-state每次yield恰320 samples / 640 bytes；記錄filter delay、startup buffering、partial output與flush處理；不得以padding / truncation掩蓋ratio錯誤 |
| **P4-A06** | Async responsiveness | 證明capture / playback不阻塞Core event loop、不busy-poll；記錄採用的fd readiness、thread或其他模型及ownership；同時跑heartbeat並提供worst gap |
| **P4-A07** | Lifecycle | 覆蓋`aclose`、cancel、read / write failure、stop冪等與至少10次reopen；每次重置filter / accumulator，無task、thread、fd或ALSA owner殘留 |
| **P4-A08** | Buffer與xrun | 列period frames、period count、kernel / userspace buffer、blocking mode；至少5分鐘capture adaptation及shared-clock playback run，記錄xrun / underrun / overrun；任何xrun須附root-cause與重現 |
| **P4-A09** | Target resources | 10次warm-up後保存capture-to-yield latency raw samples及P50 / P95 / max、CPU、RSS、temperature與throttling；Core依數據核准或要求調整，不可只寫「可接受」 |
| **P4-A10** | Build / license | 從clean target依文件可build / install / rerun；列OS、kernel、Python、ALSA、package與native library版本；binary / wheel / `.so`不提交Core reference |

## 4. Required return structure

POC repository回交至少包含下列可定位內容；可依既有目錄命名，但manifest中的relative path必須完整：

```text
poc_audio/
├── deliveries/
│   └── DELIVERY-AUDIO-POC-M3-OPTION-A-VALIDATION-001.md
├── tools/
│   └── <reproducible option-a runner>
├── harness/
│   └── <source and deterministic fixture generator>
└── evidence/m3_option_a/
    ├── manifest.json
    ├── environment.txt
    ├── config.sanitized.*
    ├── results.*
    └── raw/
```

`manifest.json`至少列：POC full SHA、hardware / wiring、sanitized config SHA-256、runner與fixture SHA-256、candidate source hashes、license、每個P4 Test ID狀態、raw artifact path、開始 / 結束時間與完整reproduction command。未執行為`Pending`，硬體或環境不足為`Blocked`；不得標成`Pass`。

Sanitized config可進reference，但不得含credential、operator account、endpoint或private absolute path。Raw PCM若因大小或隱私不適合進Git，manifest須提供fixture產生器、摘要hash與retention location；不得以無法定位的口頭結果取代。

## 5. Return decision table

POC delivery必須對下列項目逐一推薦，不得只回覆「Option A works」：

| Decision item | Required answer |
| :--- | :--- |
| Direct ALSA binding | selected candidate、version、hash、license、理由與rejected alternatives |
| Resampler | selected candidate、version、hash、license、filter mode、state / flush API |
| Valid-bit mapping | channel index來源、valid bits、alignment、conversion formula與evidence path |
| Buffering | period frames / count、accumulator策略、實測latency / xrun trade-off |
| Async I/O | event-loop integration或bounded worker ownership、cancel / cleanup模型與heartbeat結果 |
| Deployment | target system packages、source-build steps、runtime identity、notice requirements |
| Residual risk | 已知限制、未通過項目、是否仍可達成M3 AudioInput contract |

## 6. Gate disposition

在POC回交完整40-character SHA且Core Designer發出final selection ACK前：

- Developer可實作Audio Protocol、mock/null、native / stream config schema與fake-source seam / test skeleton；
- Developer不得開始或mergeAudio real backend、production dependency lock、valid-bit allowlist、buffer / period或async I/O final implementation；
- Display、Camera、GPIO及其他M3 package不受本delivery阻擋；
- M3 Audio real acceptance保持`Blocked by Audio P4`。

POC P4通過後，Core仍須對產品exact implementation SHA執行`M3-AUD-*`與`M3-AUDI-*`，POC evidence不能直接宣告M3 Accepted。
