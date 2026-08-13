# Developer Progress ( dev_progress_M3.md )

本文件由 **Developer** 維護，記錄 M3 的任務拆包、Story Point、相依、模擬測試、Raspberry Pi 5 實體測試與 USER 協作安排。

**規劃約束**：

1. 本計畫不修改 `arch.md`、`implement/` 或已簽核的 `docs/test_spec/test_spec_M3.md` 契約；若 API 無法落實，依 workflow 開立 `IR_dev_M3`。
2. `TR_spec_M3_I` 的 coverage sign-off 只放行開發，不代表 implementation 或硬體驗收通過。
3. M3 共 **47 個 Test ID**：27 個 `DEV-PY311`、20 個 `RPI-NATIVE`。每一個測項都要有真實 assert、可定位 pytest node 與對應證據；不得以人工 smoke 取代可自動驗證的結果。
4. 所有正式 Pi test card 必須對應同一個完整 40-character implementation SHA。未執行、硬體缺席或只測 working tree 時只能標 `Pending` / `Blocked` / `Diagnostic`，不得標 `Pass`。
5. USER 負責實體接線確認、按鍵操作、喇叭聽覺、OLED 視覺及必要的電平量測；Developer 負責固定 fixture、命令、程式化斷言、log / checksum 收集與結果判讀；Tester 對 delivery exact SHA 執行獨立驗收。

---

## M3 ── Raspberry Pi HAL 與硬體 bring-up

### 進場與估點基準（2026-08-13）

- Designer gate：`Development Ready — Audio real backend blocked by POC P4`；M3 整體可開工。
- `TR_spec_M3_I`：`Resolved`，決議 `APPROVED FOR DEVELOPMENT`。
- Core design baseline：`1266a191640f3a3643105ef04368de8b22638786`。
- Display POC v0.3：Accepted as M3 design input；Audio Option A direction 已接受，但 selected implementation 仍須 P4 final selection ACK。
- 規劃前回歸基線：隔離 host ROS pytest plugin 後，`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q` 為 **204 passed in 18.56s**（Python 3.12.3）。未隔離時會因外部 ROS `launch_testing` 缺少 `lark` 在 collection 前失敗，屬 host 環境問題。
- 估點沿用既有口徑：**1 SP 約為資深開發者半天**，包含產品實作、真實 assert、聚焦測試、必要文件與 Developer 自驗。
- M3 重估為 **108 SP**（約 54 開發人日，單人順序執行口徑）。較原 99 SP 增加 9 SP，原因是 Test ID 由 43 增為 47、Audio native / stream config、fake-source seam及 Option A quality / lifecycle / resource evidence，並將 Ready / Blocked package 明確拆開。不含 USER 等待硬體／改線時間、Tester 獨立驗收、Designer 最終 review、外部 POC 回覆等待及驗收退件重工。

### Developer 開發紀錄

| 日期 | 工作包 | 狀態 | 結果 / 下一步 |
| :--- | :--- | :--- | :--- |
| 2026-08-13 | WP-M3-01 | **Completed** | 建立 47-ID manifest、M3 portable / RPi acceptance雙 gate、RPi deselection hook 與未預填 Pass 的 evidence card template；Blocked ID不會被計為Pass。 |
| 2026-08-13 | WP-M3-01~06、08、09、11 | **Developer complete except approved blockers** | 24 個可執行 DEV Test ID 全綠；完成 nested Audio schema、OLED-128 strict config、Null/Mock HAL、Renderer、Arbiter、Boot/Shutdown owners、picamera2/gpiod/Button host seams與M3 portable composition。M3-AUD-003/004、M3-CFG-002等待Audio P4。 |
| 2026-08-13 | WP-M3-10 | **Blocked — IR_dev_M3_I** | USER reference已驗 exact SHA `5c2b6ba532a2661d5db79e27736e79890931515f`並移至Core外 `/tmp`。ABI v1要求resolved `gpio_chip.chip_index`，Core Ch 10 DisplayConfig / factory輸入無對應欄位；已開 `M3-DISPLAY-CONFIG-001`，禁止硬編碼gpiochip0。 |
| 2026-08-13 | WP-M3-10 | **Unblocked — IR_dev_M3_I Resolved** | Designer新增strict `DisplayConfig.gpio_chip_index`與ABI v1直接mapping契約；missing / negative / mock-null carry regression通過。focused 23 passed；完整non-RPi 233 passed、1 deselected。 |
| 2026-08-13 | Regression | **PASS (non-RPi)** | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q -m 'not rpi'`：233 passed、1 deselected。`-m rpi` acceptance gate持續明確列出23個Blocked IDs，不宣稱M3 Accepted。 |

### 開工與 Blocking 結論

| 分類 | 結論 | 工作包 / 解除條件 |
| :--- | :--- | :--- |
| **Developer complete** | portable 工作已完成且 non-RPi regression 全綠 | WP-M3-01~06、08、09、11；guardrail、portable config / HAL、Renderer、Arbiter、Audio schema / fake seam、Camera、GPIO / Button與composition |
| **Blocked — Audio P4** | 不得實作／merge selected real backend，不得加入 production dependency lock | WP-M3-07；等待 POC 完整 40-character SHA、P4-A01~A10 evidence及 Core Designer final selection ACK |
| **Resolved — Display config contract** | `DisplayConfig.gpio_chip_index`由strict loader驗證並直接映射ABI v1；禁止hardcode或global/environment probe | `IR_dev_M3_I / M3-DISPLAY-CONFIG-001`已Resolved；WP-M3-10可繼續 |
| **Blocked — target device** | 不阻擋portable code；阻擋20張Pi card與M3 acceptance | WP-M3-12~13；前置real package解除後，等待USER確認Pi / peripherals、local config及安全操作時段 |
| **Not M3 blocker** | 不列入本階段 gate | LLM POC、Audio P3 TTS winner、Display ACK advisory |

accepted Display ABI v1的gpiochip boundary已由 `IR_dev_M3_I` 收斂：Core `DisplayConfig.gpio_chip_index`是唯一strict input，adapter直接映射到ABI v1；WP-M3-10已解除設計阻擋。

### POC Input Baseline

| POC domain | Accepted contract | Core adoption record | Source / artifact identity | License / target | Fixture / config | Open conditions | Evidence index |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Audio** | v1.0 locator：`docs/outsource/references/poc_audio/audio_m3_contract_v1.0.md` | `DELIVERY-AUDIO-POC-M3-ACK-001/002`；Option A direction accepted；`DELIVERY-AUDIO-POC-M3-VALIDATION-001` action required | Accepted delivery `87ff000559ded8c0d7499d621af7dfcccb81858c`；native evidence `0edeb7d9f8ff3811d1480ab4b464db2842978233`；候選 binding / resampler 尚未 selected，POC binary 不進 Core Git | Pi 5 target OS / arch、binding / resampler version、source hash、transitive dependency、license / notice與build identity皆由P4回交後核准 | INMP441 + MAX98357A、shared I2S、`googlevoicehat-soundcard`；P1 native FAIL、P2 direct `hw:0,0` PASS；實際channel、valid-bit alignment、sanitized local config / hash待P4與USER readiness | **Blocks Audio selected real package start**：P4 full SHA + required evidence + Core final selection ACK；P3延至M4a，不阻擋M3 | `DELIVERY-AUDIO-POC-M3-VALIDATION-001`定義P4-A01~A10；Core正式位置為`docs/outsource/evidence/<delivery-id>/audio/` |
| **Display** | v0.3 locator：`docs/outsource/references/poc_display/display_m3_contract_draft.md` | `DELIVERY-005-poc_display-m3-v0.3-ack`；Accepted as M3 design input，D1~D5 Resolved | Source candidate `5c2b6ba532a2661d5db79e27736e79890931515f`；已驗證checkout位於`/tmp/snowboard-display-reference-5c2b6ba532a2661d5db79e27736e79890931515f`；stage-exit evidence `055517a905bd2c8f8531c05acfa658854e25491f`；review `4ed5f64a2604fa3c388cfa60fb971bb508a4ee40` | Pi 5 / target OS arch；ABI v1、artifact license / notice與runtime identity由accepted manifest及target build重驗 | Waveshare 1.5-inch SSD1351；SPI0 CE0、4 MHz、operator-resolved gpiochip index、DC24、RST25；實際artifact / config full hash由target build / readiness card記錄 | Config boundary已由`IR_dev_M3_I`解決；WP-M3-10可開始native adapter，並直接映射validated index至ABI v1 | POC D1~D5只作輸入；Core正式位置為`docs/outsource/evidence/<delivery-id>/display/` |

> Baseline 表只引用已採用紀錄，不以 branch HEAD、縮寫 checksum、候選套件或 POC「可見／不 crash」自驗冒充 Core integration baseline。所有external reference repo均由USER在相關package開工前指派位置，Developer手動clone到Core repo外並鎖定exact SHA；clone及產物不進Core Git。

---

### 工作包總覽

| 工作包 | SP | 範圍與主要交付 | 主要 Test ID | 相依 | 開工狀態 |
| :--- | ---: | :--- | :--- | :--- | :--- |
| **WP-M3-01** 測試與 evidence 骨架 | 5 | M3 entrypoint、47-ID manifest、RPI deselection、fixture / barrier / call-log、card schema、環境與checksum index | M3-REG-001（部分） | M2 PASS、TR spec Resolved | **Completed** |
| **WP-M3-02** Portable config + SSD1351 strict config | 9 | Audio native / stream schema、mock/null real-only rejection、Display selected profile strict validation；不加入P4後才可決定的Audio allowlist | M3-CFG-001；M3-CFG-002 skeleton；M3-HAL-001（部分） | WP-M3-01 | **Completed except P4 conditional ID** |
| **WP-M3-03** Portable HAL / factory / fallback | 6 | Null / Mock契約、Pi-only lazy import、RM real→null、GPIO unavailable graph | M3-HAL-001~002、M3-AUD-001~002、M3-DSP-001~002、M3-CAM-001、M3-GPIO-001~002 | WP-M3-01、02 | **Completed** |
| **WP-M3-04** selected profile Renderer | 10 | Hint / RenderModel、128×128 RGB565、offline fonts、State / Main / Blank、wrap / ellipsis / missing glyph | M3-REND-001~005 | WP-M3-01、02 | **Completed** |
| **WP-M3-05** Display Arbiter / owner lifecycle | 10 | slot registry、atomic flush、fullscreen ownership、degrade latch、thread affinity、StatusBar、Boot / Shutdown Blank | M3-ARB-001~007、M3-SCN-001 | WP-M3-03、04 | **Completed** |
| **WP-M3-06** Audio schema / fake-source seam | 5 | native / stream boundaries、raw-source與converter seam、deterministic fixture與P4後測試接點；不選binding / resampler / valid bits | M3-AUD-003~004、M3-CFG-002 preparation | WP-M3-01~03 | **Completed to approved P4 boundary** |
| **WP-M3-07** Audio Option A selected real package | 11 | direct ALSA、核准conversion、exact framing、selected allowlist / dependency lock、async lifecycle、fallback與Pi setup | M3-AUD-003~004、M3-CFG-002、M3-AUDI-001~004 | WP-M3-02、03、06；P4 final ACK | **Blocked by Audio P4** |
| **WP-M3-08** picamera2 real backend | 6 | JPEG / RGB / I420、stride / plane conversion、lifecycle、missing CSI fallback與setup | M3-CAMI-001~003 | WP-M3-02、03 | **Developer complete；Pi evidence Blocked** |
| **WP-M3-09** gpiod + Button InputSource | 10 | libgpiod 2.x fd readiness、debounce、GPIO output、five button semantics、graceful shutdown | M3-GPIOI-001~002、M3-BTN-001~005 | WP-M3-02、03 | **Developer complete；Pi evidence Blocked** |
| **WP-M3-10** SSD1351 native adapter | 13 | accepted ABI v1 adapter、source build、artifact validation、buffer / byte order、lifecycle、cleanup與setup | M3-DSPI-001~006 | WP-M3-02~05；resolved config→ABI gpiochip boundary | **Ready — IR_dev_M3_I Resolved** |
| **WP-M3-11** Portable composition / fallback | 6 | M3 graph、null / mock factories、capability freeze、Display observer chain、Boot / Shutdown與blocked-real seam | M3-HAL-002、M3-SCN-001、M3-REG-001（部分） | WP-M3-02~05、08、09 | **Completed** |
| **WP-M3-12** Real composition + Pi diagnostics | 10 | selected real wiring、20 RPI nodes、fixed fixtures、latency / cleanup probes、USER checklist與cards | 全部20個RPI-NATIVE IDs | WP-M3-07~11；USER readiness | **Blocked by 07 / 10 / target device** |
| **WP-M3-13** Regression / exact-SHA delivery | 7 | 27 DEV IDs、20 Pi cards、M1/M2/full regression、clean Python 3.11+、evidence index與handoff | M3-REG-001；全體47 IDs | WP-M3-01~12 | **Portable regression complete；acceptance Blocked** |
| **合計** | **108** | | **47 個 M3 Test ID** | | |

### 工作包最低完成條件

#### WP-M3-01：測試與 evidence 骨架（5 SP）

- 建立 `tests/milestones/test_m3_rpi_hal.py` 與 47-ID manifest；entrypoint 集中重現但不以 wildcard re-export 造成重複 collection。
- `tests/conftest.py` 將未明確選取 `-m rpi` 的 Pi 測項 **deselect** 並列出數量，不再以 skip / xfail 處理。
- 每個 test function / parameter set 標記確切 Test ID；manifest 拒絕 unmapped、empty、skip、xfail 或只 assert fixture 自身的假綠燈。
- race / lifecycle 只用 `asyncio.Event`、Condition predicate、fd readiness 或 process completion 控時；不使用 sleep 猜同步。
- 建立 evidence template，但不預填 Pass；正式 card 只在 exact SHA 執行後更新。

#### WP-M3-02：Portable config + SSD1351 strict config（9 SP）

- 依Ch 10建立`AudioFormatConfig`、input / output native / stream schema與mock/null real-only欄位拒絕；P4前不加入resampler identifier allowlist或valid-bit final值。
- 依 Ch 10 擴充 selected profile 所需欄位：profile、128×128、RGB565、rotation 0、MSB-first、32768 bytes、artifact path / SHA、ABI v1、SPI0 CE0 / mode 0 / 4 MHz、DC24 / RST25。
- unknown、缺值、checksum / ABI / size / format / rotation / byte-order / buffer / speed / SPI / GPIO contradiction 都在 factory 前以 path-aware `ConfigValueError` 拒絕。
- invalid config 證明無 native import、`dlopen`、GPIO / SPI call；mock / null 攜帶 real-only 欄位同樣拒絕。
- `config.example.yaml` 走同一 loader 且不含真實 pin、artifact path、credential 或使用者絕對路徑；secret repr / str 不洩漏。

#### WP-M3-03：Portable HAL / factory / fallback hardening（6 SP）

- 維持既有 Protocol，不新增平行 HAL API；real dependency 只在被選中 branch lazy import。
- NullAudioInput 可 `aclose()` / reopen、拒絕同 instance 第二個 active iterator；NullAudioOutput 完整消費；NullCamera 回合法 RGB / I420 / JPEG；NullDisplay `(0,0)` 全 no-op。
- MockGPIO 一 pin 一 owner、debounce、callback isolation、unregister 冪等與 configure-before-set；MockDisplay 嚴格驗 buffer 長度並保留 call order。
- RM 對 audio / display / camera factory 或 start 失敗轉 null 並 freeze capability=false；null 再失敗 fatal；GPIO failure 不建立 NullGPIO 且不啟動下游 input source。

#### WP-M3-04：selected profile Renderer（10 SP）

- 實作 Ch 8 的 immutable `DisplayHint` / `RenderModel` 與同步 renderer，不讓 chip / SPI / ABI 邏輯滲入 Renderer。
- M3 gate 僅包含 `status.state`、固定 fixture 用 `main.text`、`fullscreen.blank`；不得提前產品化 M4c `main.error` / session owner 或 M7 animation。
- 128×128 output 必為 32768-byte RGB565 MSB-first；Blank 全黑；六種 state 文案、missing glyph `□`、pixel-width wrapping、5 行 deterministic ellipsis 與空字串 clear 有真實 bitmap assert。
- 只從 repository Noto Sans TC assets 載入，驗證兩個已簽核 SHA-256 與 OFL inventory，不依賴 OS font。

#### WP-M3-05：Display Arbiter / owner lifecycle（10 SP）

- 實作四個已定稿 sync API、static slot registry、immutable snapshot 與一 intent 一組 clear→write→show。
- fullscreen 期間只更新 backing model；同 owner 更新、不同 owner 拒絕、非 owner release no-op；release 後只 render 最新 Normal model 一次。
- `(0,0)` 不呼叫 renderer但 ownership 有效；首次 renderer / HAL runtime failure 只 log 一次並 latch degraded，不 publish `ErrorOccurred` 或進 SM ERROR。
- Arbiter 不停止 device；stop / late write 冪等；native thread 直接呼叫由 event-loop affinity guard 拒絕。
- StatusBar start seed IDLE 不發虛構 Event；Boot owner finally release、Shutdown owner 維持到 Display stop，包含 NullDisplay / failure 路徑。

#### WP-M3-06：Audio schema / fake-source seam（5 SP）

- 實作native / stream config資料結構、mock/null real-only欄位拒絕及private raw-source / converter seam；不得選定binding、resampler、valid-bit alignment、buffer或async I/O。
- 建立non-aligned chunks、左右channel tone、silence、impulse、clipping、1 kHz / 12 kHz與lifecycle call-log fixture，保留M3-AUD-003/004及M3-CFG-002的P4後接點。
- P4前不得建立可發布的`driver=alsa` production config，不得import / lock `pyalsaaudio`、`samplerate`或其他候選，也不得以sample dropping完成假實作。

#### WP-M3-07：Audio Option A selected real package（11 SP）

- 只有POC回交完整SHA、P4-A01~A10 evidence且Designer發出final selection ACK後才可開工；ACK-002或候選套件名稱不能解除gate。
- 以direct ALSA `hw:`開啟48 kHz / stereo / S32_LE，核對requested / actual format；依核准config選channel、解析valid bits、stateful anti-alias 3:1 resample、saturating S16並累積成640-byte frame。
- callback / blocking I/O不得阻塞event loop；aclose、cancel、failure、stop、reopen須釋放ALSA owner並重置filter / accumulator / partial state。
- selected dependency version / hash / license / system package / build寫入production lock；target build產物不進Git。
- AudioOutput M3 fixture直接匹配48 kHz / stereo / S32_LE；P3前不做runtime adaptation。invalid device走RM null fallback並記sanitized evidence。

#### WP-M3-08：picamera2 real backend（6 SP）

- Pi-only dependency 只在 selected branch import；`capture()` 回 config 固定格式，不在 runtime 偷換格式。
- JPEG 可 decode 且尺寸正確；RGB 長度 `width*height*3`；I420 長度 `width*height*3//2`，處理 picamera2 stride / plane layout，不以截長冒充格式轉換。
- start / capture / stop / reopen 可重複；缺 CSI 或初始化失敗走 NullCamera，log / capability / Look worker 不 fatal。

#### WP-M3-09：gpiod + Button InputSource（10 SP）

- 使用 libgpiod 2.x 與 event-loop fd readiness；callback task 有追蹤、例外隔離、stop 時完整收斂。
- register / debounce / unregister / configure_output / set_output 與 monotonic `GPIOEvent.at` 對齊 Protocol；不得 claim kernel-managed SPI CE0。
- Button 依 config 的 `short_press_min_ms` / `long_press_min_ms` 分流：IDLE 短按、session 中斷、任意狀態長按、ERROR recovery 前後五條語意都由 process / state assert 驗證。
- GPIO unavailable 時 capability=false、Button source 不啟動；USER 實測 output pin 必須使用安全負載或量測工具，不直接短路 / 帶載改線。

#### WP-M3-10：SSD1351 native adapter（13 SP）

- 開工前由USER指派reference repo位置；Developer手動clone到Core repo外的暫存／指定目錄，checkout accepted SHA `5c2b6ba532a2661d5db79e27736e79890931515f`並核對manifest、header / adapter identity、license / notice與fixture config。
- clone、POC source副本及Pi build產生的binary / wheel / `.so`一律不進Core Git；不得改用fork、branch HEAD或手動複製內容。
- Python adapter 只實作既有 `DisplayDevice`；start 前驗 artifact SHA、ABI version / struct size，失敗不得 claim GPIO / SPI。
- full frame 只接受 32768-byte RGB565 MSB-first；clear 只改 back buffer，show 才 present；rotation / color 不由 Renderer 之外第二套產品 UI 決定。
- stop / repeated stop / reopen 釋放 native handle、DC/RST GPIO、SPI fd 及背景 thread；ctypes status / error mapping sanitized。
- build / install README 固定 target、system deps、header / artifact checksum、license與 clean build command；build output不提交為不明 provenance binary。

#### WP-M3-11：Portable composition / fallback（6 SP）

- 建立 M3 composition，不破壞 M1 / M2 composition fixture；graph 使用 `core.display.device → renderer → arbiter → observer` 明確相依。
- 先接mock/null與blocked-real registry seam；不得以未實作real branch宣稱完整M3 graph。GPIO無null；capability freeze / producer arm順序與Ch 5一致。
- M3 local deployment example / setup doc 使用 placeholder 與 sanitized path；真實 pins / device / artifact 不寫入 generic defaults。
- Startup / shutdown、Button、Display Blank、fallback 與 exit code 以 subprocess / call-log 串接驗證，不用單一 smoke 取代各 Test ID。

#### WP-M3-12：Real composition + Pi diagnostics（10 SP）

- Audio / Display gate各自解除後接入selected real factory；20個`rpi` nodes可分區執行Audio / Camera / GPIO / Button / Display。
- 固定並 checksum：PCM tone / speech、camera target、OLED orientation / RGB bars / state / main fixture、manual checklist version。
- 自動收集 Pi model / revision、OS / kernel、Python、pip freeze、device discovery、wiring declaration、config / artifact / fixture SHA、command start/end / exit code與 machine-readable結果。
- Display 100-frame latency保留raw samples / P50 / P95 / max；Audio另記CPU、RSS、temperature、throttling與xrun。
- USER observation 與自動 assert 分欄；人工結論不得覆寫 buffer、call order、cleanup、format或exit code失敗。

#### WP-M3-13：Regression / exact-SHA delivery（7 SP）

- 先跑27個DEV-PY311 Test ID，再跑M1 entrypoint、M2 entrypoint與完整`-m "not rpi"` suite；無新skip / xfail、無Pi-only import、無刪除先前驗收。
- Developer 的 working-tree Pi smoke 只記 `Diagnostic`。正式 cards 必須在 USER 核准 candidate commit 後，對其完整 40-character SHA 重跑。
- Tester 對同一 SHA 獨立跑全部 Pi cards；若任何修正改 code / test / authoritative doc，原 cards 失效，建立新 candidate SHA 再驗。
- evidence README 列出47 ID → pytest node → artifact path、known limits、Blocked / Fail disposition；不得包含credential、不必要個資或未索引的大型媒體。

---

### Test Spec 覆蓋與預定測試檔

| Test ID | 主責包 | 預定測試檔 |
| :--- | :--- | :--- |
| M3-HAL-001~002 | WP-M3-03；02 / 11整合 | `tests/test_m3_hal_001_002.py` |
| M3-AUD-001~004 | WP-M3-03、06、07 | `tests/test_m3_aud_001_002_003_004.py` |
| M3-DSP-001~002 | WP-M3-03 | `tests/test_m3_dsp_001_002.py` |
| M3-CAM-001 | WP-M3-03 | `tests/test_m3_cam_001.py` |
| M3-GPIO-001~002 | WP-M3-03 | `tests/test_m3_gpio_001_002.py` |
| M3-ARB-001~007 | WP-M3-05 | `tests/test_m3_arb_001_002_003_004_005_006_007.py` |
| M3-REND-001~005 | WP-M3-04 | `tests/test_m3_rend_001_002_003_004_005.py` |
| M3-SCN-001 | WP-M3-05 / 11 | `tests/test_m3_scn_001.py` |
| M3-CFG-001~002 | WP-M3-02、07 | `tests/test_m3_cfg_001_002.py` |
| M3-BTN-001~005 | WP-M3-09 / 12 | `tests/test_m3_btn_001_002_003_004_005_rpi.py` |
| M3-AUDI-001~004 | WP-M3-07 / 12 | `tests/test_m3_audi_001_002_003_004_rpi.py` |
| M3-CAMI-001~003 | WP-M3-08 / 12 | `tests/test_m3_cami_001_002_003_rpi.py` |
| M3-DSPI-001~006 | WP-M3-10 / 12 | `tests/test_m3_dspi_001_002_003_004_005_006_rpi.py` |
| M3-GPIOI-001~002 | WP-M3-09 / 12 | `tests/test_m3_gpioi_001_002_rpi.py` |
| M3-REG-001 | WP-M3-01 / 11 / 13 | `tests/test_m3_reg_001.py` |

命名保留完整 Test ID token；同檔合併只代表共享 fixture，不代表合併 acceptance criteria。每個 ID 在 manifest 中仍需至少一個直接測到 `src/sbd/` 行為的 non-empty node。

---

## 執行波次與相依順序

| 波次 | 工作包 | Exit gate |
| :--- | :--- | :--- |
| **W0 Start** | WP-M3-01 | 47-ID manifest、RPI deselection、baseline與evidence schema ready |
| **W1 Portable contracts** | WP-M3-02、03、06 | Config / null / mock / factory / fallback全綠；Audio seam無selected implementation；DEV不載Pi dependency |
| **W2 Chip-independent Display** | WP-M3-04、05 | Renderer / Arbiter / State / Blank DEV測項全綠 |
| **W3 Independent backends** | WP-M3-08、09、11 | Camera / GPIO host seams、portable composition與fallback全綠；Pi diagnostics ready |
| **W4 Gated real packages** | WP-M3-07、10 | Audio P4 final ACK；USER指派Display repo位置並完成accepted SHA checkout；兩包host contract / stub tests全綠 |
| **W5 Target-device integration** | WP-M3-12 | USER readiness完成；20 RPI nodes及manual observations對candidate SHA完成 |
| **W6 Acceptance / delivery** | WP-M3-13 | 27 DEV + 20 RPI、M1/M2/full regression、Tester PASS、Designer無Blocking |

W0~W3的可執行範圍已完成。W4的Audio gate等待P4 final ACK；Display reference已在Core repo外驗證，config→ABI gpiochip boundary已由`IR_dev_M3_I`解決。external reference repo與build outputs不進Git。

---

## 模擬與實體測試計畫

### A. DEV-PY311 模擬測試（Developer 完成，USER 不需操作）

涵蓋 27 個 Test ID：`HAL(2) + AUD(4) + DSP(2) + CAM(1) + GPIO(2) + ARB(7) + REND(5) + SCN(1) + CFG(2) + REG(1)`。

正式 gate 命令：

```bash
python -m pytest -v tests/milestones/test_m1_foundation.py
python -m pytest -v tests/milestones/test_m2_mock_pipeline.py
python -m pytest -v -m "not rpi" tests/milestones/test_m3_rpi_hal.py
python -m pytest -v -m "not rpi"
```

本機若只有 workspace venv，使用等價的 `.venv/bin/python`；host ROS 環境須以 clean venv 或 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 隔離。交付 evidence 要記錄實際 interpreter與命令，不能靜默改寫。

DEV gate 判定：

1. 24 個目前可執行的 M3 DEV Test ID 全綠，另外3個Audio P4 conditional DEV IDs明確標Blocked；47-ID manifest無空映射，不得用skip、xfail或空測試冒充通過。
2. M1 / M2 entrypoint 與完整 non-RPI suite 全綠；未刪除、skip / xfail既有測項。
3. `sounddevice`、未核准Audio Pi-only module、`picamera2`、`gpiod`、native display module / `.so` 不出現在 default import snapshot。
4. race 不用 sleep控時；結束無 task / handle / fd / waiter；log與exception不含敏感內容。

### B. USER 硬體 readiness（正式 Pi 測試前共同完成）

USER提供或現場確認，Developer將結果寫入readiness card。任何external reference repo另由USER在相關package開工前指派位置；Developer只在Core repo外手動clone exact SHA，且不加入Git：

- Raspberry Pi 5 型號 / revision、OS / kernel、Python版本、供電與可用儲存空間。
- Audio：INMP441、MAX98357A、接線 / 供電、`googlevoicehat-soundcard` overlay、`arecord -l` / `aplay -l`裝置識別與 sanitized local config。
- Camera：CSI camera型號 / revision、排線方向，device discovery可見。
- Display：Waveshare 1.5-inch SSD1351實體 revision；SPI0 CE0、DC24、RST25接線；accepted artifact / config full checksum。
- GPIO / Button：conversation button BCM / physical pin、pull-up / pull-down、short / long門檻，以及一個可安全量測的 output pin / LED+限流或邏輯分析儀。

安全規則：SPI、CSI、GPIO、I2S的接線 / 拔線一律先關機並斷電；fallback優先使用不存在的 device / artifact config觸發，不在通電時熱拔硬體。USER 未確認安全負載時不執行 output電平測試。

### C. USER-assisted Developer Pi run（diagnostic / candidate verification）

| 測試時段 | USER 動作 | Developer 動作 | Test ID | 預估現場時間* |
| :--- | :--- | :--- | :--- | ---: |
| **H0 Readiness** | 確認硬體 revision、接線、供電與允許的操作 | 收集 environment / discovery / hash，檢查衝突與 evidence path | 全體前置 | 30–60 分 |
| **H1 Audio** | 聽固定 tone / 語音；逐項回報可聽、爆音、雜訊 | 跑direct native、conversion、fallback、quality / resource / lifecycle probes | M3-AUDI-001~004 | 60–90 分 |
| **H2 Camera** | 將鏡頭對準固定 target，確認首幀非純黑 | 跑 JPEG / RGB / I420、尺寸 / decode / content及 missing-device fallback | M3-CAMI-001~003 | 30–45 分 |
| **H3 GPIO / Button** | 依提示短按、長按、在指定狀態按鍵；使用安全工具量測 output | 以 state / process / race barrier驗 callback、debounce、interrupt、recovery、shutdown / exit code | M3-GPIOI-001~002、M3-BTN-001~005 | 60–90 分 |
| **H4 Display** | 觀察 Boot / Shutdown Blank、IDLE文字、方向 / 鏡像、RGB bars、可讀性 / flicker；允許拍攝 evidence | 跑 atomic flush、fallback、reopen / cleanup、fixture checksum、100-frame latency raw samples | M3-DSPI-001~006 | 90–120 分 |
| **H5 Integrated fallback** | 僅在斷電後依卡片改線；其餘以 invalid config / device path操作 | 跑 M3 composition、capability map、process exit、reopen與完整 `-m rpi` | 20 個 RPI IDs整合 | 45–60 分 |

\* 不含驅動安裝、重新接線、硬體故障或缺件排除時間。任何時段可分開執行，各 card獨立記錄，不用一次完成。

USER 對人工感知欄位明確回覆 `Pass` / `Fail` 與觀察；Developer不得代替 USER 宣稱「可聽」「可讀」「無 flicker」。Developer根據完整自動結果與 USER觀察填寫 developer-run card；正式 acceptance仍由 Tester裁定。

### D. Candidate SHA 與 Tester 獨立驗收

1. DEV gate 與 Developer diagnostic全綠後，Developer依 workflow先展示完整 commit標題、60 words內英文 bullet body與檔案清單，取得 USER明確同意才建立 remote-verification candidate commit。
2. 取得完整 40-character SHA後，在 Pi checkout / build該 exact SHA；重新產生 environment、artifact、config、fixture hashes，不沿用 working-tree diagnostic的 Pass。
3. USER依 test card完成物理操作與人工觀察；Tester獨立執行：

```bash
python -m pytest -v -m rpi tests/milestones/test_m3_rpi_hal.py
```

4. 任一 card Fail：保留證據、依 `TR_dev_M3`修正；只複驗原 failure、直接影響與新 regression。任何 code / test / authoritative doc變更都必須產生新 candidate SHA並使舊 acceptance失效。
5. 20 個 RPI cards、27 個 DEV IDs、M1/M2 regression全數通過，Tester PASS且Designer final review無 Blocking後，才可宣稱 M3 Accepted。

---

## RPI evidence 目錄與 card 規則

正式 delivery 建議結構：

```text
docs/outsource/evidence/<delivery-id>/
├── README.md
├── environment/
│   ├── system.json
│   ├── devices.txt
│   └── packages.txt
├── checksums/
│   └── SHA256SUMS
├── cards/
│   └── M3-<DOMAIN>-<NNN>.md
├── logs/
├── results/
└── media-metadata/
```

每張 card 必須含 test ID / status、branch + exact SHA、硬體 / 接線、artifact / ABI / license、sanitized config + hash、fixture + hash、完整命令與 USER操作、預期 / 實際、開始 / 結束時間、exit code、log / raw / media metadata索引。大型照片 / 影片可放受控位置，但 repo內保留 checksum、metadata、結果摘要與可定位索引；不提交 credential或不必要個資。

---

## 主要風險與重估條件

| 風險 | 目前影響 | 緩解 / 決策 | 主責包 |
| :--- | :--- | :--- | :--- |
| Audio P4尚未回交final selection | WP-M3-07不能開工；Audio conditional DEV IDs與Pi cards不能Pass | 僅做schema / fake seam；等待full SHA、P4-A01~A10及Designer final ACK | WP-M3-06、07、12、13 |
| USER尚未指派Display reference repo位置 | WP-M3-10不能checkout accepted SHA、驗manifest或build | 開工前由USER指派；Developer在Core repo外手動clone exact SHA；clone與產物不進Git | WP-M3-10、12、13 |
| `rpi`預設目前以skip處理 | 違反portable collection規則 | WP-M3-01改成deselect + count，manifest禁止skip/xfail | WP-M3-01 |
| Pi-only套件或native load污染DEV suite | 開發機collection / startup失敗 | optional/system dependency文件化、factory lazy import、subprocess sys.modules guard | WP-M3-02、03、07~10 |
| ALSA I/O、gpiod fd或ctypes owner跨thread | race、event-loop block、cleanup不完整 | heartbeat、明確owner / barrier、reopen與fd / task / thread檢查 | WP-M3-07、09、10 |
| camera stride / YUV layout與宣告格式不同 | 長度綠燈但內容錯誤 | 明確plane / stride轉換，decode / length / nonzero三重assert | WP-M3-08 |
| 人工結果取代程式assert | 假綠燈 | USER checklist只補可聽 / 可讀 / flicker；自動失敗不可被人工Pass覆寫 | WP-M3-12、13 |
| USER硬體或時段不可用 | RPI cards保持Pending / Blocked | 先完成W0~W3；Pi分成H0~H5可重複時段，缺件不改skip | WP-M3-08~13 |

以下情況需更新估點並記錄原因，不在 code內自行改契約：

1. 任一 public API、ABI、PCM、pixel、GPIO ownership或lifecycle需偏離已核准文件。
2. 任一工作包新增超過 2 SP，或出現未列出的跨包相依 / system service / kernel module工作。
3. Accepted Display artifact不是可直接包裝的 ABI v1，或缺license / target compatibility。
4. P4 selected implementation無法滿足quality、exact framing、async lifecycle或resource evidence；須先由Designer重新disposition。
5. 實體硬體 revision、接線或driver版本與selected baseline不同，造成test fixture不等價。

---

## M3 共同 Definition of Done

1. 47 個 Test ID全部映射至pytest node與evidence；27 DEV IDs及20 RPI cards全通過，無Pending / Blocked / skip / xfail。
2. 測試含直接、真實assert且觸及產品實作；manifest、mock call-log、manual checklist或process smoke都不單獨冒充功能通過。
3. M1 / M2 entrypoint與完整suite維持通過；default DEV collection不import Pi-only dependency。
4. Audio / Display / Camera / GPIO lifecycle可stop / reopen，結束無task、stream、native handle、GPIO claim、SPI fd或thread殘留。
5. Fallback / capability / logging / exit code與Ch 5 / Ch 11一致；log、exception、config、evidence不洩漏credential、原始音訊 / 影像或不必要個資。
6. 正式evidence對同一完整implementation SHA，含environment、artifact / config / fixture checksum、命令、實際結果與USER人工觀察。
7. Tester對exact SHA獨立簽核PASS；Designer final code/test review無Blocking。任何後續產品變更須重新判定受影響cards。
