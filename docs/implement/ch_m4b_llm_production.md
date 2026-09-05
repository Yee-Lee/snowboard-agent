# M4B-MVA — 最小 Reasoner 與語音架構設計

狀態：Designer revision for review；USER產品方向已確認，Architecture / Reviewer /
Tester與量測profile尚未簽核。不是Development Ready、candidate freeze或Gate 3 PASS。
日期：2026-09-05。追蹤：[IR_dev_M4B_III](../reviews/IR_dev_M4B_III.md)、
[AR_impl_M4B_I](../reviews/AR_impl_M4B_I.md)、
[TR_spec_M4B_IV](../reviews/TR_spec_M4B_IV.md)。

本章取代R1的per-operation fresh Conversation、mandatory replacement pre-warm、
8-attempt/48-MiB recycle與model-generated canonical action envelope。
R1與其批准紀錄仍是不可改寫的歷史；可由Core commit
5d09f23及更早Git history查閱。已發布candidate不改寫。
本章是供審查的新設計，不授權在未解架構矛盾下開始耦合產品實作。

## 0. USER decisions and scope

- M4是最小可行架構（MVA）的離線語音主線；M4B完成必要Reasoner設計與行為驗證，
  M4C完成Audio/LLM/Display整合；ALPHA擴大品質與穩定性收斂；M5才加入實際tool。
- 同一產品session必須能承接上一句問題／澄清。未自行建立context management，
  不等於禁止runtime history。Session由SM從wake至IDLE擁有。
- 不做長期記憶、摘要、檢索、跨session恢复、pending task manager或完整tool reasoning loop。
- Reasoner擁有action/next_perceptions決策；LLM提供回答與結束意圖，SM負責時序與驗證。
- 初始身分為「雪板，你的語音小助理」。Capabilities只說當前可用能力；沒有影像輸入
  不得假裝看見環境。一般知識回答須基本正確，不以好聽但錯誤的句子通過。
- 短句一般對話目標2秒、初始上限3秒；完整恢復目標10秒。冷啟動無產品SLA，
  可評估background warm-up，但本輪不預先改main啟動拓樸。
- 上述是可修訂的工程／產品目標。未達標先確認有效性、分析瓶頸、提出優化或新門檻，
  不代表停止M4、放棄模型或取消計畫。每次修訂保留old target/result/reason/new target與USER決策。
- 32個本輪user tokens只是POC候選，不是已核准的總prompt limit。
- 既有五個未提交WIP可捨棄；不要求backup commit或移植其寫法。
- 自動測試驗程式契約／政策；語意品質用小型人工rubric。工程比較優先交POC，
  Core Developer做产品實作，Tester驗產品exact SHA。

## 1. Authority, evidence and exclusions

Gemma 4 E2B mobile、LiteRT-LM 0.16.0、Pi 5 4GB與既有target ABI/離線
artifact/license選擇維持。POC Attempt 006 P9/P10B machine FAIL及USER waiver不可改標。
POC winner profile是provenance，不再把其prompt、output、history、pre-warm與數字自動當M4B-MVA契約。
M4B-MVA須有獨立Core profile ID、prompt/schema/config digest與changed-surface inheritance。

本次核實區分：
1. source確實每generate create/close、每replacement驗完整hash及預熱；
2. 原8次有POC斜率推算理由，但沒有Core正常allocation與長期漏失的有效區分；
3. Reasoner呼叫LLM及SM驗證都符合架構，不以「不是Python自行理解」判違約；
4. Developer最新Pi 8.2秒／1.77–1.82GB只找到摘要，尚無可獨立核對的腳本與逐次樣本；
5. 15秒watchdog存在，但不構成端到端產品完成時間SLA。

不實作真實tool dispatch、MQTT、look/camera、voice wake、長篇回答、streaming或
二次LLM推論。M4不以模型tool品質阻擋voice-only；既有ToolRegistry與generic validator
相容性由portable regression保護，真實tool語意在M5評估。未來look屬perception能力，
「你能看嗎」與「幫我看看」的能力詢問／觀察要求須分開，M4不啟動camera。

## 2. Minimum Reasoner policy

建議model semantic result固定兩個欄位，constrained JSON，暫不引入文字控制marker：

    {"text":"我是雪板，你的語音小助理。","end":false}
    {"text":"","end":true}

Exact fields；end必須bool；end=false要求nonblank text；end=true只允許empty text。
Model不輸出action_kind/action_payload/next_perceptions或tool arguments。
這是Designer首選編碼，POC依同一格式量測；變更須versioned修訂，不任意換成full envelope。
USER的範例是產品事實／development案例，不是exact-literal驗收答案。

| Injected condition | Reasoner disposition | Product result |
| :--- | :--- | :--- |
| 有效text/end=false且speak/listen可用 | speak；next_perceptions由Reasoner固定listen | 單一LLMResponse(speak, {text}, (listen,)) |
| 有效end=true | rest；next_perceptions空 | 單一LLMResponse(rest, {}, ()) |
| 模型建議不存在的key、tool或next_perceptions | 拒絕模型結果 | 依§4區分未改state與dirty Conversation |
| speak/listen不可用 | 不執行無法延續的speak | rest；不詢問core資源或猜測失效原因 |
| 過長input、無有效ASR文字、inference前拒絕且session仍完整 | 固定簡短說明／P5；listen | 不宣稱正常知識回答PASS |
| runtime無法證明context完整 | 結束session | rest→IDLE；需新wake，不能處理失去前文的「對」 |

MVA end路徑沿用empty rest，不新增「先farewell speak再自動rest」或extra LLM turn。
正常end與context loss均以既有Display回IDLE表達結束，不假裝成功回答。
若要新增有聲收尾，須另定consumer及action契約，不偷偷用empty next_perceptions結束speak。
Refusal若是合法短回答可走speak/listen；是否回答正確由人工rubric判定。

固定產品facts（姓名／角色／可用能力）、簡短繁中風格與輸出契約在session建立時傳入。
每turn只送新perception內容；不重送全transcript、不要求模型產生固定Core控制語法。
Reasoner不得以字串關鍵字分類「你是誰」等問法；LLM理解自然語言。
M4 profile只啟用listen/speak/rest；一般能力介面保留未來擴充，但不提前建立read/look政策。
若觀察到當前capability與session開始時不同，視composition invariant失效，結束session，
不沿用錯誤能力描述。RM startup-static能力原則不變。

### Validation ownership

| Layer | Responsibility | Failure |
| :--- | :--- | :--- |
| child | model token/output bound、strict parse、semantic result shape | typed operation error；dirty history必須丟棄 |
| adapter | frame size、version、request/session identity、terminal、metrics、single flight | protocol/identity failure destructive recovery |
| Reasoner | product policy、capabilities、canonical envelope、Ch9 validator | bounded P5或session end；無法收斂才ERROR |
| SM | Fact identity、合法action/payload/next_perceptions、task完成與派發 | 既有contract violation→ERROR |

SM檢查不是可任意移除的重複驗證。人工語意PASS也不能替代任一程式契約。

## 3. Session API and ownership

SM仍為session唯一owner；Reasoner只是受控participant。新增窄介面建議如下：

    class ReasonerSessionControl(Protocol):
        async def begin_session(self, session_id: str) -> None: ...
        async def end_session(self, session_id: str, reason: str) -> None: ...

LLM adapter在既有start/stop/abort/force_abort之外提供：

    async def open_session(self, session_id: str, facts: SessionFacts) -> None: ...
    async def generate(self, session_id: str, turn_id: int,
                       value: TurnInput) -> SemanticGeneration: ...
    async def close_session(self, session_id: str, reason: str) -> None: ...

SessionFacts = name/role/locale/available_perceptions/available_actions；
TurnInput = 當前perceptions(kind/status/text)，M4只允许listen。
SemanticGeneration = semantic(text/end) + diagnostics；session identity留在控制層，
不render進model prompt、不log。Public LLMResponse形狀與每turn一個Fact不變。
所有API均single flight；沒有parallel Conversation。

SM在WAKE分配ID後、PERCEPTION前以既有非阻塞completion-notice模式完成begin_session。
不得await blocking native operation卡住SM inbox；Interrupt/Shutdown能取消未完成open。
Reasoner begin只登記ownership；lazy open可在第一個reason呼叫建立Conversation，
但該成本必須算入第一筆請求，不能以READY排除。一session只開一次。

正常rest、Interrupt、Error、Shutdown四條路徑，在in-flight收斂後、清SM session欄位／
resume wake之前呼叫end_session並證明close完成；未曾進THINK也須清Reasoner session登記。
CONTROL pending也是收斂追蹤項，不能僅清reason task。
相同session end可重複no-op；wrong nonempty session拒絕，不得關閉後來的session。
先close舊Conversation才容許新session。遲到open/result/close ACK不准更動新session。

### Implementation skeleton (after architecture approval)

    begin_session(sid):
        require no active session/control
        remember sid; conversation_open = False

    reason(sid, tid, cid, perceptions, pending):
        require sid == current_sid
        if not conversation_open:
            await llm.open_session(sid, product_facts)
        result = await llm.generate(sid, tid, current_turn_input)
        response = apply_mva_policy(result, capability_of)
        publish exactly one LLMResponse with sid/tid/cid

    finish_convergence(trigger):
        await in_flight_completion_and_cancel_proof()
        await reasoner.end_session(sid, trigger)
        clear_session_tracking()
        follow_existing_idle_or_shutdown_path()

新增檔案/symbol以Ch4 manager/ports/notices、Reasoner、llm.py、prompt_builder.py、
llm_child_protocol.py及LiteRT adapter/worker為直接修改面。main只注入窄port，
不把Reasoner或SM提升為runtime owner。

## 4. Conversation state, failure and capacity

Child state = READY_NO_SESSION / SESSION_IDLE / GENERATING / FATAL。
Session正常成功後保留Conversation；Engine跨session常駐。
Request-local references/thread要清理，不能把Conversation也當request-local清掉。
Session close必須丟history/KV/reference；這不等於Engine allocator一定歸還全部PSS。

| Condition | Conversation / terminal | Parent / Reasoner |
| :--- | :--- | :--- |
| 成功generate | 保留、SESSION_IDLE；RESULT | policy→一個LLMResponse |
| input超界且尚未send_message | 原Conversation不變；INPUT_TOO_LARGE/session retained | 固定短回覆+listen；不計正常quality PASS |
| timeout/cancel、native error、invalid model output | join worker；close Conversation；SESSION_ENDED | 若仍可publish則rest；外部cancel不publish |
| close/join無法證明、protocol desync、crash | FATAL；不假稱session clean | Ch6 Level2→RM recovery；清產品session |
| context capacity將滿 | 不開始新inference；close；CONTEXT_LIMIT/session ended | rest→IDLE；新wake才重新對話 |
| validated result後Reasoner仍拒絕 | close該Conversation，丟棄result | rest；不保留被拒答案當成已回答 |

P5 apology+listen只適用仍能證明context未改變的request failure。fallback不代表模型已看過該句；
fallback不得包含需要未來理解的確認提問。runtime state已破壞時不靜默建立新Conversation續同session。
Error/Shutdown不需要有聲提示。任何dirty state都不得以「thread已退出」取代typed cleanup證據。

容量分成user-new tokens、完整rendered/incremental input、output reserve、Engine total KV。
Admission須以exact tokenizer驗證累積容量+本次input+最大output reserve，避免先開始才耗盡。
POC驗token_count/render API在selected runtime的真實語意；未驗清前不可宣稱capacity protection。
不做摘要／sliding window／自動重送history。數值由§7 profile freeze固定，未凍結不得正式驗收。

## 5. Readiness, recovery and memory

初次startup authenticate→Engine load→依measured profile optional prewarm→READY_NO_SESSION。
同次開機replacement預設不做disposable inference prewarm；冷啟動是否預熱先以§11 POC比較。
任何保留prewarm必須證明下一筆真實請求收益，且不得污染第一個session。
不因「cold startup無產品SLA」移除bounded operational watchdog；watchdog是清理掛死，
不是使用者等待承諾。Background warm-up只是允許的後續方案，不在本draft加入新supervisor。

移除attempt-count、post-prewarm 48MiB與固定三generation成功條件。
主要planned trigger是MemAvailable低於measured profile的capacity reserve；owner PSS作歸因，
沒有穩態證據不定2GB等上限。取樣仍用完整unique-PID owner PSS及MemAvailable，
資料缺失不沿用舊sample，不當正常PASS；startup缺能力為preflight failure。

在open/generate admission前及terminal後取樣；不在active inference中planned recycle。
若low memory但session存在：停止後續admission，讓當前inference完成清理，將其result
discard並回SESSION_ENDED，close session；Reasoner rest。不得先說出需要回答的問題再悄悄丟history。
等SM完成session close後由同key RecoveryTicket排程一次replacement。
Replacement仍低於reserve時不無限recycle：barrier不開、保存capacity failure並依既有RM fatal處置。
真正crash/cancel失敗等fault recovery與planned capacity maintenance分開記錄。

恢復目標10秒從RM接受recovery至replacement ready/barrier釋放，包含舊owner清理、
身份驗證、load及任何選定prewarm。保留分項timing，不把rehash藏到計時之外。
Engineering timeout與目標分欄；超目標但在watchdog內完成是target miss，不必自動kill。
watchdog超時/cleanup失敗仍走既有Level3。門檻修訂不改寫先前result。

### Same-install trust boundary

首次install/preflight/initial trust完整hash model、runtime、config並驗ABI；hash I/O在
executor或既有非阻塞準備流程，不阻塞SM event loop。Replacement不得每次完整rehash大model。
首選：root/受信任部署owner管理、service無寫入權的sealed install generation，
受信任operator保證運行期間不替換其內容；parent保留validated manifest與generation identity。
每次replacement重驗path無symlink、owner/mode、device/inode/size/mtime/ctime及manifest identity；
任一變動撤銷信任、fail closed，不在10秒critical path靜默重新建立信任。
Metadata比對本身不是digest proof；此快路徑依賴明確不可變部署邊界。
無法建立該邊界的target不可使用快路徑，回Designer採等價attestation，不直接跳過驗證。
本項不授權installer更改system packages、mount或部署服務，也不建立systemd/update功能。

## 6. Performance and quality endpoints

| Layer | Start → end | Claim |
| :--- | :--- | :--- |
| runtime POC | send/generation入口→first internal token／complete semantic output | TTFT與TTC；須含或另列Conversation create；不可冒稱audible latency |
| Core M4B | adapter接受本輪input（含必要session open/recovery等待）→Reasoner可交付LLMResponse | caller-visible TTC；IPC/render/validation計入 |
| M4 voice | 使用者最後一段語音結束→第一個有內容回答的audible onset | 目標2秒／初始上限3秒；不以提示音或固定請稍候計入 |
| engineering split | endpoint confirmed、ASR done、LLM begin/end、TTS first PCM、playback onset | bottleneck attribution，不能替代主指標 |
| recovery | RM接受recovery→barrier解除 | 完整10秒目標 |

ASR transcribe(stream)呼叫不等於使用者說完。固定WAV須提供最後speech-sample annotation；
實機用loopback/外部錄音的同一timebase觀察speech end與speaker onset，或經驗證的等價方法。
第一個PCM write不是自動等於audible onset；量測方法須列已知誤差。
輸入音長與user tokens分開，output採短句；複雜度以案例類型定義，不以32 tokens代理。
長篇／複雜問題明確請求縮短或拆分；不偷偷截斷。出界案例測可預期處置，不冒稱正常SLA達成。

自動：schema、capability policy、next_perceptions、timing、identity、cancel、cleanup。
人工：身分一致、知識基本正確、無虛構能力、追問連貫、簡短易懂。
不以keyword、exact string、另一LLM judge或schema PASS取代人工語意。
人工記run/case/operator/time、各rubric Pass/Fail與sanitized reason；獨立保留性能結果。
快但錯、fallback、提前截斷、錯誤結束不計正常回答PASS。
「100% coverage」只宣稱已列需求有驗證方法，不宣稱模型所有語意皆正確。

## 7. Profile and unresolved measurement register

新Core profile建議ID：core-m4b-mva-001；尚未建立production lock。
保持原model/runtime/ABI/license身份；改動renderer/output/session/profile單独記Core delta。
舊POC config與原digest保留為provenance，不能以同digest聲稱新profile。

| Field / decision | Draft disposition | Required before product freeze |
| :--- | :--- | :--- |
| semantic output | exact text/end兩欄 | same-schema POC correctness/TTC |
| user-new tokens | 32候選 | 語音長度與代表性繁中案例可容納性 |
| output tokens / Engine KV | 128/1024只作原baseline參考 | 新短句與多turn capacity量測、明確reserve |
| prewarm initial/replacement | 初次待比較；same-boot預設none | following-request收益與成本 |
| capacity reserve / stable window | 未定；不沿用768/48/64 | combined memory樣本與安全headroom |
| startup / generation / control watchdog | 保持bounded，值待profile；舊45/15/2只作參考 | 包含open/close與cleanup的timeout table |
| response/recovery objectives | 2秒目標、3秒上限、10秒完整recovery | 原值與每次miss保留；USER可修訂 |
| supported case envelope | 短句身分／知識／能力／追問／結束 | 固定catalog、input/output limits、人工rubric |

以Designer逐項response收斂profile；不能由Developer在YAML猜值。
新config移除recycle_max_inference_attempts/recycle_owner_pss_delta_mib；
memory reserve与timeouts由新profile提供，runtime path selector仍由Ch10管理。
分離recovery objective與operational watchdog；缺少required profile欄位在spawn前拒絕。
schema版本與完整bytes/digest待凍結，禁止sample-only defaults形成正式PASS。

## 8. Offline packaging and unchanged target ABI

繼承已Resolved的IR_dev_M4B_I／TR_spec_M4B_II target ABI，不重新選型：
Debian13 aarch64；root-owned non-symlink /usr/bin/python3.13；CPython3.13.5、
SOABI cpython-313-aarch64-linux-gnu、MULTIARCH aarch64-linux-gnu、
64-bit little-endian、empty abiflags；stdlib /usr/lib/python3.13及其lib-dynload。
五個python3.13/libpython3.13 target packages須installed、同一3.13.5-* revision。
Per-run ABI attestation包含sorted package tuples、base SHA、sys.version、SOABI/MULTIARCH、
stdlib roots/glibc；install/preflight/acceptance一致，drift撤銷既有attestation。

產品仍用--copies --without-pip isolated venv；stdlib/platform libraries屬target，
14-file LiteRT payload屬tracked runtime closure，不把target CPython bytes收進該manifest。
Install staging驗完atomic rename，existing output/symlink拒絕；無apt/pip download/網路fallback。
Native runtime只能在child lazy import；parent不得import。禁止user/system third-party site、
PYTHONPATH/PYTHONHOME/LD_PRELOAD escape。Model/config/runtime仍full-digest建立初始trust，
same-install replacement依§5；no-follow、license/notices與offline evidence維持。
原manifest內容如因新增product config identity須修訂，保留原POC lineage而非改model digest。

## 9. Minimum regression and affected files

| Risk / injected condition | Expected outcome / minimum assertions |
| :--- | :--- |
| two turns same session | 一個Conversation；第二輪能回答第一輪追問（real人工）；mock只證明reuse |
| next session | previous close ACK在new open前；old canary/context不進新session；no retained refs |
| interrupt during open/generate/close | 無late LLMResponse；control/task收斂；session清除；失敗走Level2 |
| normal end / no-THINK end / Shutdown | 一次有效close或idempotent no-op；清登記；Shutdown不rebuild |
| end=false/text valid | Reasoner產speak/listen，model未提供next_perceptions |
| end=true或unavailable capability | rest/empty next；不派發tool，不呼叫不存在perception |
| oversized input / capacity full | 前者無inference且state retained；後者close/rest，不暗中reset續對話 |
| invalid model JSON / timeout / cancel | dirty Conversation discard；typed joined terminal；新session健康；zero thread warning |
| wrong session/request/duplicate terminal | fail closed；不交付result；原owner cleanup，無cross-session mutation |
| normal allocation below capacity reserve | 不因8次或48MiB排程；完整samples仍保留 |
| low capacity / replacement仍不足 | 一次回收、session結束、closed barrier；不recycle loop／fake PASS |
| installed identity mutation | spawn前失敗；zero inference；不以stat-only當digest |
| no-next-request recovery failure | main RM fatal monitor仍結束；不存在unobserved failure |
| output/cancel/privacy | logs/evidence無private text/prompt/audio/tool args；人工紀錄不copy raw answers |

Source直接面：reasoner/prompt_builder/llm/llm_child_protocol；LiteRT worker/adapter/lock/resource；
SM manager/ports/notices/convergence；config models/loader/factory与main窄port wiring。
Tests/工具直接面：M4B CFG/LOCK/IPC/RDY/GEN/OUT/P5/CAN/REC/HIST/PRIV/RES/PKG/INH、
fake child、m4b_target_cases、m4b_target_metrics、candidate_gate、m4b_inheritance、
gate3-product-catalog。OFF維持既有網路邊界並驗新composition。
不重開M4A-only target rows；同SHA重驗真正受新session/composition影響的Audio/resource/privacy。
Candidate卡不能仍固定20 Conversations／5 create-close／三generation或prewarm digest。
20 sessions與session內multi-turn分開計數；自然capacity soak不硬湊兩次重啟，
recovery另用受控注入驗。歷史r14公式/vector保持；新Core capacity/stability判準另version，
不能把改判準的結果回填舊r14。

## 10. Review sequencing and handoff

跨團隊名稱M4B-MVA，基線M4B-MVA-001；不再使用草稿別名R2。
唯一順序與release條件見[M4B-MVA gate](../milestones/M4B_MVA.md)：
Architect修訂→Reviewer審arch/design/POC計畫→Designer定版→交付POC、gate Open→
POC回交→Designer審核通過、gate解除→Developer／Tester進場。
不允許Developer／Tester因部分契約穩定提前寫spec或實作。
進場後仍先完成test-spec coverage，再開始產品實作；candidate commit需USER確認。
Reviewer審的是包含本章/protocol/跨章delta與POC計畫的一個完整package，
數值由POC產生再由Designer採用，不把「設計定版」誤解為先猜定量測結果。

## 11. POC work package

[REQUEST-LLM-POC-M4B-MVA-MEASURE-001](../outsource/deliveries/REQUEST-LLM-POC-M4B-MVA-MEASURE-001.md)
屬M4B-MVA-001；沿用既有LLM POC團隊/repository，必要時協調Audio。
工作包尚未完成Reviewer審查／Designer定版，未交付。
正式交付後依定版範圍執行，只有Designer審核並明確解除M4B-MVA-POC才進場；
POC結果不取代Core產品exact-SHA驗收。
