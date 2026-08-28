# M4A Developer Raspberry Pi 送審前診斷 Runbook

本手冊定義 Developer 在請求 M4A candidate 與交付 Tester 前，如何在 Raspberry
Pi 上驗證真實 ASR、TTS、ALSA、offline 與 lifecycle 修正。它不產生正式 acceptance
card，不取代 [`candidate_hardware_gate.md`](candidate_hardware_gate.md)，結果只能標記為
`Developer Diagnostic` 或 `Developer Exact-Candidate Verification`。

## 1. Gate 邊界與責任

| 階段 | 受測內容 | 允許結論 |
| :--- | :--- | :--- |
| Working-tree Diagnostic | 隔離 checkout 套用尚未提交的 patch | Diagnostic Pass / Fail；不得送作正式 evidence |
| Exact-candidate Verification | USER 核准後的 clean provisional SHA | Developer Verified / Fail；通過後才可請 Tester 獨立驗收 |
| Tester acceptance | frozen SHA、正式 matrix / preflight / acceptance | 依 candidate hardware gate 判定正式 Pass / Fail |

Developer 不得要求 Tester 代跑本手冊來判斷修正是否有效。Tester 必須使用新的 run
ID、fresh product / output，獨立執行正式 gate。

## 2. 必要輸入

所有路徑必須是 Git 外、受控且可由 operator 讀取的絕對路徑：

- Raspberry Pi 5，aarch64，正式部署 CPython 3.13；
- clean Core base checkout 或完整 provisional candidate SHA；
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

## 4. 隔離 checkout 與 identity

每次使用全新 Git 外目錄。Working-tree Diagnostic 從 clean base clone 後只套用本次
`src/`、`scripts/`、`tests/` patch；不得修改 formal checkout。記錄 base SHA 與 patch
SHA-256，結果標記 `Diagnostic`。

Exact-candidate Verification 必須改用 clean detached candidate：

```bash
git clone --no-hardlinks <formal-core-checkout> <new-diagnostic-root>/repo
git -C <new-diagnostic-root>/repo checkout --detach <40-character-candidate-sha>
test "$(git -C <new-diagnostic-root>/repo rev-parse HEAD)" = "<40-character-candidate-sha>"
test -z "$(git -C <new-diagnostic-root>/repo status --short -- src tests scripts requirements pyproject.toml)"
```

Dirty working-tree 結果不得升級或重新命名為 exact-candidate verification。

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

candidate 第一次驗證使用 fresh build。`--build-root`、`--output` 與其 `.json` 在命令
開始前都必須不存在；不得預先 `mkdir --build-root`。

```bash
<offline-exec> timeout 600s python3 scripts/m4a_audio_product.py build-whisper \
  --lock-root requirements/m4a \
  --source-archive <controlled-source>/whisper.cpp-v1.9.2.tar.gz \
  --build-root <new-diagnostic-root>/build-whisper \
  --output <new-diagnostic-root>/input/m4a-whispercpp-worker
```

同一 candidate 重跑時可使用持久保存、且 worker 與 build-result checksum 仍吻合的 build
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
- Working-tree Diagnostic 全綠後才可請求 provisional candidate。candidate 建立後必須以其
  exact SHA 重跑本手冊；exact-candidate verification 全綠後才可交 Tester。
- Tester 必須另用 fresh run ID、fresh output 與正式 candidate gate 獨立重跑；Developer
  結果不能複製、改名或合併為正式 Pass。
