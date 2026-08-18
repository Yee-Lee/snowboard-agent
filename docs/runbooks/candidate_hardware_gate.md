# M4 Candidate / Hardware Gate

本手冊自 M4 第一個產品候選起適用，目標是避免把錯誤版本或 portable 可發現的問題帶到 Pi。它不是通用硬體驗收 framework，也不回溯重跑或改判 M3。

## 1. 最小流程

| 階段 | 執行時機 | 必要結果 |
| :--- | :--- | :--- |
| Developer fast loop | 日常開發 | 團隊主要 Python 版本的 affected tests 通過 |
| Provisional candidate | M4 implementation 可送驗 | USER 核准 commit，取得完整 40-character SHA |
| Portable matrix | 準備或更新 frozen candidate 時一次 | 同一 SHA 在 CPython 3.11、3.12、3.13 平行通過 portable suite |
| Designer review / freeze | matrix 通過後 | 無 Blocking finding，記錄同一 candidate SHA |
| Pi preflight | 正式硬體驗收前 | SHA、protected paths、Pi runtime、matrix、hardware / artifact / config identity 與新 run output 全部有效 |
| Pi acceptance | preflight 通過後 | 部署 runtime 執行完整 RPI-NATIVE suite，保存 result 與 raw log |

一般 development push 不跑三版本 matrix。Pi 只跑正式部署 runtime，不乘上三個 Python minor。

## 2. Candidate identity 與 protected paths

Runner 必須由呼叫者傳入 `--candidate-sha`，在測試前確認它是完整 SHA 且等於目前 `HEAD`。Branch 名稱只記作診斷資訊，不參與 Pass / Fail。

Protected paths 只包含會改變測試結果的輸入：

- `src/`、`tests/`；
- candidate / acceptance runner 與 candidate CI workflow；
- dependency、lock、package metadata；
- runner 讀取的 config contract。

本機實際 config、evidence、一般文件與不影響 runner 的腳本不因未提交而拒絕 candidate。Protected path 有異動時須建立新 candidate；不要求對無關文件重跑 matrix。

## 3. Portable 與 Pi 分流

```text
candidate_gate.py portable \
  --candidate-sha <sha> --run-id <portable-run> \
  --python 3.11|3.12|3.13 --suite <portable-suite> \
  --timeout-seconds <limit> --output <new-output>

candidate_gate.py matrix \
  --candidate-sha <sha> --run-id <portable-run> \
  --input-root <portable-run-root> --output <portable-run-root>/matrix-index.json

candidate_gate.py preflight \
  --candidate-sha <sha> --run-id <acceptance-run> \
  --portable-index <matrix-index.json> --runtime 3.13 \
  --hardware <hardware.json> --config <sanitized-config.yaml> \
  --artifact-manifest <artifacts.json> --output <new-acceptance-output>

candidate_gate.py accept \
  --candidate-sha <sha> --run-id <acceptance-run> \
  --preflight <acceptance-output>/preflight.json \
  --suite <rpi-suite> --timeout-seconds <limit> --output <acceptance-output>

candidate_gate.py debug \
  --candidate-sha <sha> --run-id <debug-run> \
  --node <rpi-node> --timeout-seconds <limit> --output <new-debug-output>
```

`portable` 固定使用 `-m "not rpi"`，`accept` / `debug` 固定使用 `-m rpi`。Debug 可按診斷需要執行，不需先取得 formal FAIL bundle；其結果只能是 diagnostic，不能改名、複製或合併為正式 Pass。

## 4. Timeout、run output 與 evidence

- 每個 suite / subprocess 使用一個明確 bounded timeout；逾時停止並保存 stdout / stderr。
- Portable、preflight 與 debug output 必須不存在；已存在即拒絕，不覆寫舊 run。Acceptance 只能在同一 run 的 preflight 目錄寫入一次 result。
- 每個正式命令保存一份簡單 result：run ID、完整 SHA、命令、平台、Python、開始／結束、exit code、status 與 raw log locator。
- Preflight 另外記錄實際 artifact manifest、sanitized config 與 hardware description 的 SHA-256；不要求中間 JSON 互相建立 checksum chain。
- Matrix 只驗證三個 Python minor、同一 SHA / run ID、bounded timeout、零 exit 且沒有 Fail / Skip / XFail。Branch 名稱不要求相同。

## 5. 人工操作

需要聽、看或操作硬體時，Tester 可在現場直接要求 operator 執行，不由通用 runner 建立 READY、nonce、producer PID或獨立 observation handshake。

有人工測項時，在既有 test report / card 記錄 `run ID`、`Test ID`、operator、時間及 Pass / Fail；沒有人工測項就不建立這些欄位。可自動驗證的 buffer、格式、呼叫順序與 lifecycle 仍由測試 assertion 判定。

## 6. 變更與重跑邊界

- Protected input 修改：建立新 candidate SHA，再跑一次三版本 matrix。
- 只有實體接線或 Git 外 artifact / config 改變：同一 frozen SHA 可保留，但須用新 run ID重做 preflight與完整 acceptance。
- Gate runner或workflow修改：只跑受影響的小型 regression；下一個 candidate 再執行三版本 matrix。
- 不重跑 M3 hardware evidence，不要求六項 command-level dry run，也不為每個 failure stage建立完整 identity chain。
