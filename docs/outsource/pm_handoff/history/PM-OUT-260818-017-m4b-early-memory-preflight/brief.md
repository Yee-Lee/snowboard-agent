# M4b Pi 5 4GB 前期 memory preflight 與跨POC資源預算

- Handoff ID : `PM-OUT-260818-017-m4b-early-memory-preflight`
- Status : `Resolved — post-POC Core integration preflight implemented`
- Finding ID : `OUT-M4B-2026-007`
- Priority : `Blocking before Pi Gate 2A authorization`
- Owner : Core Team Designer（主導Audio / LLM POC跨團隊契約）
- Related handoff : `PM-OUT-260817-015-llm-poc-contract-plan-review`、`PM-OUT-260817-016-m4a-poc-core-evidence-handoff`
- Reviewed Core candidate : branch `dev_agent_m4`, HEAD `f30b8cc3a14222f307dbee52a3a23c479391ef2c`
- Reviewed LLM POC : branch `llm`, HEAD `096cd728a277db584b23a5b0c91e3e7692b672fb`
- Available Audio POC checkout : branch `dev_audio_m2`, HEAD `aad41ce13333bdf94bf6d6ab0996f83982f9f0b1`（團隊仍在工作，不作winner依據）

## 結論與影響

現行contract已正確要求LLM Gate 2B以Accepted Audio package執行P9 residency與P10B 20-session combined test；但這是final winner前的正式驗收，不足以避免Gate 2A投入大量候選測試後才首次發現Pi 5 4GB無法容納OS、Core、LLM、VAD、ASR與TTS。

Core須在Pi Gate 2A授權前主導一個不取代P9/P10B的early memory preflight：固定目標OS baseline、system-wide量測口徑、安全headroom、Audio / LLM envelope交換格式與surrogate版本，讓兩個POC在final combined gate前即可淘汰明顯超出4GB預算的pairing。Audio與LLM POC各自量測並提交evidence；資源分配、threshold與跨團隊協調由Core裁決，不交由任一POC自行假設。

## OUT-M4B-2026-007 — Blocking before Pi Gate 2A authorization

### 問題

現有M4B-P9要求4GB、swap=0、總PSS / RSS不超3.5GB並記錄 `MemAvailable`，Audio P9也要求Core提供LLM residency surrogate；但仍缺少：
- 目標Raspberry Pi OS image與Core skeleton的實測baseline。
- `RSS`、`PSS`、`cgroup memory`與system `MemAvailable`的primary / diagnostic口徑；`PSS/RSS` 不能互換或直接以sum RSS作唯一gate。
- Audio winner產出的steady / peak / cold-load envelope如何交給LLM Gate 2A作前期projection。
- LLM實測尚未形成前，Audio POC surrogate採用何種保守LLM envelope；LLM Gate 2A形成後如何revision並判斷受影響run。
- 在正式Gate 2B前的Green / At-risk / No-go decision及re-estimation trigger。

### 必做修訂

#### 1. Core固定4GB system budget baseline
以正式預定的Raspberry Pi OS Lite 64-bit image與Core最小process tree，在Pi 5 4GB建立versioned baseline packet，至少固定：
- OS image、kernel、firmware、boot config、啟用服務與checksum / 版本。
- 實際 `MemTotal`、idle與Core-skeleton `MemAvailable`、swap設定、CMA / GPU reservation。
- Core parent / Python / IPC的steady、peak與cold-start數據。
- power、cooling、temperature與背景服務條件。

不得以「Pi 5標稱4GB」或一般網路估值代替該baseline。

#### 2. 固定唯一量測與decision口徑
Core須指定：
- Primary capacity evidence : system `MemAvailable` 最低點，以及可用時的cgroup v2 `memory.current` / `memory.peak` 或等價system working-set指標。
- Shared-memory-aware process evidence : 各process `PSS` / `smaps_rollup` 及process tree identity。
- Diagnostic evidence : 各process `RSS`、threads、CPU、FD、temperature、throttling、swap used與swap-in/out、OOM / kernel log。
- Phase evidence : idle、cold load、READY steady、ASR active、LLM prefill/decode、TTS first chunk / generation、cleanup後baseline。

現行 總PSS / RSS不得超3.5GB 須改成不歧義的primary metric與計算式。Sum RSS會重複計算shared pages，只能作diagnostic；若沿用3.5GB上限，須明確說明它套用system used、cgroup working set或sum PSS中的哪一個。

Early preflight與正式P9至少共同要求：
- `swap used = 0` 且無swap-in/out。
- 無OOM、crash或kernel memory pressure事件。
- cold-load與階段交接瞬間峰值都在budget內，不只看steady state。

#### 3. 建立跨POC resource envelope契約
Audio與LLM都使用同一schema提交：

```yaml
environment_id
component_set / artifact IDs / checksums
process_tree
thread_count
steady_pss_mb
active_p95_pss_mb
cold_load_peak_pss_mb
minimum_memavailable_mb
cpu_load_profile
temperature / throttling
swap / oom
measurement_method / sample interval / duration
cleanup_baseline
```

- Audio POC在VAD+ASR+TTS finalist同時常駐後，交付 `audio_resource_envelope`，不能只將三個獨立RSS相加。
- LLM POC在Gate 2A每個finalist交付 `llm_resource_envelope`，固定runtime、model、quantization、KV、MTP、threads與token envelope。
- 任一artifact、quantization、KV、MTP、thread、OS或process-lifecycle變更，必須產生新revision並標示哪些preflight / Gate evidence失效。

#### 4. 在昂貴Gate 2A前加入early preflight
不新增競爭Gate名稱；在既有Gate 2A authorization / work-package entry加入以下順序：
1. Core發布OS/Core baseline與versioned conservative LLM envelope，供Audio P9 surrogate使用。
2. Audio finalist產生實測Audio envelope；未完成時可用Core核准的保守Audio surrogate作LLM planning，但不能轉正式PASS。
3. LLM finalist做最小Pi smoke後，以實測LLM envelope + Audio envelope / surrogate執行system reservation preflight。
4. Core依固定規則標示 `Within budget`、`At risk / re-estimate` 或 `No-go before full qualification`。
5. 只有 `Within budget`，或Core書面接受且有明確改善work package的 `At risk` pairing，才投入完整Gate 2A lifecycle / quality / soak；明顯超預算者先比較較小artifact、KV、MTP、thread或fallback model。

#### 5. 固定Core主導與回流
- Core Team Designer擁有OS/Core budget、surrogate revision、threshold與跨POCdecision。
- Audio / LLM POC Team各自擁有自己repo中的runner、manifest與量測evidence，不得互相代寫或修改repo。
- 若preflight發現4GB不可行，Core決定candidate縮減、resource lifecycle change、8GB產品變更提案或no-go；8GB informational結果不能自行修復4GB mandatory fail。
- 若需改變模型常駐策略、process owner、RM lifecycle或產品contract，另提architecture / contract change；POC不得為通過數字隱性卸載模型。

### 驗收方式
Core提交的權威文件能讓Audio與LLM POC使用同一versioned baseline / schema / decision rule完成early preflight，並能從任一結果追溯OS、artifact、config、surrogate、量測方法與cleanup。至少提供一個可執行的synthetic packet self-test，證明共享頁不被sum RSS錯誤重複計算、memory pressure可使測試失敗、cleanup後回到baseline。

正式M4B-P9 / P10B仍保留且要求Accepted Audio exact package；本finding只把容量風險提早，不降低final gate。

## Core回交要求
Core直接修訂既有權威contract / milestone / test specification，不另建立第二套Gate。至少檢查並按需更新：
- `docs/outsource/deliveries/DELIVERY-LLM-POC-M4B-CONTRACT-001.md`
- `docs/outsource/deliveries/DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md`
- `docs/milestones/M4.md`
- 適用的M4a / M4b test specification、resource schema與surrogate specification

若影響process owner、resource lifecycle或產品public contract，修訂唯一 `docs/arch.md`；否則在response聲明 `Architecture change: No` 並說明理由。

本輪正式response固定為：
- `docs/outsource/responses/PM-OUT-260818-017-m4b-early-memory-preflight.md`

Response須定位 `OUT-M4B-2026-007` 的權威修改路徑、Core owner、baseline / surrogate ID與revision規則、Audio / LLM envelope producer、Gate 2A entry影響、P9/P10B不被取代的聲明、未決threshold及被測implementation SHA。若Core另發delivery，只在response引用，不複製內容。

請提交單一reviewable commit；PM拉回後另記錄branch HEAD完整SHA。Core須直接與Audio / LLM POC Team完成技術對齊，PM不代傳逐輪問題。

## PM動作
PM只交付本 `brief.md` 給Core Team。Core提交response並push後，PM拉回Core約定branch並通知Designer exact-SHA intake；Core再將已commit的baseline / surrogate / schema與decision rule直接交付兩個POC團隊。POC repo的任何修訂仍由各POC團隊自行一次commit/push，內部與Core不得代改。
