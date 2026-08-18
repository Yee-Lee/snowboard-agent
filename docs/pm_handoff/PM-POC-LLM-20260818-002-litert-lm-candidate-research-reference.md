# LiteRT-LM / 模型候選與 Pi 5 評測研究參考

- Handoff ID : `PM-POC-LLM-20260818-002`
- Status : `Ready for PM`
- Owner : LLM POC Team
- Nature : 技術研究參考；不取代 Core contract、Gate ACK 或 POC 實測
- Reviewed POC repo : `poc_llm/snowboard-agent`
- Reviewed branch / HEAD : `llm` / `096cd728a277db584b23a5b0c91e3e7692b672fb`
- Related handoff : `PM-OUT-260817-015-llm-poc-contract-plan-review`、`PM-POC-LLM-20260817-001-readiness-correction`
- Research checked : 2026-08-18

## 結論

目前不需要先花時間廣泛搜尋 runtime、模型與量化組合。建議以 `LiteRT-LM v0.16.0 + Gemma4-E2B official .litertlm` 作主候選，`Qwen2.5-1.5B dynamic INT8` 作正式 fallback，`Qwen2.5-0.5B dynamic INT8` 作最低資源基線；所有其他組合只有在這三組出現明確 blocker 時才擴張。

官方已證明 Gemma4-E2B 可在 Raspberry Pi 5 CPU 執行，但公開數據來自 16GB 機型，不代表 4GB 與 Audio/TTS 共存已通過。POC 仍須依 Core contract 在 Pi 5 4GB、swap=0 上取得 exact-artifact evidence；本文件只提供可直接採用的研究起點，避免重複檢索與錯誤推論。

## 建議固定的第一輪 pairing

| Pairing ID | Runtime / artifact | 定位 | 第一輪設定 |
| :--- | :--- | :--- | :--- |
| LRT-G4E2B-MOBILE | LiteRT-LM `v0.16.0` + official Gemma4-E2B mobile `.litertlm` | 主候選 | CPU/XNNPACK、4 threads、embedded quantization default、`max_num_tokens=512`、MTP off、persistent process |
| LRT-Q25-15B-I8 | LiteRT-LM `v0.16.0` + Qwen2.5-1.5B dynamic INT8 | 正式 fallback | CPU/XNNPACK、4 threads、同一 prompt/output envelope |
| LRT-Q25-05B-I8 | LiteRT-LM `v0.16.0` + Qwen2.5-0.5B dynamic INT8 | resource floor | 只在通過相同 schema / 品質 gate 時才可升格，不因模型小而放寬契約 |

`Qwen3-0.6B` 可保留為後續候選，不建議僅因檔案約 328 ~ 586MB 就預設它最省 RAM。其公開 Android CPU benchmark 在 2048 / 4096 context 下曾出現約 2.7 ~ 2.9GB peak private footprint；模型檔大小不能代替 runtime memory evidence。

若 Gate 1 只允許最多兩個 Pi finalist，優先比較 Gemma4-E2B 與 Qwen2.5-1.5B；Qwen2.5-0.5B先作 harness/resource floor，不自動占用 finalist 名額。最終 candidate manifest仍須固定單一檔名、來源revision、SHA-256、license、chat template、quantization與config，不能只寫模型家族名稱。

## 已核對的官方資料

### Gemma4-E2B
官方 LiteRT-LM benchmark條件為 Raspberry Pi 5 16GB、CPU/XNNPACK、4 threads、context 2048、1024 prefill tokens、256 decode tokens、cache已初始化，且TTFT不含model load：

| Model file | Prefill | Decode | TTFT | Peak CPU memory |
| :--- | :--- | :--- | :--- | :--- |
| 2583MB | 133 tok/s | 7.6 ~ 8 tok/s | 7.8s | 1546MB |

`7.8s` 幾乎等於 `1024 / 133`，主要是1024-token prompt的prefill，不可直接推論短口語prompt也需等待7.8秒。以相同吞吐粗估，200 input tokens約需1.5秒prefill；這只是規劃值，產品仍須量p50/p95。

Gemma4-E2B是2.3B effective parameters，但含embedding約5.1B total parameters。Google列示的近似模型記憶體為BF16 11.4GB、SFP8 5.7GB、Q4_0 2.9GB、mobile 1.1GB、mobile text-only 0.84GB。LiteRT mobile artifact使用混合mobile quantization；不要把它誤標為單一INT4，也不要在第一輪自行重轉Q4。

### Qwen LiteRT-LM artifacts
下列數據來自Android，不是Pi 5數據，不得跨裝置直接排名：

| Model | Artifact size | CPU prefill | CPU decode | TTFT | Peak memory |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Qwen2.5-1.5B dynamic INT8 / S25 Ultra | 1598MB | 297.58 tok/s | 34.25 tok/s | 3.71s | 1997MB |
| Qwen2.5-0.5B dynamic INT8 / S24 Ultra | 521MB | 250.73 tok/s | 29.97 tok/s | 2.31s | 1363MB |
| Qwen3-0.6B mixed INT4 / two Android CPU examples | 474.61MiB | 231.15 ~ 576.59 tok/s | 8.33 ~ 12.90 tok/s | 0.52 ~ 1.23s | 約2890MB |

Qwen2.5-1.5B值得作fallback，但較小的檔案不保證Pi RSS低於Gemma4-E2B；只有同一Pi、同一runtime、同一token envelope與同一量測方法才能裁決。

## 建議的效能與記憶體調整順序

1. 先壓縮完整prompt：量測system instructions、schema、tool definitions、history及user text合計token；目標 `input <= 200`，不是只限制使用者語句。
2. 限制output：固定16 / 32 / 64 output token profiles。Pi官方Gemma decode約8 tok/s；每減少8 tokens約少1秒生成時間。
3. process常駐：model只載入一次；分開報cold READY與warm request。每輪重設conversation/history，不重載engine。
4. KV先用512：對 `input <= 200 + output <= 64/128` 已有餘裕；再以1024作壓力 / 相容對照，不先開2048 / 4096。
5. CPU threads比較4與3：4 threads作LLM-only baseline；3 threads用於Audio/TTS共存，依end-to-end p95而非LLM單體tok/s裁決。
6. delegate順序：XNNPACK是正式baseline；v0.16 Linux ARM64 experimental YNNPACK只作A/B，不預設較快。
7. MTP順序：先MTP off；確認artifact含drafter且4GB仍有headroom後才測on。它主要影響decode，效益依task而異且可能增加memory。
8. 量化順序：先使用artifact embedded default；`activation_data_type` 不是weight或KV quantization。自製轉換只在官方artifact確定無法達標後另提change request。

## 建議直接採用的 benchmark matrix

同一candidate至少固定以下input/output buckets，不以單一1024-token官方工作負載代表口語產品：

| Input tokens | Output tokens | 用途 |
| :--- | :--- | :--- |
| 64 | 16 / 32 | 短命令 / 最小口語turn |
| 128 | 16 / 32 | 一般單輪 |
| 200 | 32 / 64 | 產品目標上限 |
| 256 | 32 / 64 | 邊界 |
| 512 | 32 / 64 | 壓力 / history膨脹 |
| 1024 | 32 / 64 | 與官方prefill趨勢對照，不作日常口語baseline |

每筆保存：exact input/output token count、cold/warm、TTFT、time-to-valid- `LLMResponse`、generation tok/s、total latency、peak RSS/PSS、system `MemAvailable`、threads、temperature、throttling、swap、artifact/config/checksum。口語整合另量 `time-to-first-audio`；TTFT不能代替使用者真正聽到聲音的時間。

## 不應做的推論

- 不以模型檔案大小推論Pi active RAM。
- 不以Android tok/s推論Pi tok/s。
- 不把 `cache=disk/memory/no` 當作公開可切換的KV dtype。
- 不宣稱LiteRT-LM公開config可任意切 `fp16/int8 KV`；目前 `max_num_tokens` 控制KV容量，KV精度主要由artifact / 轉換決定。
- 不以LLM-only 4GB PASS取代Audio+LLM Gate 2B。
- 不因官方TTFT 7.8秒就判定口語不可用；先量實際完整prompt token數與time-to-first-audio。

## 官方參考來源

- LiteRT-LM overview、supported models與Pi Gemma4-E2B benchmark
- LiteRT-LM configuration keys
- LiteRT-LM releases
- Gemma4-E2B LiteRT-LM model card
- Gemma 4 parameter / quantization / memory overview
- Gemma 4 QAT mobile optimization
- Qwen2.5-1.5B LiteRT artifact與Android benchmark
- Qwen2.5-0.5B LiteRT artifact與Android benchmark
- Qwen3-0.6B LiteRT artifacts與Android examples

## POC團隊提交方式

本文件是研究參考，不要求POC另寫逐項finding response，也不要求文件預填或指向尚未形成的自身SHA。POC應把採用 / 拒絕的pairing、理由與實際benchmark條件併入既有Gate 1 / Gate 2 authoritative plan、candidate manifest與evidence；全部準備完成後依既有流程一次commit/push並通知PM收件。Core contract與Core Designer ACK仍是唯一執行授權來源。
