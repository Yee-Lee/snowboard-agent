---
requestor: "Designer"
owner: "Developer"
status: "Resolved"
---

# CR_M3_I — M3 最終 Code/Test Review

## 審查結論

**判定：REJECTED，M3 目前不可 close。**

現行 portable suite 與 M1/M2 regression 均通過，但 target-device 驗收存在 exact-SHA 不成立、Test ID 與實際刺激不對應、硬體卡未覆蓋已簽核 acceptance criteria、正式 evidence bundle 缺欄位，以及 Audio cancellation / playback 完整性缺少保護等 Blocking 偏離。這些屬 workflow 定義的假綠燈與高回歸風險，不是風格或可選重構。

審查基準：

- Code HEAD：`fe9c418d4822bcc0cc30494360681ed434a8e6c1`
- 20 份 RPI JSON 所宣告的 implementation SHA：`bae36dcb2684a14a129be1e90f3533451d280820`
- 權威契約：`docs/milestones/M3.md`、`docs/test_spec/test_spec_M3.md`、Ch 2a、Ch 8、Ch 10、`docs/display_spec.md`
- 審查範圍：M3 code、tests、review / delivery 文件與 `docs/outsource/evidence/DELIVERY-M3-HARDWARE-VALIDATION-001/`

## Blocking findings

### CR-M3-001 — Tester PASS 與硬體 evidence 不對應可重現的 exact SHA

- **契約依據**：M3 §5.2.1「M3 delivery SHA 前」；M3 test spec §3 Product revision；Ch 2a §2a.2 Acceptance boundary；`dev_progress_M3.md` Definition of Done 6–7。
- **可驗證證據 / 最小重現**：20 份 `results/*.json` 全部宣告 `bae36dcb...`；目前 code HEAD 是 `fe9c418...`。後一提交修改 `renderer.py`、`gpiod/driver.py` 與 RPI milestone gate，表示被審程式已不同。`tests/rpi_support.py:56-59` 只執行 `git rev-parse HEAD`，未拒絕 dirty worktree，因此可在未提交修正上跑卡片，卻把父提交 SHA 寫入 evidence。`milestone_progress.md` 引用的 `M3_tester_review.md` 不存在於 repo。
- **預期 / 實際**：預期 Tester 在乾淨、固定的單一 candidate SHA 上獨立執行並提交可定位 PASS；實際 evidence 無法證明執行內容等於所宣告 SHA，也無 Tester 報告可核對命令、結果與 Advisory。
- **影響**：現有 `20/20 PASS` 與 `Tester PASS` 無法作為 M3 acceptance 證據；後續修正也會再次改變 candidate SHA。
- **建議修正方向**：evidence runner 在執行前驗證 worktree 對受測檔案乾淨，記錄 branch、完整 HEAD 與必要 artifact identity；Developer 完成所有 CR 修正後建立單一 candidate，再由 Tester 對該 exact SHA 獨立重跑。
- **最低驗收條件**：所有 DEV / RPI 結果與 Tester 報告指向同一個包含最終修正的 40-character SHA；執行時受測工作樹乾淨；repo 內有 Tester 簽核文件，列出平台、完整命令、0 Fail / 0 Blocked / 0 Skip / 0 XFail、各 Test ID disposition 與 evidence index。

### CR-M3-002 — Test ID traceability 以節點名稱冒充契約覆蓋

- **契約依據**：Developer role「測試腳本命名必須嚴格對應測項編號」；M3 test spec §2.11、§2.13；workflow 的假綠燈禁制。
- **可驗證證據 / 最小重現**：
  - `M3-CAMI-002` 規格是 missing CSI → RM null fallback / capability false / WARNING / App 繼續，但 `test_m3_cami_002()` 實際測 RGB / YUV；規格的 RGB / YUV 是 `M3-CAMI-003`，兩者內容互換。
  - `M3-GPIOI-001` 規格要求 debounce、unregister、重複 unregister、output；實際只等待單一 edge 後 stop。
  - `M3-GPIOI-002` 規格要求 GPIO start failure、不得建立 NullGPIO、capability false、下游 input 不啟動與 WARNING；實際測正常 output 並讀一個 manual PASS 環境變數。
  - `tests/m3_manifest.py` 只因節點存在就將上述 ID 標為 `Implemented`，milestone gate 未驗證節點內涵。
- **預期 / 實際**：預期每個 ID 的刺激與 assert 對應同名 acceptance criteria；實際 node name / manifest 狀態為綠，但測到的是另一行為或局部 smoke。
- **影響**：Camera fallback、GPIO debounce / cleanup / failure policy 沒有被相應 Test ID 驗收，47/47 統計失真。
- **建議修正方向**：重新對齊 node 與 Test ID；可交換 Camera test body 或正確改名，GPIO 則補齊規格指定的完整行為。manifest 只在有效 product assertions 存在後標 Implemented。
- **最低驗收條件**：`M3-CAMI-002/003` 與 `M3-GPIOI-001/002` 各自直接覆蓋規格列出的刺激和可觀察結果；fallback 案例經 ResourceManager / composition 觀察 capability、log 與下游行為；不得以自行建立 Null object 或手動字串代替。

### CR-M3-003 — Audio、Button、Display RPI cards 未執行已簽核的整合行為

- **契約依據**：M3 test spec §2.9–§2.10、§2.12；M3 §5.4；Ch 2a §2a.2 acceptance boundary；Ch 8 §7 / §9。
- **可驗證證據 / 最小重現**：
  - `M3-AUDI-002` 在 real start raise 後自行建立 `NullAudioInput`，未走 RM fallback，也未 assert capability、WARNING 或 App continue。
  - `M3-AUDI-003` 沒有呼叫 `AudioOutput.play()` 或固定 PCM fixture，只接受預先設定的 `SBD_M3_MANUAL_* = PASS`。
  - `M3-AUDI-004` 只讀 3×100 frames 與重開；未驗 deterministic quality、xrun、cancel、read failure、CPU / RSS / temperature / throttling、device owner 或 first-frame state reset。
  - `M3-BTN-001/003` 只驗 signal；未驗 SM session transition、graceful shutdown 與 exit code。`M3-BTN-002/004/005` 只有 manual PASS 與 expected 描述，沒有實際事件 / state trace。
  - `M3-DSPI-001` 直接呼叫 `clear/write/show`，沒有以 arbiter `write_main` 驗證一次 intent 一組 flush；`M3-DSPI-002/005` 沒有執行 boot / state / shutdown 或 render orientation fixture；`M3-DSPI-003` 自行建立 NullDisplay；`M3-DSPI-004` 未檢查 handle、GPIO claim、SPI fd 或 thread cleanup。
- **預期 / 實際**：預期 manual observation 只補充可聽 / 可讀 / flicker，程式 assert 仍驗證 buffer、ownership、fallback、lifecycle 與 state flow；實際多張卡只驗局部 HAL smoke 或接受人工旗標。
- **影響**：Audio adaptation / cleanup、Button product semantics、Display atomic ownership / fallback / cleanup 仍可能偏離設計，但現有 gate 會報 PASS。
- **建議修正方向**：以最小 composition / ResourceManager graph 執行實際產品路徑；人工卡先由測試呈現固定 fixture，再記錄觀察，不能只讀 PASS。相近案例可 table-driven 或共用 fixture，不要求每個 finding 新增獨立 test function。
- **最低驗收條件**：上述每一個 RPI ID 均具有直接、真實 assert，完整覆蓋 test spec 的可觀察結果；fallback 經 RM、Button 經 bus + SM / app lifecycle、Display 經 arbiter / lifecycle owner、Audio 具 quality / resource / cancel / read-failure / owner evidence；人工 PASS 不覆蓋自動失敗。

### CR-M3-004 — 正式 hardware evidence bundle 不符合 EV-RPI / card schema

- **契約依據**：`docs/test_spec.md` EV-RPI；M3 test spec §3；`M3-developer-template/README.md` 與 `CARD_TEMPLATE.md`。
- **可驗證證據 / 最小重現**：`DELIVERY-M3-HARDWARE-VALIDATION-001/` 只有 `results/*.json`。沒有 delivery README / manifest、environment system snapshot、devices / packages、checksums、20 張 cards、logs 或 media-metadata index。20 個 JSON 均缺 `status`；普遍缺 branch、硬體 / 接線、artifact path / SHA / ABI / license、fixture SHA、完整命令 / 操作、預期 / 實際、開始 / 結束、exit code與 artifact path。manual JSON 只含 `manual: PASS`。
- **預期 / 實際**：預期每個 RPI ID 都有完整可重現卡片與索引；實際 JSON 只能證明測試 helper 寫出摘要，無法重建環境或核對 artifact / 人工觀察。
- **影響**：即使重新跑出綠燈，也無法稽核是否使用 selected hardware、artifact、config 與 fixture，亦無法追溯原始量測。
- **建議修正方向**：依已存在的 template 建立 delivery-specific bundle；大型媒體可留在受控位置，但 repo 內保留 checksum、metadata、摘要與 locator。
- **最低驗收條件**：20 張卡全部具 §3 必填欄位且 status 明確；environment / device / package / checksum / log / result / media index 可由 delivery README 導航；raw latency、manual checklist、artifact / config / fixture identity 可定位且不含 credential 或不必要個資。

### CR-M3-005 — Audio cancellation 與 playback 完整消費沒有契約保護

- **契約依據**：Ch 2a §2a.2 Acceptance boundary；M3 §5.4 Audio cancel / stop / reopen；`M3-AUDI-001`、`M3-AUDI-004`。
- **可驗證證據 / 最小重現**：`AlsaAudioInput._next_frame()` 只捕捉 `Exception`；Python 3.11+ 的 `asyncio.CancelledError` 不在此分支，取消 `anext(stream)` 後 `_active` 不會由 `_release()` 清除，後續 `frames()` 可得到 `AudioInput already streaming`。現有 `test_m3_aud_004` 只測 `aclose()`，沒有 cancel / read-failure 列。`AlsaAudioOutput._write_worker()` 只拒絕負回傳；positive partial write 不會重試或報錯，與「完整消費、無截斷」不一致。
- **預期 / 實際**：預期 cancel / read failure 後 source、resampler、partial frame 與 active owner 均重置，playback 完整寫入或明確失敗；實際 cancellation 可留下 active stream，partial write 可被視為成功。
- **影響**：session cancel 後 AudioInput 可能無法重開，AudioOutput 可能截斷；兩者都屬 M3 lifecycle / data integrity 風險。
- **建議修正方向**：讓 stream termination 在 cancellation / read failure 路徑可靠 release，並依 selected ALSA binding 的 write 回傳語意處理完整消費或明確短寫失敗；不要限制唯一實作方式。
- **最低驗收條件**：自動 regression 覆蓋 `aclose`、cancel、read failure、stop 與 reopen，並證明 source close、filter / partial state reset、active owner 解除；以 fake PCM 覆蓋完整與 partial write，且 Pi exact-SHA 卡證明無截斷 / xrun / owner 殘留。

### CR-M3-006 — M3 狀態與交付文件互相矛盾且引用缺失產物

- **契約依據**：workflow [E]；Designer 最終把關與提交規則；M3 test spec §3–§4；`dev_progress_M3.md` Definition of Done。
- **可驗證證據 / 最小重現**：`milestone_progress.md` 同時記錄 `Tester PASS`、implementation SHA `bae36dcb...`、結論「exact implementation SHA 與 RPI cards 仍為 Pending」、gate matrix `M3 target-device acceptance: PENDING`，並引用不存在的 `M3_tester_review.md`。`test_spec_M3.md` §3 仍稱所有 RPI cards Pending。`docs/outsource/pm_handoff/README.md` 仍列 M3 final acceptance Pending。hardware validation 沒有對應 delivery / response / evidence README；`dev_progress_M3.md` 上方宣告完成，但工作包總覽仍保留多項 Pi evidence Blocked / Pending。
- **預期 / 實際**：預期 milestone status、Developer progress、Tester sign-off、delivery 與 evidence index 對同一 candidate / disposition 一致；實際文件無法回答哪個 SHA 被接受、誰簽核、哪些項目仍 Pending。
- **影響**：即使程式修正，handoff 仍可能錯誤宣告 M3 Accepted 或讓 M4 以錯誤 baseline 進場。
- **建議修正方向**：先保留 M3 Open / Rejected；Developer 修正其進度與 delivery 文件，Tester 在重驗後更新 Tester-owned狀態 / 報告，Designer 複審通過後再統一宣告 Accepted。
- **最低驗收條件**：所有 M3 gate 文件只引用存在的 repo-relative 產物與同一 exact SHA；工作包、47-ID disposition、Tester report、hardware delivery / evidence index、PM handoff 狀態一致；在 CR Resolved 前不得標 M3 Accepted / Closed。

## Advisory

目前沒有獨立 Advisory。所有列出項目均直接涉及已簽核 acceptance criteria、假綠燈、資料完整性或高風險 regression protection。

## Designer 驗證證據

在本機專案 `.venv` 對目前工作樹執行：

```text
.venv/bin/python -m pytest -q -m "not rpi"
239 passed, 21 deselected in 7.77s

.venv/bin/python -m pytest -q tests/milestones/test_m1_foundation.py
1 passed in 1.23s

.venv/bin/python -m pytest -q tests/milestones/test_m2_mock_pipeline.py
1 passed in 1.97s

.venv/bin/python -m pytest -q -m "not rpi" tests/milestones/test_m3_rpi_hal.py
1 passed, 1 deselected in 0.74s
```

上述結果只證明 portable / regression gate；本機無 Pi 硬體，因此不取代 RPI-NATIVE 驗收。

## Developer 修訂與重新送審

1. 修正主程式、RPI tests、evidence runner 與 Developer-owned文件；不得修改已簽核設計 / test spec 來迎合現況。若契約無法落實，依流程另開 `IR_dev`。
2. 在本單逐項回覆修改檔案、行為、測試 node 與 evidence locator，將 YAML `status` 改為 `Revised`。
3. 所有修正完成後建立單一 candidate SHA，再交 Tester 對該 exact SHA 獨立驗收；不得沿用 `bae36dcb...` 的既有 PASS 宣告。
4. Tester PASS 後，Designer 僅複審本輪 findings、直接影響範圍與新 regression；全部 Blocking 解決後才可將本單改為 `Resolved` 並 close M3。

## Developer 修訂回覆（2026-08-16）

本輪已完成 code、test、evidence runner 與 Developer-owned 文件修訂，並交付
junior developer 的 exact-SHA Pi 重測手冊。`Revised` 表示已重新送審，不代表
RPI-NATIVE、Tester sign-off 或 Designer resolution 已完成。

### CR-M3-001 回覆 — exact SHA 與 Tester evidence

- `tests/rpi_support.py` 新增 `SBD_M3_CANDIDATE_SHA` 比對，並拒絕
  `src/`、`tests/`、manual helper、`pyproject.toml`、`requirements/` 的 tracked
  或 untracked dirty tree；每張
  result 記錄 branch 與完整 implementation SHA。
- `tests/milestones/test_m3_rpi_hal.py::test_m3_rpi_hardware_acceptance_gate`
  在 20 node 全通過後，再驗證 20 results / cards 的 `status=Pass` 與 candidate
  identity 完全一致。
- `docs/outsource/evidence/DELIVERY-M3-HARDWARE-VALIDATION-001/README.md`
  已明確將 `bae36dcb...` 的舊 results 標為 superseded，不再宣告 Tester PASS。
- 待辦：修訂內容取得 USER commit 同意、產生單一 candidate SHA 後，由 junior
  developer 依 runbook 執行；Tester 再對同一 SHA 獨立簽核並建立 repo 內報告。

### CR-M3-002 回覆 — Test ID traceability

- `M3-CAMI-002` 現在以 deterministic missing-CSI start failure 經
  `M2Composition` / `ResourceManager` 驗證 `NullCamera`、camera capability false、
  WARNING 與完整 start/stop；`M3-CAMI-003` 才執行 live RGB / I420 capture。
- `M3-GPIOI-001` 現在使用 BCM17→BCM27 loopback，直接驗 edge、kernel debounce、
  callback 欄位、unregister 後無事件、重複 unregister 與 output；
  `M3-GPIOI-002` 經 RM 驗 GPIO start failure、不建立 NullGPIO、capability false、
  `input.button` 不啟動、WARNING 與 App continue。
- Node 保持一 Test ID 對一同名 function；20-node collection 已驗證。

### CR-M3-003 回覆 — Audio / Button / Display integration cards

- `M3-AUDI-002` 改走 RM fallback；`M3-AUDI-003` 真正播放固定 3 秒 440 Hz
  native PCM 後才接受 current-run checklist；`M3-AUDI-004` 新增 warm-up + 300
  measured frames、3 次 reopen、cancel / EOF、buffer/filter/owner、raw latency、
  CPU / RSS / temperature / throttling 與 xrun disposition。
- `M3-BTN-001~005` 全部接上 real gpiod `ButtonInputSource` → EventBus →
  StateManager，驗 WAKE/PERCEPTION、interrupt convergence、graceful shutdown、
  recovered ERROR 與 recovery-active ignore 的 event/state trace；移除 manual PASS。
- `M3-DSPI-001` 經 arbiter `write_main` 驗單一 atomic flush；`002` 執行
  `DisplayLifecycle` boot/state/shutdown；`003` 經 `M3Composition` / RM fallback；
  `004` 驗 arbiter reopen 與 native handle/buffer/SPI/GPIO fd/thread cleanup；`005`
  真正顯示固定方向/RGB565 fixture 與產品 renderer；人工結果不能蓋過自動失敗。

### CR-M3-004 回覆 — EV-RPI bundle schema

- `tests/rpi_support.py` 只在 card assertions 完成後寫 `status=Pass`，並產生
  `manifest.json`、`environment/{system,hardware,devices,packages}`、
  `checksums/SHA256SUMS`、20 張 Markdown cards、schema-complete JSON results、
  logs index 與 media-metadata index。
- Result 包含 hardware/wiring、package/native artifact identity、ABI/license、
  config/fixture SHA、完整命令/操作、expected/actual、UTC start/end、exit code 與
  artifact locator；manual card 必須是本次開始後產生的逐項 checklist。
- `hardware.template.json` 與 `scripts/record_m3_observation.py` 已提供 junior
  developer 填寫入口；舊 20 JSON 不會通過新 gate。

### CR-M3-005 回覆 — Audio data/lifecycle integrity

- `AlsaAudioInput._next_frame()` 明確處理 `asyncio.CancelledError`，以 shielded
  release 清除 active owner、source、resampler、raw bytes 與 samples；invalid frame
  length 也先 release 再失敗。
- Input / Output 開啟後以 pyalsaaudio `PCM.info()` 拒絕實際 negotiation 不等於
  48k / stereo / S32_LE / 960 frames 的裝置。
- `AlsaAudioOutput._write_worker()` 依 frame count 續寫 positive partial result，
  並拒絕 negative、zero-progress、non-integer 與超量回傳。
- `tests/test_m3_aud_001_002_003_004.py::test_m3_aud_004` 已涵蓋 aclose、EOF、
  cancel、stop 冪等、restart、fresh first frame、完整/partial/stalled playback。

### CR-M3-006 回覆 — 狀態與交付一致性

- `docs/reviews/dev_progress_M3.md` 已將舊 20-card / 47-of-47 宣告標為
  superseded，現況統一為 portable PASS、exact-SHA RPI retest Pending。
- delivery README 同步標示 Pending；`docs/runbooks/m3_rpi_validation.md` 詳列
  junior developer 的 20-card 刺激、PASS/FAIL 條件、log/JUnit、人工 checklist、
  bundle 檢查與交回 Tester 流程。
- `docs/reviews/milestone_progress.md` 為 Designer-owned，現有 USER/Designer
  working-tree 修改未由 Developer 覆寫；`docs/test_spec/test_spec_M3.md` 與
  `docs/outsource/pm_handoff/README.md` 亦依權責保留，待 Tester / Designer 在
  exact-SHA 重驗後更新。M3 目前不得標為 Accepted / Closed。

### Developer 本機驗證

```text
.venv/bin/python -m pytest -q tests/test_m3_aud_001_002_003_004.py
4 passed

.venv/bin/python -m pytest -q -m "not rpi"
239 passed, 21 deselected

.venv/bin/python -m pytest --collect-only -q -m rpi <five M3 RPI files>
20 tests collected

.venv/bin/python -m compileall -q src tests scripts
exit code 0

git diff --check
exit code 0
```

### 重新送審仍待外部完成

1. USER 核准並建立包含本輪修正的單一 candidate commit。
2. Junior Developer 在 Pi 5 依 `docs/runbooks/m3_rpi_validation.md` 重跑 20 cards；
   不得沿用 `bae36dcb...` results。
3. Tester 對同一 SHA 獨立核對 27 DEV + 20 RPI、0 Fail / Blocked / Skip /
   XFail、完整 evidence index，建立存在於 repo 的 sign-off。
4. Designer 更新其 owner 文件並複審本輪 findings；只有 Requestor 可將本單改為
   `Resolved`。

## Designer 最終複審裁定（2026-08-17）

**本輪判定：PASS。** 固定 implementation SHA
`5c9e5aac47e7f4f0dd168d8c75541438ee74f858` 的 CR-M3-001～006 Blocking
findings 已全數符合契約或經 USER 明確核准的 transition disposition；未追加新門檻。

USER 本輪明確要求直接審核已在實機通過的固定 SHA，且不再次 freeze。依
`designer-review-5c9e5aa-20260817/README.md` 的 transition scope，Designer 可用兩批
保留的 debug runs 作 Accepted / Rejected 判定，不冒充 legacy single-run acceptance，
也不更改 `TR_dev_M3_I` 的 Tester-owned YAML 狀態。

| Finding | 裁定 | 最終證據 |
| --- | --- | --- |
| CR-M3-001 | Pass | 20 個唯一 target Test ID 全部指向完整 SHA `5c9e5aa...`、同一 config checksum、`Pass` / exit 0；runner 對 `src/`、`tests/`、必要 scripts與dependency paths執行 exact-SHA / clean guard。 |
| CR-M3-002 | Pass | Camera與GPIOI同名 nodes已直接覆蓋 fallback、format、debounce、cleanup、output與no-null GPIO policy；20 IDs無缺號或重複。 |
| CR-M3-003 | Pass | Audio、Button與Display cards包含產品路徑 assertions；AUDI-003、DSPI-002、DSPI-005本次人工 checklist全部為true。 |
| CR-M3-004 | Pass | 兩批 evidence均包含manifest、results、cards、environment、checksums、raw logs與media index；首次GPIOI-001 invocation failure及成功rerun均保留。 |
| CR-M3-005 | Pass | Portable Audio lifecycle / partial-write regression通過；本次AUDI-001/002/004實機run為3 passed，AUDI-003播放與聽覺check通過。 |
| CR-M3-006 | Pass | 本單、`milestone_progress.md`、hardware delivery README、PM handoff index及audit response統一以`5c9e5aa...`為M3 Accepted implementation；舊`bae36d...` / `cab627...` bundle維持superseded。 |

### Designer 獨立驗證

```text
complete -m "not rpi": 240 passed, 21 deselected in 35.91s; exit 0
evidence reconciliation: 20 unique IDs; exact SHA/config aligned;
all status=Pass and exit_code=0; 3 manual checklists all true
git diff --check 5c9e5aa^ 5c9e5aa: no output
```

Target evidence index：
`docs/outsource/evidence/DELIVERY-M3-HARDWARE-VALIDATION-001/designer-review-5c9e5aa-20260817/README.md`。
兩批 debug runs 的分批性已揭露；USER核准其作本次 transition direct review，故不要求
重跑或再 freeze。`IR_dev_M3_oled_shutdown_I` 是未納入本 candidate scope 的 future
Advisory，不阻擋本次 M3。

本 CR 設為 `Resolved`；M3 implementation SHA `5c9e5aa...` 標記為 **Accepted**，
可準備 milestone closeout commit proposal。
