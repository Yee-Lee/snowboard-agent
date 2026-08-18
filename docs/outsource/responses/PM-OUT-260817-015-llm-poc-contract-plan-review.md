# Response: PM-OUT-260817-015 — M4b LLM POC Contract / Plan Review

- **Handoff**: `PM-OUT-260817-015-llm-poc-contract-plan-review`
- **Findings**: `OUT-M4B-2026-002` ～ `OUT-M4B-2026-006`
- **Status**: `POC committed reply received — revision required before closure`
- **Response owner**: Core Team Designer
- **Date**: 2026-08-17
- **Reviewed Core baseline**: `dev_agent_m3` / `c559e5cf65d20676696293f06f1e5bc2afd02ae6`
- **Reviewed LLM POC baseline**: `llm` / `4ac7ba3941077babf34c7c575003a65f5c541009`
- **Reviewed LLM POC reply**: `origin/llm` / `0cff62f942f2eec82fcc0b0f953a7cc4a2819e3a`
- **Core response SHA**: `Pending PM intake after this response is committed; this file does not self-reference its future commit`
- **Architecture change**: `No`

## 1. 結論與交付

Core已直接修訂既有權威contract [`DELIVERY-LLM-POC-M4B-CONTRACT-001`](../deliveries/DELIVERY-LLM-POC-M4B-CONTRACT-001.md) 與 [`M4.md`](../../milestones/M4.md)，不建立重複addendum。User / PM應將該contract revision交付LLM POC Team；POC依contract §10在自己的repo修訂並commit一次，再回傳reply path、branch與完整40-character SHA。收到committed reply前，Gate 0未完成，Gate 1 / Pi Gate 2不得宣告通過。

本輪已核對POC repo的最新committed HEAD與handoff相同。該repo另有未commit的readiness-correction文件；它不屬於`4ac7ba3...`，不構成receipt、計畫修訂或gate evidence。

## 2. Findings disposition

| Finding | 裁決 | 權威定位 | POC執行影響 |
| :--- | :--- | :--- | :--- |
| `OUT-M4B-2026-002` | **Resolved in Core contract** | Contract §5 P6/P7、§7.1；M4 §6.1/§6.2 | Level 1是cooperative cancel；Level 2包含terminate→bounded wait→必要時kill→waitpid→rebuild/READY；只有force-abort、outer completion或rebuild失敗才是Level 3 product exit 4。Native cancel不可用但Level 2全Pass者可conditional eligible |
| `OUT-M4B-2026-003` | **Resolved in Core contract; execution dependency pending** | Contract §4 Gate 2、§5 P9/P10、§8/§9；M4 §6.2.1 | Gate 2A先跑LLM-only；P9/P10B必須引用Accepted Audio final handoff ID / SHA / kit。缺件為`Blocked`，surrogate不可轉Pass。4GB/swap=0是mandatory，8GB僅informational |
| `OUT-M4B-2026-004` | **Resolved in Core contract** | Contract §5 P2/P3 | 固定exact `LLMResponse` schema、`speak/tool/rest` payload、`listen/read/look` allowlist、tool-intent-only、P5 fallback、20-case × 3 hot repetitions與log hygiene。Fixture / validator須事前凍結 |
| `OUT-M4B-2026-005` | **Resolved in Core contract** | Contract §5 P1～P12、§7.1 | 每個P ID已有Mandatory / Conditional / Negotiable分類與唯一結果語意；P4固定cold/hot量測但門檻仍由Core裁決，不得事後修改方法 |
| `OUT-M4B-2026-006` | **Core crosswalk resolved; POC document update pending** | Contract §8～§10 | External Gate 0 / 1 / 2A / 2B / 3已唯一映射internal milestone、delivery area、P ID與evidence。POC須移除D1～D6 / D1～D8雙軌歧義並回交committed planning packet |

## 3. Audio dependency與owner

Audio與LLM先平行完成standalone Gate 2A。Audio POC以Core核准、versioned deterministic LLM resource surrogate完成其internal M4，經review後產生`POC Accepted` final reference package；因此Audio不等待LLM winner。Core Designer負責intake該Audio handoff ID / SHA / kit並通知LLM POC解鎖Gate 2B；LLM POC再用Accepted Audio package執行P9 residency及P10B combined sessions。這個順序沒有循環依賴，也不把surrogate當正式combined evidence。

## 4. POC repo comparison與必改範圍

在已核對的`llm` / `4ac7ba3941077babf34c7c575003a65f5c541009`中，現行planning仍混用D1～D6與D1～D8、合併External Gate 0 / Internal M0，且未承載本輪cancel、Audio dependency、product output及P1～P12裁決。POC至少應一致更新下列已commit權威區域；可依repo ownership合併文件，但不得留下第二套gate：

- `docs/milestone/README.md`
- `docs/milestone/llm_delivery_gate_draft.md`
- `docs/milestone/m0_llm_readiness.md` ～ `m4_llm_combined_validation_and_delivery.md`
- `docs/delivery/DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT.md`
- 適用的harness / fixture catalog / validator / test與evidence schema

## 5. Architecture與產品文件邊界

**Architecture change: No.** 本裁決對齊既有`docs/arch.md`、`docs/implement/ch02_contracts.md`、`ch06_resource_manager.md`與`ch09_action_payload.md`：沒有新增process owner、IPC、public HAL或lifecycle level。`docs/model_spec.md`與`docs/protocol.md`仍是Core Gate 3 entry deliverables；在POC final winner尚未產生前不得虛構selected model，protocol則在production child integration前完成review。

## 6. LLM POC回覆驗收

POC回覆必須是單一reviewable commit，並在通知中提供：

1. reply / authoritative plan path、branch、完整40-character commit SHA；
2. revision receipt、真實Initial Manifest及唯一crosswalk；
3. Gate 1 frozen harness / catalog / validator、candidate / license與Ubuntu pre-screen packet；
4. Gate 2A / 2B逐work-package owner、dependency、estimate、entry / exit、runner、evidence、cleanup、failure / no-go；
5. 受影響文件清單與尚未決定、需Core threshold decision的項目。

Core收到後只對該exact SHA作intake。聊天、branch name、工作目錄未commit檔案或預填未來SHA均不算Gate 0 exit。

## 7. Core本輪驗證

- 比對LLM POC branch / HEAD與handoff reviewed baseline一致。
- 逐項對照Core architecture、Reasoner normalizer與action payload契約。
- 檢查M4a / M4b Gate 2A→Audio final reference→LLM Gate 2B順序無循環依賴。
- 僅修改文件；未執行或宣稱POC benchmark / Pi evidence Pass。

## 8. POC committed reply intake — 2026-08-18

Core Designer已確認LLM POC工作樹乾淨，`origin/llm`可解析且正好指向
`0cff62f942f2eec82fcc0b0f953a7cc4a2819e3a`。該commit相對原baseline
`4ac7ba3941077babf34c7c575003a65f5c541009`包含Gate 0 receipt、Initial Manifest、
milestone index、crosswalk及M0 fake lifecycle packet；因此「已commit並push、可作exact-SHA
intake」成立。

但015尚不能標記`Resolved`或歸檔。以下Blocking差異仍直接違反本response §6與Core
contract revision：

1. **POC承載的contract仍是舊revision。** POC路徑
   `docs/pm_handoff/DELIVERY-LLM-POC-M4B-CONTRACT-001.md`的SHA-256為
   `b2d7163da58f4e39cdaf1c99acfacebf4f433c38897a0004e5d92cbd4da4f217`，不等於Core
   revision的`d7d7adb84891803016b8656eb474f7a56bf39d5e416256192d003026c210585c`；前者仍只列
   `OUT-M4B-2026-001`，並保留舊P2/P3、cancel level、Gate 2與resource規則。
2. **Gate 2A / 2B與Test ID crosswalk未對齊。** POC crosswalk仍把Gate 2合併，M3只列
   P1～P8/P11、把P10與P12移到M4；Core contract要求Gate 2A執行P1～P8、P10A、P11、P12，
   Gate 2B才執行P9/P10B。POC M3並在combined gate前固定winner，與「2A僅provisional
   finalist、2B後才final winner」衝突。
3. **Gate 1 packet仍是規劃描述，不是§10要求的可執行packet。** Commit只有M0 dummy
   runner/schema；尚未提供Gate 1 frozen fixture catalog、P2/P3 expected results、validator
   version/checksum、Ubuntu x86/arm64 command/timeout/result schema與最多兩名finalist的固定
   decision packet。
4. **Gate 2 work package欄位不完整。** M3/M4文件尚缺逐包estimate、re-estimation trigger、
   可定位runner/command、P10A/P10B分流及Core五種result semantics；不得讓後續執行者自行
   補解產品契約。

最低複驗條件：POC先以Core 2026-08-17 revision取代舊contract副本，修正唯一crosswalk與
M3/M4 gate語意，補齊Gate 1可執行packet及Gate 2A/2B工作包，再以新的單一commit push至
`origin/llm`並通知完整40-character SHA。Core只複驗上述四項及其直接影響範圍；不要求在
015結案前執行Ubuntu benchmark、Pi Gate 2或產生candidate結果。
