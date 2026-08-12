# test_spec_M3.md ── M3 Raspberry Pi HAL 與硬體 bring-up

本文件為 `docs/test_spec.md`（總論）的子檔。Test ID 格式、判定規則、平台代碼、共用 fixture 與證據代碼定義於總論；本文件只列 M3 範圍的測項與驗收命令。

---

## 1. M3 範圍說明

- 覆蓋 `milestones/M3.md` 的 M3「Raspberry Pi HAL 與硬體 bring-up」。
- 測項分為兩類平台：
  - **DEV-PY311**：開發機純 Python 測試，驗證 null/mock 契約、factory lazy import、Display 仲裁層邏輯、Display profile renderer、config schema。不得 import Pi-only library。
  - **RPI-NATIVE**：`rpi` marker，僅在 Raspberry Pi 5 上執行，驗證 real backend 啟動、HAL 工作方法與 null fallback；Pi-only dependency 明確標記。
- **M3 的 Pass 以前序 M1 / M2 全部 regression 仍通過為必要條件。**
- milestone entrypoint：`tests/milestones/test_m3_rpi_hal.py`（含 `rpi` 測項）；純軟體聚焦測試可分散於 `tests/` 但須能透過 entrypoint 集中重現。

---

## 2. M3 需求──測試對照

### 2.1 HAL Factory 與 lazy import（開發機可跑）

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-HAL-001** | Ch 2a §2a.1 Factory 模式；`milestones/M3.md` §5.1 | factory top-level import 引入 Pi-only 套件，使開發機無法啟動 | `FX-MOCK-HAL`；分別以 `driver=null`、`driver=mock` config 呼叫各 HAL factory；監看 sys.modules diff | `sounddevice`、`picamera2`、`gpiod` 及 native display `.so` 均不出現在 sys.modules；factory 只 lazy import 被選中的 backend；null/mock 建立成功 | `DEV-PY311` / `EV-AUTO` / M3 startup |
| **M3-HAL-002** | Ch 2a §2a.1 Null Object 契約、Factory 失敗與 RM Fallback | real backend start 失敗時 RM 自動換注 null；null start 仍失敗則 fatal | 以 `FX-RM-GRAPH` 模擬 real audio/display/camera start raise → null start OK；另模擬 null start 亦 raise | audio/display/camera real→null 各自 fallback；`capability_map["audio"]` / `"display"` / `"camera"` = `False`；log WARNING；null start 失敗 → fatal log + 啟動中止；GPIO start 失敗不建立 NullGPIO，`capability_of("gpio")=False` | `DEV-PY311` / `EV-AUTO`、`call log` / RM graph |

### 2.2 Audio HAL — Null / Mock 契約

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-AUD-001** | Ch 2a §2a.2 Null 實作行為；`milestone` §5.4 | null frame 格式錯誤，或 iterator 獨佔未正確拒絕第二次呼叫 | `FX-MOCK-HAL`；`NullAudioInput` start→frames → 消費數幀 → aclose；再 frames（重開）；同 instance active 時再 frames | frame bytes 長度 = `sample_rate * frame_duration_ms // 1000 * channels * (bit_depth // 8)`；每幀全 `\x00`；stop 冪等；aclose 後重開成功且無殘留 task；active 時第二個 frames 回 `RuntimeError("AudioInput already streaming")` | `DEV-PY311` / `EV-AUTO`、`EV-RACE` / Listen cancel |
| **M3-AUD-002** | Ch 2a §2a.2 Null 實作行為 | NullAudioOutput play 未完整消費 iterator，或 stop 非冪等 | `NullAudioOutput` start→play(固定 5 幀 mock pcm iterator) → stop → stop | play 完整消費所有幀後 return；stop 冪等不 raise | `DEV-PY311` / `EV-AUTO` / Speak worker |

### 2.3 Display HAL — Null / Mock 契約

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-DSP-001** | Ch 2a §2a.3 Null 實作；Ch 8 §7 NullDisplay size (0,0) 行為 | NullDisplay 拋 exception 或 size 非 (0,0)，破壞 arbiter render skip | `NullDisplay` start→clear/write_pixels/show（無 buf 驗證）；size() | lifecycle no-op；clear/write_pixels/show 皆 no-op 不 raise；size() return `(0, 0)` | `DEV-PY311` / `EV-AUTO` / arbiter |
| **M3-DSP-002** | Ch 2a §2a.3；driver write_pixels buf length 驗證 | 非法長度 buf 被接受，chip 收到破碎資料 | mock display driver 以正確/錯誤長度呼叫 write_pixels | 長度符合 panel buffer size → 無 raise；長度不符 → `ValueError` | `DEV-PY311` / `EV-AUTO` / display pipeline |

### 2.4 Camera HAL — Null / Mock 契約

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-CAM-001** | Ch 2a §2a.4 Null 實作行為；`milestones/M3.md` §5.4 | null camera 回非法格式 bytes，使下游 decoder raise | `NullCamera` 依 config 分別以 `format=RGB`、`YUV`、`JPEG` 各呼叫 capture() | RGB：length = `width*height*3` 全零；YUV I420：length = `width*height*3//2`；JPEG：合法 JPEG encoded bytes 可被標準 JPEG decoder 解析（非全零）；三種格式均不 raise | `DEV-PY311` / `EV-AUTO` / Look worker |

### 2.5 GPIO HAL — Mock 契約

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-GPIO-001** | Ch 2a §2a.5；`milestones/M3.md` §5.4 | 一 pin 多訂閱者被接受、debounce 未執行、callback 不隔離 | `FX-MOCK-HAL` `MockGPIO`；register pin 5 兩次（第二次應拒絕）；register pin 6 帶 debounce=50ms 後快速連發兩事件（間隔＜50ms）；callback raise RuntimeError | 第二次 register 同 pin → `ValueError`；快速連發第二事件被吞（callback 只觸發一次）；callback raise 不影響 pin 6 以外的事件繼續派發；unregister 未註冊 pin 為 no-op（冪等） | `DEV-PY311` / `EV-AUTO`、`EV-RACE` / button |
| **M3-GPIO-002** | Ch 2a §2a.5 configure_output / set_output；arch.md §5.4 | output pin 未 configure 即 set，或重複 configure | `MockGPIO`；configure_output pin 10 initial=False；set_output pin 10 True；重複 configure pin 10；另 set_output pin 20（未 configure） | configure 成功；set_output pin 10 成功且電平更新；重複 configure 同 pin → `ValueError`；set_output 未 configure pin → `ValueError` | `DEV-PY311` / `EV-AUTO` / GPIO output |

### 2.6 Display 仲裁層（純軟體）

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-ARB-001** | Ch 8 §5.1–§5.2；§7 atomic flush | status/main 每次更新只呼叫一組 clear/write/show；fullscreen active 期間 status/main 更新不 render | `MockDisplay` 紀錄 call order；write_status_slot("state") + write_main("text")；再 request_fullscreen("owner_a") 後 write_main("during_full") | 每次常規更新恰好一組 clear→write→show；fullscreen active 時 write_main 不觸發 show；DisplayDevice.write_pixels 只在 show 前才呼叫 | `DEV-PY311` / `EV-AUTO`、`EV-RACE` / display pipeline |
| **M3-ARB-002** | Ch 8 §5.3–§5.4；§10 tests 2–8 | 不同 owner 搶 fullscreen 未被拒、非 owner release 清除 fullscreen | owner_a request → owner_b request → owner_a release；owner_b 再 request；同 owner 重複 request | owner_b 搶佔時 return False；owner_a release 後 model 回常規且一次 render；owner_b 重新 request 回 True；同 owner 重複 request 更新 hint 並回 True | `DEV-PY311` / `EV-AUTO` / display pipeline |
| **M3-ARB-003** | Ch 8 §7；§10 test 9 | NullDisplay size (0,0) 時 arbiter 仍執行 renderer，或 ownership 規則失效 | `NullDisplay` 注入 arbiter；write_status_slot / request_fullscreen / release_fullscreen 操作 | size (0,0) 時 renderer 不被呼叫（arbiter 直接 return）；ownership 規則仍成立（release 非 owner 為 no-op、相同 owner 重複 request 回 True） | `DEV-PY311` / `EV-AUTO` / null device |
| **M3-ARB-004** | Ch 8 §8 runtime degradation；§10 tests 12–13 | renderer 或 HAL runtime failure 後繼續 render 或 publish ErrorOccurred | `MockDisplay.show()` 第一次 raise；後續 write_main | 第一次 raise 後 `_rendering_enabled=False` latch；後續 write_main 更新 backing model 但 show 不再呼叫；不 publish `ErrorOccurred`；不進 SM ERROR | `DEV-PY311` / `EV-AUTO`、`EV-LOG` / error policy |
| **M3-ARB-005** | Ch 8 §9 lifecycle；§10 test 13 | stop 後 observer 仍 write 觸發 fatal；或 stop 呼叫 device.stop() 造成雙重停止 | arbiter start→write 正常→stop→stop；stop 後 write_main（delayed observer） | stop 後 write 為 no-op + DEBUG；stop 不呼叫 device.stop()；重複 stop 冪等不 raise | `DEV-PY311` / `EV-AUTO` / reverse stop |
| **M3-ARB-006** | Ch 8 §6 slot registry；§5.1；display_spec.md §3.3 state slot | unknown slot raise UnknownDisplaySlot；State owner startup seed IDLE 不發布虛構事件 | write_status_slot("nonexistent_slot") → 期望 raise；arbiter start 後 state slot 值確認 | `UnknownDisplaySlot` raise；state slot 初始值為 IDLE mapping ("待命")；StatusBar start 不 publish 任何 Event | `DEV-PY311` / `EV-AUTO`、`EV-LOG` / display profile |
| **M3-ARB-007** | Ch 8 §10 test 14；ch8-Q9 | native thread 直接呼叫 arbiter 未被 thread-affinity guard 拒絕 | 從非 event-loop thread 直接呼叫 write_status_slot | thread-affinity guard 拒絕並 raise（`RuntimeError` 或等效錯誤） | `DEV-PY311` / `EV-AUTO` / threading |

### 2.7 Display Renderer 與 selected profile（純軟體）

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-REND-001** | Ch 8 §4 renderer 契約；display_spec.md §2–§3；`milestones/M3.md` §5.1 | renderer 回錯誤 buffer 長度或未知 template | 以各 required template（`status.text`、`status.state`、`main.text`、`main.error`、`fullscreen.blank`）呼叫 render；另以 unknown template 呼叫 validate | render 回 bytes 長度 = panel buffer size（128×128 for SSD1351 profile）；validate 未知 template/欄位 → `DisplayHintError`；size (0,0) 時 arbiter 不呼叫 renderer | `DEV-PY311` / `EV-AUTO` / display pipeline |
| **M3-REND-002** | display_spec.md §2.2 typography；§3.3 state 文案 | 狀態文案錯誤、字型未離線隨附、或 missing glyph 使整個 render 失敗 | 以 `status.state` template 依序注入六種 state；以含不支援字元的 main.text 呼叫 render | IDLE→"待命" / WAKE→"準備中" / PERCEPTION→"接收中" / THINK→"思考中" / ACTION→"回應中" / ERROR→"錯誤"；不支援字元逐一替換為 `□`，render 不 raise；Noto Sans TC 字型從 assets/ 離線載入，不依賴系統字型 | `DEV-PY311` / `EV-AUTO`、`EV-REVIEW` / display spec |
| **M3-REND-003** | display_spec.md §2.1 layout tokens；§3.2 CMP-BLANK；§4.1 SCN-BOOT / SCN-SHUTDOWN | Fullscreen Blank 非全黑、startup/shutdown 未使用 Blank | render `fullscreen.blank` hint；bitmap 檢查 | render 產出全黑 frame（128×128 全零或 RGB565 等效）；`main.progress` template 存在於 registry 但 renderer 接受後不產生非空產品可見內容（技術預留） | `DEV-PY311` / `EV-AUTO` / SCN-BOOT / SCN-SHUTDOWN |
| **M3-REND-004** | display_spec.md §2.2 text wrap / overflow | 超長文字 overflow 未截斷、省略符號使用錯誤字型 | 超出 Main 5 行上限的長文字注入 `main.text`；空白 / sanitization 後空字串 | 超出高度 deterministic 截斷，最後一行保留足夠寬度顯示 `…`（FONT-UI-REGULAR）；空字串 / 全空白 → clear Main（不保留上一筆、不顯示 placeholder） | `DEV-PY311` / `EV-AUTO` / content policy |
| **M3-REND-005** | display_spec.md §2.3 asset inventory；font SHA-256 | 字型檔 SHA 不符，或使用未授權版本 | 讀取 `NotoSansTC-Regular.otf` 與 `NotoSansTC-Medium.otf` 並計算 SHA-256 | Regular SHA-256 = `5bab0cb3c1cf89dde07c4a95a4054b195afbcfe784d69d75c340780712237537`；Medium SHA-256 = `bf206dca0975779bac71cb49a037a364156ca98a0c431b1b7d6b29fb8952ac7e` | `DEV-PY311` / `EV-AUTO` / asset |

### 2.8 Display Scenario lifecycle（純軟體）

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-SCN-001** | display_spec.md §4.1 SCN-BOOT / SCN-SHUTDOWN；§4.2 fullscreen model rule 4 | Boot / Shutdown Fullscreen owner 未在 finally release，阻塞後續 Display 操作 | `FX-MOCK-APP`；模擬 app lifecycle boot owner request_fullscreen(blank)→建立 Normal model 後 release；另模擬 shutdown request → process stop 期間維持；NullDisplay 情況下 boot 仍 release | Boot owner release 後 arbiter 渲染最新 Normal model；Shutdown owner 維持至 Display stop；NullDisplay / failure 情況下 release 仍必須被呼叫（finally）；`capability_of("display")=False` 不改變主流程 exit code | `DEV-PY311` / `EV-AUTO`、`EV-RACE` / lifecycle |
| **M3-SCN-002** | display_spec.md §4.1 SCN-STATE / SCN-PERCEPTION / SCN-INTERRUPT | SCN-PERCEPTION new turn 未先 clear 舊 Main；SCN-INTERRUPT 未在回 IDLE 後 clear | `FX-MOCK-APP`；StateChanged PERCEPTION 觸發；第二 turn StateChanged PERCEPTION 前先確認 clear 呼叫；後觸發 InterruptRequested → verify Main 顯示「已中止」→ 回 IDLE 後確認 clear | 每次 `StateChanged.new=PERCEPTION` 先 `write_main(None)` 清除上一輪；interrupt 期間 Main="已中止"；真正回 IDLE 後 write_main(None) clear | `DEV-PY311` / `EV-AUTO` / SCN matrix |
| **M3-SCN-003** | display_spec.md §5.2 SET-SHOW-SESSION-CONTENT；§5.1 content policy | session content setting 影響 State/Error/Blank，或支援 runtime reload | 以 `SET-SHOW-SESSION-CONTENT=False` 啟動；觸發 PERCEPTION / ACTION-SPEAK；另觸發 SCN-ERROR | Perception / Speak 內容不寫入 Main；State / Error / Blank 不受 setting 影響；setting 在 process 啟動時生效，runtime 修改不生效；session / audio / exit code 不受影響 | `DEV-PY311` / `EV-AUTO` / content setting |

### 2.9 GPIO Button 語意（Pi 硬體）

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-BTN-001** | `milestones/M3.md` §5.4 Button 語意；Ch 2a §2a.5；Ch 4 SM | 短按 IDLE 未產生 WAKE；短按進行中 session 未產生 InterruptRequested | Pi 實體對話按鈕 pin；短按（`short_press_min_ms` ≤ `duration_ms` < `long_press_min_ms`）於 IDLE | `ButtonPressed` Signal 產生；SM 轉 IDLE→WAKE→PERCEPTION (listen)；無殘留 task | `RPI-NATIVE` (rpi marker) / `EV-PROC`、`EV-RACE` / SM session |
| **M3-BTN-002** | `milestones/M3.md` §5.4 Button 語意 | 短按進行中 session 未觸發 InterruptRequested | PERCEPTION / THINK / ACTION 進行中時短按 | `InterruptRequested` 行為觸發；session 收斂後回 IDLE | `RPI-NATIVE` / `EV-RACE` / interrupt |
| **M3-BTN-003** | `milestones/M3.md` §5.4 Button 語意 | 長按未觸發 graceful shutdown，或 exit code 非 0 | 任意狀態下長按（`duration_ms` ≥ `long_press_min_ms`）| `ShutdownRequested` Signal；App graceful shutdown；exit code 0 | `RPI-NATIVE` / `EV-PROC` / shutdown |
| **M3-BTN-004** | `milestones/M3.md` §5.4 Button 語意 | ERROR 狀態短按未直接進 WAKE | recovery 完成（或無 recovery）後的 ERROR 狀態短按 | 短按後直接 WAKE，開始新 session（不需先回 IDLE） | `RPI-NATIVE` / `EV-PROC` / SM ERROR |

### 2.10 Audio Real Backend（Pi 硬體）

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-AUDI-001** | `milestones/M3.md` §5.4 Pi 驗收 item 1；Ch 2a §2a.2 PCM 格式；DELIVERY-AUDIO-POC-M3-ACK-001 | real ALSA backend frame 格式或 timeout 不符，或 output 未完整消費 | Pi ALSA config（I2S INMP441、googlevoicehat-soundcard）；AudioInput start → frames timeout N 幀 → aclose；AudioOutput start → play(固定 PCM fixture) | AudioInput：在 timeout 內產出幀數 ≥ N；每幀 bytes 長度 = `16000 * 20 // 1000 * 1 * 2`（16kHz mono 16-bit 20ms）；AudioOutput：完整消費所有幀，無 PCM 截斷 | `RPI-NATIVE` / `EV-PROC` / audio pipeline |
| **M3-AUDI-002** | Ch 2a §2a.1 real→null fallback；`milestones/M3.md` §5.4 fallback | 不存在的 ALSA device 未觸發 null fallback | 以不存在的 ALSA card 名稱啟動 | real start raise → null fallback 啟動；`capability_of("audio")=False`；log WARNING 含 device name；App 繼續執行（不 fatal） | `RPI-NATIVE` / `EV-PROC`、`EV-LOG` / fallback |

### 2.11 Camera Real Backend（Pi 硬體）

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-CAMI-001** | `milestones/M3.md` §5.4 Pi 驗收 item 3；Ch 2a §2a.4 | picamera2 backend capture 格式/尺寸不符 | Pi CSI camera；以 config `format=JPEG`、`width=640`、`height=480` 呼叫 capture() | 回合法 JPEG bytes（可 decode）；不 raise；尺寸符合 config | `RPI-NATIVE` / `EV-PROC` / camera |
| **M3-CAMI-002** | Ch 2a §2a.1 null fallback；`milestones/M3.md` §5.4 | CSI 未接線時未 fallback null，Look worker 爆 | 不存在 CSI camera 時啟動 | camera real→null fallback；`capability_of("camera")=False`；log WARNING；App 繼續 | `RPI-NATIVE` / `EV-PROC`、`EV-LOG` / fallback |

### 2.12 Display Real Backend（Pi 硬體，含 selected profile）

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-DSPI-001** | `milestones/M3.md` §5.4 Pi 驗收 item 4–5；Ch 8 §7 atomic flush；display_spec.md §1.2 SSD1351 | real SSD1351 driver 一次 intent 觸發多組 clear/write/show | Pi SSD1351 display；一次 write_main intent | call log：恰好一組 clear→write_pixels→show；無多餘 flush | `RPI-NATIVE` / `EV-PROC` / display atomic |
| **M3-DSPI-002** | display_spec.md §4.1 SCN-BOOT SCN-SHUTDOWN；`milestones/M3.md` §5.4 | startup/shutdown Fullscreen Blank 未執行或未 release | Pi 啟動→進入 IDLE→shutdown | Boot：OLED 顯示全黑（人工確認）；SCN-STATE IDLE "待命" 文案可讀（人工確認）；Shutdown：全黑維持至 Display stop；hardware 型號、config hash、測試時間、pass/fail 記錄於 `docs/outsource/evidence/` | `RPI-NATIVE` / `EV-PROC`、人工 checklist / lifecycle |
| **M3-DSPI-003** | Ch 2a §2a.3；`milestones/M3.md` §5.4 fallback；display_spec.md §5.3 | display device 不存在時 fatal 或 session 中斷 | SPI/driver 不存在或 .so 未編譯時啟動 | real→null fallback；`capability_of("display")=False`；主流程繼續；exit code 不因 display failure 改變 | `RPI-NATIVE` / `EV-PROC`、`EV-LOG` / fallback |

### 2.13 GPIO Real Backend（Pi 硬體）

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-GPIOI-001** | `milestones/M3.md` §5.4 Pi 驗收 item 2；Ch 2a §2a.5 gpiod backend | gpiod register/debounce/unregister/output 在指定 pin 不可重複 | Pi 指定測試 pin；register→simulate rising edge→callback 確認→debounce 快速連發→unregister→unregister（冪等）；configure_output→set_output | callback 恰觸發一次（debounce 吞第二次）；callback 內 edge 與 at 欄位正確；unregister 後不再觸發；重複 unregister no-op；output 電平可量測 | `RPI-NATIVE` / `EV-PROC`、`EV-RACE` / GPIO |
| **M3-GPIOI-002** | Ch 2a §2a.5；`milestones/M3.md` §5.4 | GPIO start 失敗時建立 NullGPIO，未正確記 capability=False | libgpiod 不可用或 pin conflict 時 | GPIO start raise → 不建立 NullGPIO；RM 記 `capability_of("gpio")=False`；下游 input_events 不啟動；log WARNING | `RPI-NATIVE` / `EV-PROC`、`EV-LOG` / GPIO fallback |

### 2.14 Config M3 schema（開發機）

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-CFG-001** | Ch 10；`milestones/M3.md` §5.2 Pi local config 範例 | Pi config 範例含 real pin / ALSA / credential，或 merge 後啟動失敗 | `FX-CONFIG`；載入含 display.driver=`ssd1351`、audio.driver=`alsa`、gpio.driver=`gpiod` 的 local YAML（pin / ALSA card 使用 placeholder）；strict merge 後建構 AppConfig | strict merge 成功，unknown key → `ConfigValueError`；`SecretValue` repr / str 不洩漏原值；Pi-only backend 名稱可被 config schema 接受；`config.example.yaml` 通過 validation | `DEV-PY311` / `EV-AUTO` / config |

### 2.15 Regression 與共同完成條件

| Test ID | 權威來源 | 風險 | 前置條件 / 刺激 | 可觀察結果 | 平台 / 證據 / 回歸 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M3-REG-001** | `milestone.md` §1.4；`milestones/M3.md` §5.1 | M3 新增 HAL/Display 修改破壞 M1/M2 | 依序執行 M1 entrypoint、M2 entrypoint、M3 純軟體聚焦測試、完整 `python -m pytest -v` | 四者全通過；M1/M2 驗收未刪除 / skip / xfail；Pi-only import 不出現在 DEV-PY311 suite；race case 無 sleep 同步；log hygiene 仍成立 | `DEV-PY311` / `EV-AUTO` / M3 共同 gate |

---

## 3. 驗收命令

```bash
# 開發機：純軟體 + M1/M2 regression
python -m pytest -v tests/milestones/test_m1_foundation.py
python -m pytest -v tests/milestones/test_m2_mock_pipeline.py
python -m pytest -v tests/milestones/test_m3_rpi_hal.py -k "not rpi"
python -m pytest -v

# Raspberry Pi 5：硬體整合（需已確認 pin 接線、ALSA device、CSI camera）
python -m pytest -v -m rpi tests/milestones/test_m3_rpi_hal.py
```

Pi 驗收時需在 `docs/outsource/evidence/` 記錄：硬體型號、接線 config hash、Python 版本、測試時間與各測項 pass/fail。人工觀察（喇叭、OLED）使用固定 fixture 與 checklist，結果記入同目錄；人工結果不取代可自動檢查的 buffer / 呼叫順序斷言。

M3 Pass 需同時滿足：
1. 開發機 `python -m pytest -v` 全通過（含 M1 / M2 regression）。
2. Pi 上 `python -m pytest -v -m rpi tests/milestones/test_m3_rpi_hal.py` 全通過。
3. Pi 人工 checklist 完成（SCN-BOOT / SCN-SHUTDOWN Blank、SCN-STATE 可讀）。
4. 不得刪除、skip 或 xfail 先前 M1 / M2 驗收。
