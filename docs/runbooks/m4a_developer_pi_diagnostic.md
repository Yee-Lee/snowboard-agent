# M4A Developer Raspberry Pi 送審前診斷 Runbook

本手冊定義 Developer 在請求 M4A candidate 前，如何以 Raspberry Pi 作為主要開發
working tree，直接修正並驗證真實 ASR、TTS、ALSA、offline 與 lifecycle，收斂後再將
單一 patch 同步回工作站。它不產生正式 acceptance card，不取代
[`candidate_hardware_gate.md`](candidate_hardware_gate.md)，例行結果只能標記為
`Developer Diagnostic`。

## 1. Gate 邊界與責任

| 階段 | 受測內容 | 允許結論 |
| :--- | :--- | :--- |
| Pi Working-tree Convergence | 從 clean base 建立的隔離 checkout；Developer 直接修正 | affected portable + target diagnostic 全綠；只能標記 Diagnostic Pass / Fail |
| Workstation Sync | 同一 base SHA、task paths 乾淨；套用 Pi 匯出的 tracked-only patch | 兩端 patch bytes / SHA-256 相同，工作站 affected portable tests 全綠後才可請求 candidate |
| Tester acceptance | frozen SHA、正式 matrix / preflight / acceptance | 依 candidate hardware gate 判定正式 Pass / Fail |

Developer 不得要求 Tester 代跑本手冊來判斷修正是否有效，也不在 candidate 建立後
例行返回 Pi 重複證明同一修正。Tester 必須使用新的 run ID、clean exact SHA、fresh
product / output，獨立執行正式 gate。

## 2. 必要輸入

所有路徑必須是 Git 外、受控且可由 operator 讀取的絕對路徑：

- Raspberry Pi 5，aarch64，正式部署 CPython 3.13；
- clean Core base checkout；若正式 gate 後另有明確診斷需求，才使用完整 provisional
  candidate SHA；
- `whisper.cpp-v1.9.2.tar.gz` 與 `requirements/m4a/` checksum 相符；
- 13 個 flat install inputs：models、Matcha archive、8 個 locked wheels，以及 fresh
  build 產生的 worker / build-result；
- controller closure manifest 與五個 wheels：PyYAML、NumPy 2.4.2、samplerate
  0.2.4、pyalsaaudio 0.11.0、Pillow 11.1.0；
- 16 kHz、mono、S16_LE、完整 640-byte frames 的受控 ASR fixture；
- device-local target config，ASR / TTS / ALSA 均選 real driver；
- `strace`、`cmake`、`git`、`ip`、`fuser` 與可建立 network namespace 的權限。

不得臨時連網下載缺少的 wheel、model 或 source。缺少任一受控輸入即停止。

## 3. Fresh device baseline

建議在獨占 Pi 上重新開機。重開機後先記錄 boot ID，並確認沒有殘留 M4A 程序、
ALSA holder 或 child workdir：

```bash
cat /proc/sys/kernel/random/boot_id
pgrep -af 'sbd-m4a|whisper|matcha|sherpa' || true
fuser -v /dev/snd/* || true
find /tmp/sbd-m4a-asr /tmp/sbd-m4a-tts -mindepth 1 -maxdepth 1 -print 2>/dev/null
git -C <formal-core-checkout> status --short --untracked-files=no
```

預期程序、ALSA holder、temp entry 與 formal tracked status 均為空。若發現不明 owner
的程序，不得直接 kill；先確認 owner / PPID / PGID。無法安全歸屬時重新開機。

本 Pi 會在重開機時清空 `/tmp`。因此 `/tmp` 中的 product、controller venv 與診斷
checkout 都必須視為不存在，不得把「檔案消失」誤判成產品 regression。

## 4. 隔離 Pi checkout、直接修正與單次同步

每次使用全新 Git 外目錄，從 clean Core base clone 建立 Pi 開發 checkout；不得修改
formal acceptance checkout。開始前記錄完整 base SHA，確認本工作包的 `<task-paths>`
乾淨。Developer 可在此 checkout 直接修改 `src/`、`scripts/`、`tests/`、dependency、
config contract與runner，並反覆執行本手冊的 affected portable tests 與 target
diagnostic，直到全部通過。affected scope 必須先依 M4 test spec、工作包與直接
regression 記錄；遇到失敗可擴充直接影響範圍，不得縮減。兩端不得同時修改同一工作包。

收斂後先以 `git add -N -- <new-task-files>` 讓新增檔案進入 diff（若沒有新增檔案則略過），
再將本工作包所有路徑明列於 `<task-paths>`，匯出 Git 外 patch 並記錄 digest：

```bash
git -C <pi-development-repo> diff --binary --full-index --no-ext-diff --no-textconv \
  --no-renames --no-color --src-prefix=a/ --dst-prefix=b/ --diff-algorithm=myers \
  -- <task-paths> > <git-external-transfer>/developer.patch
sha256sum <git-external-transfer>/developer.patch
git -C <pi-development-repo> status --short -- <task-paths>
```

`<task-paths>` 必須涵蓋本工作包的全部修改；device-local config、build product、raw log、
evidence與其他秘密不得放入 patch。回到工作站後，先確認 `HEAD` 等於記錄的 base SHA，
且 `<task-paths>` 沒有既有修改，再套用及逐 byte 核對：

```bash
test "$(git -C <workstation-repo> rev-parse HEAD)" = "<40-character-base-sha>"
test -z "$(git -C <workstation-repo> status --short -- <task-paths>)"
git -C <workstation-repo> apply --check <git-external-transfer>/developer.patch
git -C <workstation-repo> apply <git-external-transfer>/developer.patch
git -C <workstation-repo> add -N -- <new-task-files>  # 若沒有新增檔案則略過
git -C <workstation-repo> diff --binary --full-index --no-ext-diff --no-textconv \
  --no-renames --no-color --src-prefix=a/ --dst-prefix=b/ --diff-algorithm=myers \
  -- <task-paths> > <git-external-transfer>/workstation.patch
cmp <git-external-transfer>/developer.patch <git-external-transfer>/workstation.patch
sha256sum <git-external-transfer>/workstation.patch
```

工作站只再執行一次主要 Python minor 的 affected portable tests。若 base 已前進、patch
不同、測試失敗或仍須修改 protected input，不得在工作站另長出一套修正；以新 base／
完整新 patch 回 Pi 重走本節，原 Diagnostic Pass 失效。全部通過後才可依 workflow
展示 commit 內容並請 USER 核准 provisional candidate。

candidate 建立後不例行執行 Developer exact-candidate verification。只有正式 gate 發現
packaging／部署 identity 問題，且需要隔離診斷時，才建立 clean detached candidate；
其結果仍只是 diagnostic：

```bash
git clone --no-hardlinks <formal-core-checkout> <new-diagnostic-root>/repo
git -C <new-diagnostic-root>/repo checkout --detach <40-character-candidate-sha>
test "$(git -C <new-diagnostic-root>/repo rev-parse HEAD)" = "<40-character-candidate-sha>"
test -z "$(git -C <new-diagnostic-root>/repo status --short -- src tests scripts requirements pyproject.toml)"
```

Dirty working-tree 結果不得升級或重新命名為 exact-candidate verification，任何 Developer
exact-candidate 結果也不得取代 Tester acceptance。

## 5. Offline executor

所有 build、install 與 audio 診斷必須在新的 network namespace 中執行。以下
`<offline-exec>` 表示 operator 核准的等價 wrapper：建立 new network namespace、只啟用
`lo`、保留 checkout / ALSA / controlled-input 存取權，再執行 bounded command。

進入 namespace 後必須確認：

```bash
awk -F: 'NR>2 {gsub(/ /,"",$1); if ($1 != "lo") print $1}' /proc/net/dev
awk 'NR>1 && $1 != "lo" && $2 == "00000000" {print}' /proc/net/route
```

兩個命令都必須沒有輸出。不要以 `/sys/class/net` 的名稱清單判斷 namespace 是否隔離；
sysfs 可能仍顯示 host interface 名稱。

## 6. Fresh build、install 與 controller closure

### 6.1 Native worker

每一輪新 Pi working-tree base 的第一次驗證使用 fresh build。`--build-root`、`--output` 與其 `.json` 在命令
開始前都必須不存在；不得預先 `mkdir --build-root`。

```bash
<offline-exec> timeout 600s python3 scripts/m4a_audio_product.py build-whisper \
  --lock-root requirements/m4a \
  --source-archive <controlled-source>/whisper.cpp-v1.9.2.tar.gz \
  --build-root <new-diagnostic-root>/build-whisper \
  --output <new-diagnostic-root>/input/m4a-whispercpp-worker
```

同一 base 與 patch 重跑時可使用持久保存、且 worker 與 build-result checksum 仍吻合的 build
artifact；重開機本身不要求重新編譯。Tester 是否重建仍以正式 runbook 為準。

### 6.2 Product install

`--install-root` 必須不存在。即使重用已驗證 build artifact，也必須建立 fresh install：

```bash
<offline-exec> timeout 900s python3 scripts/m4a_audio_product.py install \
  --lock-root requirements/m4a --input-root <new-diagnostic-root>/input \
  --install-root <new-product-root> --python /usr/bin/python3.13
```

預期 `status=Pass`、`wheel_count=8`，並記錄 product lock SHA-256。device-local config 的
model、worker、VAD/TTS runtime path 必須指向這個 fresh product。

### 6.3 Controller runtime

VAD / TTS product venv 不可當 controller runner。建立 fresh、無 system-site-packages 的
controller venv，以 `--no-index --no-deps` 安裝 manifest 列出的五個 wheels，再執行：

```bash
OPENBLAS_NUM_THREADS=1 <controller-python> scripts/m4_audio_runtime_closure.py preflight \
  --manifest <controller-closure>/manifest.json \
  --wheel-dir <controller-closure>/wheels --venv <new-controller-venv>
```

manifest、wheel inventory、size、checksum、版本、import location 任一不符即停止。

## 7. Real audio diagnostics

使用同一 fresh controller / product / config。每個命令都在新的 offline namespace 下，
且以 `strace -f -qq -e trace=network` 包住完整程序樹：

```bash
PYTHONPATH=<diagnostic-repo>/src OPENBLAS_NUM_THREADS=1 \
  timeout 180s strace -f -qq -e trace=network -o <run-root>/asr-network.trace -- \
  <controller-python> scripts/m4a_developer_pi_check.py asr \
  --config <target-config> --pcm <controlled-asr-wav>

PYTHONPATH=<diagnostic-repo>/src OPENBLAS_NUM_THREADS=1 \
  timeout 300s strace -f -qq -e trace=network -o <run-root>/tts-network.trace -- \
  <controller-python> scripts/m4a_developer_pi_check.py tts \
  --config <target-config>
```

兩個 trace 都必須滿足：

```bash
test "$(grep -Ec 'AF_INET6?' <run-root>/asr-network.trace)" -eq 0
test "$(grep -Ec 'AF_INET6?' <run-root>/tts-network.trace)" -eq 0
```

ASR 必須有兩次非空結果、finite no-endpoint bounded 收斂、`STOPPED`，且 process / thread /
FD / temp cleanup 全 0。TTS 必須實際完成 ALSA playback + drain、controller native threads
為 1、Level-1 deferred request 維持 pending、Level-2 destroy、rebuild 後兩次 synthesis、
`STOPPED`，且 cleanup 全 0。

## 8. 失敗處理與送審條件

- config validation、缺 package、timeout 或硬體占用都算 Fail，不得以 network 0 代替產品
  結果。
- network count 非 0 時，保存 trace，先依 PID / executable 歸屬呼叫者；不得只在文件中
  宣稱 offline。
- 任何殘留程序、thread、FD 或 temp entry 非 0 時，保存程序樹後停止；不得把 Tester
  當清理工具。
- 診斷輸出不得包含 transcript、原始 PCM、TTS payload 或秘密。腳本只輸出 bounded metrics。
- Pi checkout 內 affected portable tests 與本手冊 target diagnostics 全綠，且依 §4 單次
  同步回工作站、patch identity 相同、工作站 affected portable tests 全綠後，才可請求
  provisional candidate。
- candidate 建立後不要求 Developer 例行返回 Pi。若 candidate 後任何 protected input
  改變，必須建立完整新 patch 回 Pi 重走開發收斂與工作站同步，再請求新 candidate。
- Tester 必須另用 fresh run ID、fresh output 與正式 candidate gate 獨立重跑；Developer
  結果不能複製、改名或合併為正式 Pass。

## 9. 跨階段真人實測除錯

本節適用於使用相同 App/ALSA/Whisper 組合的後續階段。它是明確啟用的私有診斷模式，
不更改普通啟動的記錄政策，也不把真人實測自動判為 PASS。使用該階段待測版本的入口、
設定與 runtime；不得為了開啟除錯而退回舊版本。原始錄音與文字保存在 repository 外，
目錄權限 0700、檔案 0600；不放入 Git，也不自動產生內容 digest。

### 9.1 同一正式入口啟動

已安裝版本若包含此診斷工具：

```bash
<app-root>/run.sh --debug
```

一般使用維持 `<app-root>/run.sh`。`--debug` 會從同一版本啟動真實 App，建立新的
`~/snowboard-debug/manual-*/`，複製設定並分開記錄日誌。來源設定不被覆寫，模型等相對
路徑仍指向原來的檔案。沒有自動按鍵或自播；由 USER 自己操作實體 Button 與麥克風。
若要指定 repository checkout、runtime 或輸出根目錄，可直接使用：

```bash
<controller-python> scripts/run-manual-debug.py \
  --installed-entry <same-version-entry> --config <target-config> \
  --python <controller-python> --output-root <private-output-root>
```

依當前測項操作，不預設重跑所有歷史案例。首次問題可先使用一個短句；要查跨 Session
問題，再完成一輪、短按回待命、開下一輪。只有查無輸入恢復時才刻意等待一次逾時。
回報實際原句、順序、顯示與聽到的回覆。若出錯，先保存這一輪，勿連續重開覆蓋現象。
以長按或 Ctrl+C 結束；預設 watchdog 30 分鐘，正常退出後才會寫出完整逐輪錄音。

### 9.2 先判定哪一層錯誤

| 資料 | 用途與限制 |
| :--- | :--- |
| `observation/result.json` | App exit、錯誤摘要與原始 cleanup 結果；正常結束仍只待 USER 回報 |
| `observation/private/run-observation.json` | Session/Turn、實際 ASR 文字、回覆、request ID、時間與私有 fatal chain |
| `observation/private/microphone*.wav` | App 實際收進來的音訊；含背景／前後靜音，不等於原生 ASR 的裁切輸入 |
| `observation/private/*-request-*.wav` | 捕捉結束後另存的實際 VAD-bounded 原生 ASR 輸入，於 child workdir 刪除前保留 |
| `observation/private/asr-child-trace*.json` | endpoint、原生計算、ERROR/例外與 request 關聯；非正常強制終止時可能不完整 |
| 私有 `display_content`／`display_presentations` | 顯示要求、儲存文字與成功呼叫 native present；不等於真人視覺判讀 |
| `application.log` | 狀態轉移與錯誤摘要；預設不在一般日誌輸出逐字稿 |

先核對 USER 原句與保存的 ASR 文字；兩者不同時，LLM 對錯句作答不能單獨歸因為推理失敗。
再核對 request/Turn 與錄音，區分截斷、串輪、辨識錯句、等待逾時及回答後的流程故障。
聽錄音時若調整音量，記錄錄音增益與喇叭輸出比例；主觀清楚不代表原音量 ASR 已正確。

### 9.3 重用錄音，先直接 ASR、再經 App 收音

Pi 的安裝、模型／runtime 複製、回歸測試與 App 實機測試依序進行。App 收音、辨識或
播放測試期間，不並行大量檔案傳輸、安裝或其他測試，避免資源競爭污染等待時間。

含此修正的測試版本中，一般無輸入／沒有可用語音結果，保留「我沒聽清楚，請再說一次。」與重新收音；ASR
system fault 則保留 `ErrorOccurred` 的 code／分類與 `ERROR` 狀態，完成 backend 重建及
舊對話清理後，播放「語音辨識發生錯誤，請按按鈕重新開始。」再回待命。故障提示不是
重新收音承諾；新 Session 由新的按鈕觸發。ALPHA 不在此定稿未來 Display 的文字與版型。

優先選用 `*-request-*.wav` 做原生 ASR 重辨，可保留相同裁切內容。只有要查完整收音或
缺少原生輸入時，才使用 `microphone*.wav`，並註明輸入範圍不同。

```bash
<controller-python> scripts/run-manual-debug.py --config <target-config> \
  --replay-asr <saved-wav> --output-root <private-output-root>
```

每次另建 `asr-replay-*/`，私有 `result.json` 保留實際文字／例外，`native-input.wav`
保留送入模型的副本。`DECODED` 只代表模型有輸出，不代表辨識正確。要檢驗音量假設，
同一份原檔分別使用 `--gain 1`、`--gain 4` 等明確數值；結果記錄 clipping 數量。
這不修改產品收音增益、模型、提示詞或原始檔。勿直接把調整增益後成功當成根因證明。

接著可把保存的 WAV 透過 App 喇叭播放，仍由 App 的真實麥克風與 Listen/ASR 接收：

```bash
<controller-python> scripts/run-acoustic-asr.py \
  --installed-entry <same-version-entry> --config <target-config> --python <controller-python> \
  --reference-wav <saved-wav> --reference-text '<USER原句>' \
  --turns 2 --output <fresh-private-output> --watchdog 180 --cleanup-timeout 20
```

這一模式會自動送出 Button 開／關 Session，測試時請勿另外按鍵或說話。輸入只從實體
麥克風進入 ASR，不注入 reference PCM。自訂錄音有獨立 private reference metadata，
不是固定 ALPHA fixture 或正式效能基準；文字不符時保留 INVALID 與實際輸出，不改成 PASS。
收音路徑多了一次喇叭／麥克風，成功或失敗都應與直接 ASR 結果分開記錄。
若要比較增益，使用上一步產生的 `native-input.wav` 副本，保留對應的 gain metadata。

### 9.4 致命錯誤後清屏

`run.sh --debug` 的外層工具會在 App 以非零碼退出後，另啟一個最多 10 秒的清屏程序。
先確認沒有活躍 App，且 SPI/GPIO 裝置無持有者，才重新開啟顯示器、呈現全黑並關閉。
占用、無法確認 owner 或清屏逾時時，保留失敗並停止；不強殺無法歸屬的其他程式。
已知屬於該 run 的子程序由既有 runner 有限時清理。

`session-result.json` 分別記錄原始 App exit 與這次獨立清屏結果，`display-clear.log`
保留失敗細節。原始 cleanup/FAIL 不被改寫；清屏成功也不能證明該次 App 曾正常 shutdown。
這是 operator-side 修復，不更改 Ch 11 的 fatal-path 契約，不重啟 App。
**普通 `run.sh` 沒有這項事後自動清屏**；若產品要求所有正常入口都具備此行為，需由 Designer
更新部署／退出設計與適用測項。
