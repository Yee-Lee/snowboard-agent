# Core Team → POC Display Team: M3 Display HAL Contract v0.2 Review

* **Delivery ID**: `DELIVERY-004-poc_display-m3-v0.2-review`
* **Previous delivery**: `DELIVERY-003-poc_display-m3_feedback`
* **Reference**: `docs/outsource/references/poc_display/display_m3_contract_draft.md` v0.2
* **Decision**: `Needs Revision (Blocking)`
* **Review role**: Core Team Designer
* **Date**: 2026-08-08

---

## 1. 審查結論

v0.2 已補上 Hardware Gate 與 Integration Contract，前一輪「完全缺少硬體規格與交接邊界」的 P1、P2 可關閉；但新增內容與現行權威設計、原廠接線資料及可驗證效能上限仍有衝突，因此目前**不得升級為 v1.0 / Accepted，也不得作為 M3 development baseline**。

本輪要求 POC Display Team 僅收斂 native driver、Python HAL adapter、硬體 fixture 與 evidence contract。產品端 Renderer、Arbiter、Display profile 與 milestone 行為仍以 Core Team 文件為權威，不由 POC contract 重新定義。

**Architecture change: No.** 本輪沒有發現需要修改 `docs/arch.md` 的模組邊界；問題均可透過外部 contract 對齊既有設計與補齊 evidence 解決。

### 已符合項目

| 項目 | 結果 | 依據 |
|---|---|---|
| HAL 不採 IPC、Queue、獨立 Service | 符合 | `docs/arch.md` §5.3；PM `OUT-POC-2026-004` |
| HAL 不管理 UI content、priority 或 fullscreen owner | 符合 | `docs/arch.md` §5.3；`docs/implement/ch08_display_arbiter.md` §1–§5 |
| `clear / write_pixels / show / size` 的 back-buffer 基本方向 | 原則符合 | `docs/implement/ch02a_core_hal.md` §2a.3 |
| Raspberry Pi 5、SSD1351、128×128、RGB565 作為主要 fixture | 可採用，待下列 D3/D4 修正 | `docs/milestones/M3.md` §5.1–§5.4 |
| POC 提供 `.so`、adapter、manifest、Pi evidence；Core 回交 SHA | 方向符合，待下列 D5 補齊 | PM `OUT-POC-2026-006`；M3 target-device evidence 原則 |

---

## 2. Blocking findings

### D1 — Python HAL lifecycle、型別與模組落點衝突

**契約依據**

* `docs/implement/ch02a_core_hal.md` §2a.1：所有 HAL 的 `start()` / `stop()` 均為 `async`，供 Resource Manager 以統一 lifecycle 管理。
* 同文件 §2a.3：權威 Protocol 位於 `src/sbd/core/display/base.py`，`write_pixels(buf: bytes)`；chip adapter 位於 `core/display/<chip>/driver.py`，native library 位於該 chip 的 `native/`。
* `docs/implement/ch08_display_arbiter.md` §0、§7：render primitives 同步且只可由 event-loop thread 呼叫；這不代表 lifecycle 也改成同步。

**實際證據與差異**

v0.2 §1–§2 將整個 HAL 描述為純同步，並把 `start()` / `stop()` 定義成同步方法；Protocol 路徑改成 `core/display/hal/protocol.py`，另加入未定義的 `DisplayInfo`、`Rgb565Frame`。這會讓 adapter 無法直接滿足 Core 已定稿的 Protocol，亦破壞 Resource Manager 的 `await instance.start()/stop()` 統一流程。

**影響**

若照 v0.2 實作，Core 必須建立第二套 Protocol 或私下包裝 lifecycle，造成跨 HAL 不一致、fallback/cleanup 假綠燈及重複模組 ownership。

**建議修正方向**

明確宣告 Core 的 `DisplayDevice` 為唯一 Python contract：保留 `async start/stop`，其餘 `clear/write_pixels/show/size` 同步；POC adapter 實作此 Protocol，不重新建立 `hal/protocol.py`。使用 `bytes`，或在 v0.3 完整定義 `Rgb565Frame` 並證明與既有 renderer 回傳 `bytes` 相容；不需要的 `info` 應移除。

**最低驗收條件**

1. v0.3 的方法簽名、落點、thread/lifecycle 語意與 Ch 2a/Ch 8 一致。
2. adapter 可被既有 Resource Manager `await start/stop`，`stop()` 冪等，失敗可觸發 NullDisplay fallback。
3. 不引入第二套 Display Protocol、Renderer 或 Arbiter ownership。

### D2 — Native C ABI 尚不是可實作、可驗錯的契約

**契約依據**

* `docs/implement/ch02a_core_hal.md` §2a.1、§2a.3：real backend 啟動失敗必須可 raise，runtime buffer 長度錯誤必須拒絕，stop 必須安全且冪等。
* `docs/implement/ch08_display_arbiter.md` §8：native/runtime failure 必須能被 Python boundary 捕捉並進入 rendering-disabled degradation。

**實際證據與差異**

v0.2 §4 只列四個 function prototype；`DisplayConfig` 的 struct layout、ABI version、handle/error 值域、pixel byte order、buffer ownership、重複 close、未 open/非法 handle、thread restriction及 Python exception mapping 均未定義。`display_clear()` / `display_close()` 回傳 `void`，卻又宣稱底層會攔截所有錯誤；Python 無法判斷失敗。Python 的 `clear()` 是只改 back buffer，C 的 `display_clear()` 卻描述為直接清實體面板，`write_pixels()+show()` 如何映射到 `display_present_rgb565()` 也不清楚。

**影響**

不同 adapter 可產生不同 buffer/flush 行為；SPI/GPIO/open/present 失敗可能被吞掉，導致 capability、fallback、runtime degradation 與 cleanup 無法驗收。

**建議修正方向**

提供實際公開 header 或在 contract 中完整定義：固定寬度型別、config struct 與 version/size、status/error enum、handle lifecycle、RGB565 byte order與長度公式、buffer 借用期限、thread ownership，以及每個錯誤到 Python exception 的 mapping。統一 back-buffer ownership：可由 Python adapter 持有，`show()` 單次呼叫 native present；`clear()` 不得先做硬體 I/O。

**最低驗收條件**

1. header 可獨立編譯，ABI/version 與 artifact checksum 可由 manifest 定位。
2. open/present/close 的成功、非法 config、非法 handle、錯長度、重複 stop/close 行為均有明確結果。
3. 一次 Core display intent 對硬體只做一次 present；`clear/write_pixels` 不提前 flush，`show` 才 flush。
4. SPI/GPIO/open/present failure 可被 Python adapter 轉成 exception，符合 startup fallback 與 runtime degradation。

### D3 — Hardware Gate 的接線與可重現參數不正確

**契約依據**

* `docs/milestones/M3.md` §5.2、§5.4：selected hardware、接線與 local config 必須固定，人工結果需記錄硬體型號與 config hash。
* PM `OUT-POC-2026-004`：必須固定 selected hardware gate。
* Waveshare 官方接線表：1.5-inch RGB OLED 與 2-inch LCD 的 Raspberry Pi 範例皆使用 DC/DS = BCM25（Board 22）、RST = BCM27（Board 13）。

**實際證據與差異**

v0.2 §5 寫成 DC = BCM24（Board 18）、RST = BCM25（Board 22），與兩個指定 Waveshare 模組的官方表不一致。文件也未固定 4-wire/3-wire mode、面板 SKU/revision、orientation、RGB565 byte order，且 primary OLED 與 backup LCD 共用同一張接線表，但 LCD 才有 BL。現行 Core `DisplayConfig` 也只有 `spi_device`，尚無 speed/DC/RST 等 real-backend options；若不在同一 Design Ready gate 補齊，Developer 只能私自發明 config。

**影響**

照表接線可能無法啟動或誤驅動 GPIO；POC 與 Core fixture 不同時，測試結果不可重現，亦無法以 config hash 追溯。

**建議修正方向**

以 POC 實際測過的 selected OLED 為唯一 M3 primary fixture，分開列出 optional LCD fixture；逐面板固定 SKU/revision、4-wire mode、供電/logic level、BCM 與 Board pin、SPI mode、chip select、rotation、logical/physical size、RGB565 byte order。提供 sanitized local config schema/範例與 config hash；Core Team後續在單一 M3 Design Ready delivery 對齊 Ch 10，不把真實部署值寫入 generic defaults。

**最低驗收條件**

1. 接線表與實際 POC fixture、原廠資料一致，並由照片/manifest 識別 pin 與面板 revision。
2. primary fixture 的所有 runtime 參數都能由 local config 表達，無需環境變數或 source hard-code。
3. 同一 config hash 可重跑 diagnostic；backup LCD 不作 primary OLED 通過的替代證據。

### D4 — 60 MHz、`<20 ms` 與 60 fps 宣稱缺乏可成立的硬體基礎

**契約依據**

* `docs/milestones/M3.md` §5.4：效能與 OLED 可讀性必須以固定 fixture/evidence 驗收。
* `docs/milestones/M7.md` §9.4：要求驗證更新效能與動畫收斂，但現行產品契約**沒有**固定 60 fps；POC 不應自行提高產品門檻。
* SSD1351 datasheet Rev 1.5 Table 13-4：4-wire SPI 最小 clock cycle 為 220 ns，約等於 4.55 MHz 上限。

**可驗證證據／最小重現**

* SSD1351 128×128 RGB565 單幀 payload 為 `128 × 128 × 2 = 32768 bytes`。依 220 ns/bit，光 payload 的理論下限約 `57.7 ms`，未計 command、GPIO 與軟體 overhead，無法支撐 60 fps（每幀 16.7 ms）。
* 即使假設未經 datasheet 支持的 60 MHz，ST7789 320×240 RGB565 光 payload 也需 `320 × 240 × 2 × 8 / 60 MHz = 20.48 ms`，已不符合 v0.2 所稱全螢幕 `<20 ms`。
* `show()` latency 也不會只等於 SPI payload time，仍包含 command、CS/DC GPIO、syscall/driver 與 scheduling overhead。

**影響**

以此作 v1.0 基準會形成不可達 acceptance、鼓勵超出元件規格的 overclock，並錯誤推導 M7 無需 partial update 或其他渲染策略。

**建議修正方向**

刪除「HAL 完全能支撐 60 fps」、「60 MHz 下 `<20 ms`」及因此排除局部更新的結論。M3 只固定經實機證明且不超出採用規格的 SPI 設定與 P50/P95 full-frame latency；M7 的 fps/animation target、是否 partial update 或更換硬體，留給 `display_spec.md` Complete profile 與 M7 Design Ready gate 決定。

**最低驗收條件**

1. v0.3 區分 datasheet limit、driver requested speed、實測 effective speed，不再以 requested speed 當實際 throughput。
2. POC evidence 提供至少樣本數、warm-up、P50/P95/max、resolution/pixel format、config hash、CPU/OS/driver、測量邊界。
3. M3 contract 不承諾 60 fps；任何超規設定不得成為產品 baseline。

### D5 — Artifact provenance 與 integration acceptance 過弱

**契約依據**

* PM `OUT-POC-2026-006`：integration 必須引用 Accepted POC SHA、artifact checksum/license，不能把 POC 自驗或 branch HEAD 當 Accepted。
* M3 target-device evidence 原則：自動化行為、環境快照、config hash、exact SHA 與人工 checklist 必須可追溯；外部 POC 自驗不能取代 Core Tester 驗收。
* `docs/milestones/M3.md` §5.4：除畫面可讀外，還需驗證 clear/write/show、ownership、NullDisplay fallback 與 failure 不改變主流程。

**實際證據與差異**

v0.2 §6 只要求「Exact Commit SHA」，沒有固定 full 40-character SHA 的內容範圍、comparison baseline、`.so`/header/adapter checksum、build toolchain、license/notice 與 known limits。POC 最終驗證僅以「畫面正確且不 crash」結案，無法揪出錯誤 buffer order、吞錯、fallback 或 cleanup 假綠燈。文件亦要求 Core Team 直接把 POC reference 標成 v1.0；依 repository workflow，POC 應發布修正版，Core 的採用決定另記於 `deliveries/` ACK，不修改外部 reference 原文。

**影響**

無法證明 Core 驗的是哪個 driver/artifact，也可能在只通 smoke 的情況下提前結案，失去授權與供應鏈追溯。

**建議修正方向**

沿用 Audio contract 的「Accepted as design input」與「final integration acceptance」兩段式 gate。POC v0.3 先補齊 artifact/provenance contract；修正通過後由 POC 發布 v1.0，Core 另出 ACK。Core M3 Accepted 後回交 full SHA、環境/config、測試/evidence 索引與 known limits；POC 只針對其硬體/native 邊界複驗，不重做產品 arbiter 全面驗收。

**最低驗收條件**

1. manifest 含 POC source SHA、artifact/header/adapter SHA-256、build command/toolchain、license/notice、target OS/arch、config hash、known limits。
2. Core 回交 full 40-character SHA，明列包含 source、tests、權威文件與 evidence index。
3. POC integration 至少驗證 start/present/stop/reopen、錯長度、invalid device/fallback、重複 lifecycle、P50/P95 及無殘留 owner/resource；「看得到且不 crash」只能作人工補充。
4. Core Tester 的 M3 acceptance 與 POC fixture verification 分開記錄，二者不得互相取代。

---

## 3. Advisory findings（不阻擋 v0.3 複審）

### A1 — 將產品渲染章節標成 non-normative

v0.2 §3 的 Mutex、State Machine、Pillow/LVGL 與 M3–M7 建議超出 POC HAL 交付責任，且部分內容與 Core 已定稿的 event-loop thread、DisplayArbiter backing model、milestone 分期不同。建議縮成「Capability notes / Non-normative」，只描述 native HAL 能力與已測限制，並引用 Core Ch 8 / `display_spec.md`；不要規定 Core renderer engine 或另建 UI state machine。

### A2 — 避免把 SPI transfer 稱為硬體 atomic

Core 所稱 atomic 是「同一同步 call stack 中 intent 不交錯，且 `show()` 是唯一 flush boundary」，不是 SPI 線上的整幀瞬間更新。建議改成 `single-flush / non-interleaved update`，避免把「不顯示 half-built back buffer」誤寫成面板掃描絕對無 tearing/flicker。

---

## 4. 請 POC Display Team 回交 v0.3

請以同一份 v0.3 revision 一次回覆 D1–D5，附下列最小包：

1. 修訂後 contract（保持 Draft，不自行標 Accepted）。
2. 可編譯 C header、Python adapter contract 與 manifest 範本。
3. primary SSD1351 fixture 的更正接線/config、原廠規格引用與 evidence schema。
4. 已有實測則附 P50/P95 evidence；尚未完成可標 `IN_PROGRESS`，但不得保留未驗證的 60 MHz/60 fps 結論。
5. finding disposition 表：每項標記 `Resolved` 或 `Pending` 並附定位。

Core Team 複審只驗證 D1–D5、其直接影響範圍與新引入 regression。D1–D5 全數符合最低驗收條件後，可將此 contract **Accepted as M3 design input**；最終 M3 integration acceptance 仍待 Core Tester 與 POC fixture evidence 完成。

---

## 5. External technical references

* [Waveshare 1.5-inch RGB OLED Module wiki](https://www.waveshare.com/wiki/1.5inch_RGB_OLED_Module)
* [Waveshare 2-inch LCD Module wiki](https://www.waveshare.com/wiki/2inch_LCD_Module)
* [SSD1351 Rev 1.5 datasheet](https://files.waveshare.com/upload/a/a7/SSD1351-Revision_1.5.pdf)
