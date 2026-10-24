## Proposal: Audio M3.1 Remediation Stage

建議在 Audio M3 與 Core M4 integration 之間，保留一個**條件式 M3.1 remediation stage**。

### 目的

M3 的主要責任仍維持：

* Target hardware / HAL qualification
* 找出真實產品環境中的 blocker
* 不在 M3 內進行大量 tuning / parameter matrix

若 M3 發現明確、可修復的問題，例如目前 VAD 的 **low-volume speech onset loss**，則進入 M3.1。

### M3.1 原則

M3.1 不是固定 milestone，也不是 DSP exploration。

只有在：

1. M3 發現具體 blocker
2. 有 evidence 支持可能 root cause
3. 有明確、最小化 remediation

時才啟動。

例如：

* input level 問題 → fixed front-end gain
* VAD trigger boundary 問題 → fixed pre-roll buffer
* SNR 問題 → 一項必要的 front-end processing

修改後只做 targeted regression / re-qualification，不進行 AGC、NS、HPF、threshold 等大量組合測試。

### 與 Core 的關係

```text
Audio M3
Target HW Qualification
        ↓
PASS ─────────────→ Core integration can proceed
        │
        └─ blocker found
                ↓
              M3.1
       Focused remediation
                ↓
        re-qualification
                ↓
        close before M4 acceptance
```

M3.1 不一定要阻止 Core Developer 開始 adapter / Event Bus / lifecycle 等低風險 integration work；但相關 Audio blocker 應在最終 M4 joint acceptance 前 close。

**建議定義：**

> M3 = identify target-hardware product blockers.
> M3.1 = optional evidence-driven minimal remediation and re-qualification.
> M4 = Core integration and system qualification.

