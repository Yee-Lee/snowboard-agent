# Snowboard 實作里程碑 ( milestone.md )

本文件回答 WHEN + VERIFY：定義實作順序、每階段範圍、相依、排除項目與可重複驗收。架構原則以 `arch.md` 為準；Python 契約與演算法以 `implement.md` 及 `implement/` 各定稿章節為準。Display 內容 profile 見 `display_spec.md`；runtime 模型選型 gate 見 `model_spec.md`。本文件只維護穩定原則與規劃；當前 stage、gate 與下一角色只見 `status/current.md`，Designer／Developer 動態內容分別見 `status/design.md` 與 `status/development.md`。

---

## M4 clean replacement boundary（2026-09-12）

USER確認M4以最小可行離線語音架構為目標：M4A提供Accepted Audio，M4B完成最小Reasoner、
同一Product Session的真實多輪Conversation與Audio+LLM resource/timing facts；M4-ERR先關閉production
error taxonomy、backend usability、recovery與fatal exit，M4C再完成整機State Manager／Display／
streaming-speak composition及audible-onset驗證。實際tool在M5，camera/look在M6。

舊M4B-MVA-001/002、fresh-Conversation、model action envelope、fake prewarm與固定8/48/768 recycle
均已退役，不是compatibility target。[M4B replacement design](implement/ch_m4b_llm_production.md)
從已驗證Foundation重建listen-only V2D2 profile、exact admission、Conversation replacement、
`snowboard.llm/3`與新memory/profile gate；POC evidence是provenance/input，不自行取得產品PASS。

M4B不設定response-time ceiling，只記錄同一monotonic timeline；M4C/ALPHA依後續整機證據裁定目標。
穩定分工與順序見[M4 plan](milestones/M4.md)及[M4B gates](milestones/M4B_MVA.md)；當前stage、
next owner與Developer/Tester entry仍只見[`status/current.md`](status/current.md)。

## 1. 規劃基準

### 1.1 規劃前提

* Core 正式支援 CPython 3.11、3.12、3.13；Developer convergence loop 使用團隊指定的單一主要版本，candidate portable gate 必須覆蓋三個 minor。Pi 耦合工作以 Pi 為主要 working tree，直接修正並執行 affected portable tests 與 target diagnostic 至全綠，再以相同 base 與工作路徑同步回工作站並確認內容一致；Pi 開發與正式 gate 都只用該 milestone 固定的部署 runtime，不將 Python matrix 乘到實體測試。
* Linux / Raspberry Pi OS / Raspberry Pi 5 是 POSIX process signal (`SIGINT` / `SIGTERM`)、native lifecycle、runtime 與硬體驗證的權威平台。
* Windows 僅驗證純 Python、mock / null、config 與 portable subprocess 測試（如 pipe/stream readiness）；明確排除 POSIX process signal 節點驗證，且不得為此修改 production signal architecture。
* 所有文件與驗收命令均使用啟用虛擬環境後的 python 。

### 1.2 階段定案原則

階段從規劃進入實作前，必須同時滿足：

1. 階段範圍、相依、排除與驗收問題已固定；上游 authority 無未解的實際契約衝突。
2. Tester 根據具體設計完成該階段 Test Spec，保留直接對應產品失敗的測項。
3. Developer 確認估點與工作路徑；估點不改產品契約。
4. 若依賴外部 POC，需有可採用的具體介面與必要結果；不依賴的研究不作為 entry gate。
   不新增互簽、freeze、authorization 或通用 administrative closure。

各條件的當前完成狀態只記於 `status/current.md`。條件未完成前，不得以「已有 milestone 規劃」推定 Developer 已獲准開始該階段。

### 1.3 階段依賴

本節為目前採用的階段順序。具體 M5.tool 契約與 entry 見
[M5](milestones/M5.md)、[設計](implement/ch_m5_tool.md)及 [current](status/current.md)。

```text
M1 純軟體核心
 └── M2 Mock 對話垂直切片
      └── M3 Raspberry Pi HAL 與硬體 bring-up
           └── M4 本機 AI 語音主線（M4a + M4b + M4c 同 SHA 通過）
                └── ALPHA Voice-only 產品化收斂 Gate
                     └── M5.tool 有限工具能力（真實 LLM＋mock）
                          └── M5 MQTT 發送與外部 read
                               └── M6 Camera／YOLO／Look
                                    └── M7 Display UX 完整化
                                         └── BETA 已納入能力的產品收斂 Gate
```

> `ALPHA` 與 `BETA` 為產品成熟度 Gate，不是功能 milestone。`M4 Accepted` 不推定 `ALPHA Accepted`；`M7 Accepted` 不推定 `BETA Accepted`。詳見 `docs/milestones/ALPHA.md` 與 `docs/milestones/BETA.md`。

ASR Product R1 若由 User 開線，使用獨立但不取代原線的條件式產品路徑：

```text
shared Core fork SHA
 ├── original: M4 → ALPHA ──┐
 └── R1: M4a.R1 → M4b.R1 → M4c.R1 → M4.R1 → ALPHA.R1 ──┴── baseline selection → M5.tool → M5
```

R1 branch 可在原 `ALPHA Accepted` 前建立與前進，但只能從已 commit 的明確 Core fork
SHA 開始，且不得取得原線的 gate credit。M5.tool 開發前依
`docs/milestones/ALPHA_R1.md` §5 記錄唯一 baseline；`ALPHA` 與 `ALPHA.R1`
不得同時進入 M5.tool。M5.tool 視為 M5 工作包的第一段。

每條已開立的產品線內，後一階段必須在該線前一階段驗收通過後開始。若前一階段只完成部分功能，不以 feature flag 或「已知失敗」跳過其 gate。

#### 1.3.1 流程修訂決策：M5.tool → M5 MQTT → M6 Look

USER 已確認本順序，先前 M6pre／M6E 拆分不再使用。詳細決策與驗收邊界集中在
[M5.tool／M5](milestones/M5.md)、[M6](milestones/M6.md)，不維護第二份草案。

- M5.tool：真實 Gemma＋mock 派發／Look 結果，完成有限能力意圖、驗證、固定派發
  回饋與原 Conversation 的下一輪回答。每 turn 一次推論，不做通用 reasoning loop。
- M5：真實 MQTT 發送與接收。外部 response／主動通知經 buffer／read，不是 handler return。
- M6：`perception.look(camera + YOLO + 結果整理／prompt) → LLM`；Look 那輪只看、不等 listen。
- VLM 獨立 POC：先描述影像，再交原對話 LLM 回答；研究現有 Gemma／runtime、模型共用、
  描述品質與 Pi 成本，不阻擋 YOLO 主線。具體研究範圍見 M6 §3。
- Wake 移出目前工作；BETA 前重新評估是否加入，不預設必做。不要求 wake IPC／模型選型。
- 本輪不納 read／Look 交錯；跨 Conversation 是明確 error path，不開另一套記憶研究。

M5.tool 的 architecture delta 見 [AR_impl_M5_TOOL_I](reviews/AR_impl_M5_TOOL_I.md)。
此為實際契約衝突修正，完成後直接交 Test Spec，不增加例行審查 gate。

### 1.4 共同完成條件

對 active／未來工作，先說明新增功能的價值及可能的產品失敗，再選擇適用驗證：

* 新增契約與直接影響回歸有測試；async race 使用明確 barrier，不以 sleep 猜時序。
* 既有適用測試不得刪除、skip 或 xfail 掩蓋失敗；不無條件重做全部已 Accepted 驗收。
* 真實模型語意、硬體與真人體驗以相應證據驗證，mock 不替代實際能力 PASS。
* Pi 上以待提交的相同內容完成所有適用自動、整合、硬體及人工測試後才可準備 commit。
  純文件變更可在工作站完成適用檢查；commit 仍依 git.md 取得 USER 明確同意。
* 公開 evidence 留必要 boolean、count、stable code／量測；不記 credential、prompt、
  完整 payload、transcript、音訊或影像。內容判讀留在 private runtime。
* Startup／測項不計算或驗證 source、config、model、artifact、evidence、text digest。
  必要內容確認只由 operator 在明確移轉／診斷邊界單獨執行。
* 真正驗取消／恢復／shutdown 的情境保留對應資源斷言，不擴展成通用 owner 清單或全矩陣。
* 唯一流程為 Design → Test Spec → Developer → Verify；實際上游矛盾回 owner 修正，
  不新增角色互簽、文件核准或 candidate freeze。已完成與封存證據維持原狀。

### 1.5 Designer 輔助規格文件產出時機

以下兩份文件由 Designer 產出，不在 implement/ 章節範圍內，但為後期里程碑的進場 gate 所需：

* `docs/display_spec.md`：最晚於 **M2 驗收期間**完成。M3 進場 gate 要求 selected profile 已納入 Tester 的 test spec 與 Developer 工作包（§5.2）。M1 / M2 不依賴本文件。

* `docs/model_spec.md`：M3驗收期間先建立schema與未定欄位。M4 generic protocol / fake scaffold不等待runtime baseline；Audio M2B reviewed selection後才可填入candidate-specific provisional設定，Audio M3 target/HAL qualification後才可準備產品exact-SHA acceptance，Gate 2B final handoff後才固定ASR / TTS production baseline。LiteRT-LM依M4b gate另行固定；M6 進場依賴 YOLO baseline（見 milestones/M6.md §2.3），Wake 延後、VLM 為獨立研究。M1 / M2 / M3不依賴本文件。

兩份文件均不阻擋 M1 / M2 立即啟動。

---

## 2. 階段總覽

| 階段 | 主要成果 | 主要平台 | 契約來源 |
| :--- | :--- | :--- | :--- |
| **M1** | 基礎契約、事件、Bus、SM、RM、三級收斂、config、logging 的純軟體核心 | 開發機 | `Ch 1 / 2 / 3 / 4 / 5 / 6 / 10 / 11` |
| **M2** | 使用 mock / null 完成可啟動、可對話、可收斂的垂直切片 | 開發機 | `Ch 2a / 2b / 7 / 9` |
| **M3** | Raspberry Pi 5 真實 HAL、null fallback 與 selected Display profile | Raspberry Pi 5 | `Ch 2a / 5 / 8 / 10 / 11`、`display_spec.md` selected profile、Core 已採用的 Audio / Display POC contract |
| **M4** | M4a Audio、M4b LLM、M4c Session Display 全數通過的本機語音主線 | Raspberry Pi 5 | `Ch 2b / 4 / 5 / 6 / 9 / 10 / 11`、M2B後的provisional model recipe與Gate 2B後的final model baseline |
| **ALPHA** | Voice-only 產品化收斂 Gate：五大項 L／P／R／Q／M：Lifecycle、Performance（保留 P01–P05，ALPHA.P 新 PN／PH）、Recovery、六項品質 regression、真人自由對話／操作 | Raspberry Pi 5 | `docs/milestones/ALPHA.md`；M4 Accepted product path |
| **ALPHA.R1** | 條件式 ASR Product R1 Voice-only 收斂 Gate；不改寫或取代原 ALPHA 結論 | Raspberry Pi 5 | `docs/milestones/ALPHA_R1.md`；M4.R1 Accepted exact SHA |
| **M5.tool** | 唯一 Accepted Voice-only 基礎上的真實 LLM＋mock 工具／Look、下一輪接續 | Raspberry Pi 5 | `implement/ch_m5_tool.md`、`milestones/M5.md` §2 |
| **M5** | M5.tool 後的 MQTT 發送、外部 response／主動通知與 read | Raspberry Pi 5 | `milestones/M5.md` §3、`Ch 2b / 7 / 9 / 10 / 11` |
| **M6** | Camera／YOLO／結果整理與 Look 接續；VLM 描述另列非阻擋 POC | Raspberry Pi 5 | `milestones/M6.md`；YOLO 選型於 M6 entry 固定 |
| **M7** | 正式 Display 版面、資產、動畫與視覺 UX 完整化 | Raspberry Pi 5 | `Ch 8`、M7 開發前核准的 `display_spec.md` revision |
| **BETA** | 已納入能力的產品收斂；依當時具體風險固定必要整合、穩定性與診斷，Wake 是否加入先行決策 | Raspberry Pi 5 | `docs/milestones/BETA.md`；M7 Accepted exact SHA |

---


> **注意**：各階段詳細規劃已拆分至 `docs/milestones/M{x}.md`；產品收斂 Gate 另見 `ALPHA.md`、`ALPHA_R1.md` 與 `BETA.md`。Agent 只應讀取當前進行中或任務直接影響的檔案。

## 10. 規劃維護原則

### 10.1 估點與範圍調整

工期、affected scope 與 active work package 由 Developer 記於 `status/development.md`，不寫回本文件。Designer 只把因此產生的 gate、跨角色阻擋或階段影響更新到 `status/current.md`。估點變更不直接修改驗收條件；若估點顯示單一階段範圍過大，由 Designer 拆分階段並重新確認其相依與驗收。只有階段切分、穩定範圍或驗收原則改變時才修改本文件。

### 10.2 docs/protocol.md 動筆 gate

`docs/protocol.md` 不在 M1 / M2 預先展開；以下任一階段開始前必須先完成對應章節：

* **M4** : LiteRT-LM child process wire schema。
* **M5.tool** : LLM 有限能力 semantic terminal 與新 profile；見 `protocol.md` §7。
* **M5** : 公開 MQTT topic / payload schema，先固定實際 domain。
* **M6** : YOLO 路徑依實際 adapter 隔離方式定義必要 wire；不預設 wake IPC。
* **Wake（延後）** : BETA 前決定加入後，才在實作前定 wake daemon IPC。

每個 wire schema 必須先於其 producer / consumer code，並明列版本與 breaking-change 政策；內部 Event dataclass 不因此增加 version 欄位。
