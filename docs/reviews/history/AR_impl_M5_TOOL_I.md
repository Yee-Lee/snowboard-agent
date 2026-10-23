---
requestor: Designer
owner: Architect
status: Resolved
---

# AR_impl_M5_TOOL_I — 有限工具意圖與派發回饋

## 1. 請求與來源

USER 已確認 M5.tool（真實 Gemma＋mock）→ M5 MQTT（發送及外部 read）→ M6
Camera＋YOLO＋結果整理→LLM；Wake 延後，VLM 描述另列 POC，read／Look 交錯不納本輪。
產品權威見 [M5](../../milestones/M5.md)、[M6](../../milestones/M6.md)，具體方案見
[ch_m5_tool](../../implement/ch_m5_tool.md)。既有 active review 屬 M4B，無本 scope 的重複 review。

價值：不改記憶架構，以兩條有限路由驗證真實模型工具能力。此單只處理下列實際契約
矛盾，不新增例行簽核。請 Architect 將 §3 可採用文字落入 arch.md，回覆具體差異後交
Tester；不重開 ALPHA、不等待 VLM POC、不要求其他角色互簽。

## 2. Findings（同一 scope 合併提出）

| ID／等級 | 依據與可重現差異 | 產品影響 | 首選修正／最低驗收 |
| :--- | :--- | :--- | :--- |
| B1／Blocking | arch §2.7 的 M4 模型只決定 text/end；新 profile 需 tool/look 意圖。現行 product projector 拒絕 look，child RESULT 只含 text/end | 無法實作真實模型選工具及 Look 下一輪輸入 | 明定 profile-specific 有限語意，Core 保留 action/route 決策；真模型選能力與 mock Look 接續可驗 |
| B2／Blocking | arch §2.8、§4.6 KEEP_NEXT 在 primary terminal 後直接 PERCEPTION；目前只有 primary／post-action-rest，沒有 tool 後 Speak feedback | 實作「已送出」會繞過 SM 或偽造第二個 LLMResponse，取消與播音歸屬不明 | 新增有限 tool_feedback ACTION phase，一次一個 record；測派發後回饋及中斷後無遲到播音 |
| A1／Advisory | arch §8.3 把「Tool 結果回饋後再次推論」泛列完整 reasoning loop；§2.6／§5.1 已有 Look/read 下一輪，但未說明此次邊界 | 可能把普通觀察／外部訊息接續錯當新 query 系統，或誤把 handler return 當外部 response | 明確保留 fire-and-forget、read 外部輸入與 Look perception，不新增通用 loop；M5 發送／接收分開驗證 |

以上不質疑原 M4 交付；只影響新 profile。跨 Conversation 列既有 replacement 的錯誤處理，
無需另開研究。Wake scope 以 milestone 為準，架構可保留延後的介面而不強迫產品啟用。

## 3. 建議可直接採用的架構文字

### §2.7 — 在 M4 邊界後追加「M5 有限能力 profile」

M4 profile 的 text/end 邊界保持原義。M5.tool 起的有限能力 profile 允許模型輸出
speak/end、已註冊命令工具意圖與 Look 意圖。模型不輸出 Core action envelope、
Session／Turn identity 或任意 perception 清單。Reasoner 驗證後映射：tool 為
`tool + KEEP_NEXT + listen`；look 為 application-owned 準備語
`speak + KEEP_NEXT + look`；一般回答與結束沿用既有 speak/rest route。
每產品 turn 至多一次模型推論，SDK 不自動執行 handler。

Look 結果在下一個 look-only turn 成為模型輸入，使用原 Conversation 的前文；不等待
新的語音，不重送完整 history，不新增對話記憶儲存。無可用結果優先 application fallback。
若 Conversation 已替換，放棄舊觀察與原問題接續，請使用者重述，不將舊結果 replay 到
空白 Conversation。M5.tool 不處理 read／Look 交錯。

### §2.8 與 §4.6 — Tool 派發後的有限 feedback phase

Fire-and-forget 的 `ActionCompleted(tool)` 只表示派發階段結果，不表示外部業務完成。
支援固定派發回饋的 profile，在 tool primary Fact＋task done join 後，由 SM 留在 ACTION
啟動唯一 `tool_feedback` Speak phase。Feedback 由應用程式根據派發 status 決定，
不產生第二個 LLMResponse，不再呼叫模型，也不由 Tool 直接操作 Audio。

Primary 與 feedback record 不並存；feedback 使用自己的 correlation，完成 join 後才依
KEEP_NEXT 進 listen。Interrupt／shutdown／system failure 對當前 phase 使用既有收斂；
遲到 completion 不得啟動新 phase。普通 TTS 可翻譯錯誤沿用既有 action failure policy。
此能力不是任意 action list，M5.tool 不產生 tool + END_SESSION。

SM 可將上一輪的派發 status 作為單一、payload-free 私有提示傳入下一次正常 cognition，
使模型知道固定回饋的事實；同 generation 使用，消費或結束／replacement 即清除。
此提示不承載外部 response，不增加模型呼叫或跨 Session persistence。

Architect 同步修訂 §4.5 的 ACTION 轉移表：支援此 profile 的 `tool + KEEP_NEXT` primary
完成後先進 `ACTION tool_feedback`，feedback `ActionCompleted(speak)` 完成後才進
PERCEPTION；不把兩個 phase 視為兩次狀態轉移。§4.8 亦須說明 primary tool status
可選固定回饋語句並保存單輪 `last_dispatch_status`，且不取代原有
`default_perceptions` 對 continuing action error 的處理。Feedback 的可翻譯失敗沿用
既有 action error 路徑，不能回頭重送 tool。

### §2.6、§5.1 與 §8.3 — 觀察與外部結果的區別

Look worker 管理 Camera 及 Vision adapter，結果整理後作為 perception facts 輸入 Reasoner。
模型選 Look 不等於新增 action=look。M6 先用 YOLO；替代性的 VLM 描述 pipeline 只屬獨立
研究，待採用後才改 production backend／資源契約。

MQTT 外部 response 或主動通知由 adaptor 驗證後進 external_message buffer，再由 read
消費；IDLE 可開新 Session，活躍 Session 依 pending/read window 規則。不得把外部結果
回寫已完成的 tool action，也不得把工具派發成功當作外部成功。
既有 read／Look 下一輪輸入不屬 §8.3 未定的通用 query、任意多工具 reasoning loop 或
跨 Session task restoration；那些能力繼續排除。

### §2.8 streaming 與 §7 部署補充

新 profile 僅將已確認 speak/end 的文字送到 streaming Speak；tool/look 意圖不得成為
播音片段，tool 派發必須等待完整語意驗證。Profile 的具體 parser/schema 屬 implement。
Wake 是可延後能力；目前 M5.tool／M5／M6 不要求 daemon 或麥克風交接產品功能，BETA 前
是否加入另作產品決策。不得以架構描述存在推定其為當前 gate。

## 4. Owner 回覆位置

Architect 已採用 B1、B2、A1 的有限契約，修改 `arch.md` §2.6、§2.7、§2.8、
§4.5、§4.6、§4.8、§5.1、§7.2、§8.3：

- B1：M4 text/end 語意保持；M5 有限 profile 由模型選 tool / Look，Reasoner 驗證後映射
  Core route。Look 在原 Conversation 的下一個 look-only turn 接續；replacement 放棄舊觀察。
- B2：`tool + KEEP_NEXT` 的 primary 完成後，SM 留在 ACTION 執行唯一 Speak
  `tool_feedback` phase，獨立 correlation、Fact / task done join 及既有取消／錯誤收斂；
  派發 status 只作單輪私有提示，不當成外部業務結果。
- A1：MQTT 外部 response / 通知經 buffer / read；Look 為 perception，M6 先採 YOLO；
  通用 query、任意多工具 loop、跨 Session 記憶仍未納入。Wake 不作當前 gate。

未解 blocking 項目：無。M4 既有行為、Session / Conversation ownership、每 turn 一次
`LLMResponse`、fire-and-forget 與原有收斂分界均保留。Designer 已核對上述修改與
M5.tool 設計，B1、B2、A1 均已收斂；此單結案，Tester 承接 M5.tool Test Spec，
不新增一般 review 或 ACK。
