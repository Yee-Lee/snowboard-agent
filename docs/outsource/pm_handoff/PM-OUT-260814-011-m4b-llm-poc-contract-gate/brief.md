# M4b LLM POC Contract / 002 結案移交要求

- **Handoff ID** : `PM-OUT-260814-011-m4b-llm-poc-contract-gate`
- **Status** : `Ready for PM`
- **Finding ID** : `OUT-M4B-2026-001`
- **Related handoff** : `PM-OUT-260805-002-m3-m4-poc-planning`
- **Related Audio handoff** : `PM-OUT-260814-010-m4a-audio-poc-contract-gate`
- **Reviewed Core candidate** : branch `dev_agent_m3` , HEAD `fb144bf4b8f530a98189feb5467546c398e96a41`

## 結論

PM-OUT-260805-002-m3-m4-poc-planning 已要求Core規劃M4b並等待Accepted LLM POC input，但目前沒有Core正式發給LLM POC Team的contract、POC receipt、team repo、manifest或evidence。此缺口不阻擋目前M3或獨立的M4a準備，但會阻擋LLM POC正式啟動、M4b entry與最終M4 acceptance。

Core應提交可由PM轉交LLM POC Team的M4b contract，並補交002指定的正式response。完成exact-SHA intake且確認002各範圍已有後續owner後，002應移入archive，不等待Audio / LLM POC全部執行完成。

## 必做修訂

### `OUT-M4B-2026-001` —— Blocking for M4b POC authorization / Non-blocking for current M3

- Core Designer建立PM-ready的LLM POC contract，明列目標、範圍、核准runtime / model / quantization候選、淘汰條件、prompt與artifact固定方式、license / checksum、品質與資源門檻、Ubuntu初篩、Pi 5最終gate、thermal及與M4a共同常駐要求。
- 定義可觀察的persistent-child契約驗證：READY、generate / result、timeout、cooperative cancel、terminate / kill / waitpid、recovery barrier、history isolation、bad output / no-go與必要evidence。
- 明確區分POC與產品化：POC提交reference wrapper、harness、candidate manifest與evidence；`model_spec.md`、`protocol.md`、Resource Manager / Reasoner整合、產品tests與M4b delivery仍由Core負責。
- 固定跨團隊流程：Core contract owner → PM正式轉交LLM POC Team → POC receipt / repo / manifest → POC exact-SHA delivery → Core review / ACK → 後續M4b OUT-TASK。
- Contract交付前，外層LLM指引只能視為 `Ready for PM` 的內部準備，不得把指引、口頭結果或未提交候選視為已授權POC或Accepted input。

## 002 結案與責任移交

- Core提交 `docs/outsource/responses/OUT-FB-2026-002-R1.md` ，逐項回應 `OUT-POC-2026-001 ~ 007` ，不得只以milestone摘要取代正式response。
- Response明列002後續責任已移交：Display由既有Display ACK / 後續M3 handoff承接；Audio M4a contract由 `PM-OUT-260814-010` 承接；LLM M4b contract與啟動由本011承接。
- PM拉回Core exact SHA、完成內部intake並確認上述owner / 路徑後，將002標示 `Intake completed` 並移入 `outsource/handoffs/archive/` 。002不應繼續等待POC執行、winner選定或M4b產品化完成。

## 驗收方式

- Core在單一候選commit提交：
  - Contract : `docs/outsource/deliveries/DELIVERY-LLM-POC-M4B-CONTRACT-001.md`
  - 本finding response : `docs/outsource/responses/OUT-M4B-2026-001.md`
  - 002正式response : `docs/outsource/responses/OUT-FB-2026-002-R1.md`
  - 同步修訂 `docs/milestones/M4.md` 、 `docs/reviews/milestone_progress.md` 及必要的handoff index，明列contract owner、PM relay、POC receipt / return、Core ACK與M4b entry gate。
- 每份response須列comparison baseline、完整candidate SHA、architecture-change聲明、逐項修改定位、未決產品門檻需要User / PM決定的項目。

## PM動作

PM只交付本 `brief.md` 給Core Team，不交付同目錄的 `review_notes.md` 。收到Core完整SHA後先完成011與002的intake / 狀態對帳；再把已提交的LLM contract正式轉交LLM POC Team並取得receipt。Agent不直接寄送、上傳或跨repo代寫。
