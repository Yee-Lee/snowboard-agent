# 核心團隊 M4b LLM 任務

對象：核心產品團隊與主線產品開發團隊  
Owner：內部 Designer  
狀態：Ready for PM delivery；不代表 PM 已交付  

## 結論

M4b 在 M4a Audio 與 LLM POC Accepted 後開始，交付固定 LiteRT-LM runtime / model baseline 的正式產品整合。POC wrapper 只作產品化來源，不直接合併主線。

目前活動產品文件仍使用單一 M4，且缺少 `docs/model_spec.md` 與 `docs/protocol.md` ；這些缺口必須在 M4b 進場前完成。

## CORE-LLM-01：固定 M4a / M4b 邊界

* M4a：VAD、ASR、TTS、Audio HAL 與語音品質。
* M4b：LLM runtime、model、persistent child、輸出契約，以及與 M4a 的整合 regression。
* M4b 只能引用活動產品 repo 明確 Accepted 的 M4a 完整 SHA；歷史典範不算現行基線。
* 更新 `docs/milestone.md` 、progress 與 dashboard，不再以單一 M4 混合兩個 gate。

驗收：M4b entry 明確列出 accepted M4a SHA、POC handoff、owner、Test ID 與阻擋項目。

## CORE-LLM-02：固定 Reasoner 與 LLM 契約

* 固定 PromptBuilder 輸入、 `LLMResponse` 、normalizer、payload validator 與 P5 fallback 邊界。
* 模型只產生 `speak` / `tool` / `rest` intent，不執行 tool handler。
* Reasoner 只取得受限的 perception / action capability view，不取得 Resource Manager。
* 每次 generate 建立新的 single-turn conversation；model 可常駐，但 hidden history / KV state 不跨 operation。
* Prompt、perception text、raw output 與 tool payload 不進一般 log。

驗收：Ch 2b / 4 / 5 / 9 / 11 與 test spec 對合合法輸出、違約、P5、capability 及 history isolation 使用同一語意。

## CORE-LLM-03：固定 model 與 child protocol

* 建立 `docs/model_spec.md` ，記錄唯一 runtime、model artifact、quantization、checksum、license 與資源 budget。
* 固定 context / output token 上限、temperature、top-p、threads、startup / generate / cancel timeout。
* 建立 `docs/protocol.md` ，至少定義 version、READY、GENERATE、RESULT、CANCEL、ERROR、SHUTDOWN、request ID 與 exit proof。
* Strict config 只接受核准 driver / model path / limits；不得 runtime download、浮動版本或隱式 fallback 到其他模型。

驗收：文件、config、factory、protocol schema 與 POC winner manifest 完全一致。

## CORE-LLM-04：產品化 POC winner

* 從 POC Accepted SHA 抽取 reference client / server、manifest、fixtures 與 fault-injection harness，再適配產品目錄。
* 實作 lazy factory、 `backend.cognition.reasoner.llm` resource、READY gate、Reasoner wiring 與 reverse stop。
* 一次只允許一個 active generation；stale / duplicate result 不得污染目前 request。
* Cancel 失敗時依期限 terminate、kill、waitpid；無 exit proof 不得視為完成。
* Child crash 或 destructive cleanup 後依產品 recovery barrier rebuild，舊 result 不得進入新 generation。

驗收：unit / integration tests 覆蓋 READY、generate、cancel、force-abort、crash、rebuild、shutdown 與 orphan=0。

## CORE-LLM-05：完成 M4b 驗收

* Pi 5 驗證 cold READY、hot p50 / p95、tokens/s、RSS、disk、CPU 與 thermal。
* 驗證合法 action、P5 fallback、capability 限制、history isolation 與 log hygiene。
* 與 M4a models 同時常駐，完成至少 20 個固定語音 sessions。
* LLM failure 不重新定義 Audio 結果，也不繞過既有 State Manager / recovery 契約。

驗收：Tester 依產品 delivery exact SHA 確認 Pi evidence 與完整 regression；團隊自驗不等於 Accepted。

## M4b 不包含

* VAD、ASR、TTS 或 Audio model 重新選型。
* 雲端 LLM、RAG、跨 session 記憶、Vision 或 wake daemon。
* 讓模型直接執行 Python / tool handler。
* 未經 review 的 runtime、model、prompt 或 output schema 變更。

## 主線交付要求

主線團隊須在產品 repo 的 `docs/reviews/outsource/` 提交 delivery manifest、POC handoff 引用、架構 / model / protocol 變更聲明、tests / Pi evidence 與完整 commit SHA。
