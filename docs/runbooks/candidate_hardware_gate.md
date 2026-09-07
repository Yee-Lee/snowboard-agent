# M4 Candidate / Hardware Gate

本手冊自 M4 第一個產品候選起適用，目標是讓 Pi 耦合工作先在 target 收斂，並確保
送進正式 gate 的內容只同步一次、candidate identity 可重現。它不是通用硬體驗收
framework，也不回溯重跑或改判 M3。

## 1. 最小流程

| 階段 | 執行時機 | 必要結果 |
| :--- | :--- | :--- |
| Developer Pi convergence | Pi 耦合的日常開發 | 隔離 Pi checkout 內 affected portable tests 與 target diagnostic 全綠；同 base/task paths/patch digest 單次同步回工作站，affected portable tests 再通過一次 |
| Developer workstation loop | 完全與 target 無關的日常開發 | 團隊主要 Python 版本的 affected tests 通過 |
| Provisional candidate | M4 implementation 可送驗 | USER 核准 commit，取得完整 40-character SHA |
| Portable matrix | 準備或更新 frozen candidate 時一次 | 同一 SHA 在 CPython 3.11、3.12、3.13 平行通過 portable suite |
| Designer review / freeze | matrix 通過後 | 無 Blocking finding，記錄同一 candidate SHA |
| Pi preflight | 正式硬體驗收前 | SHA、protected paths、Pi runtime、matrix、hardware / artifact / config identity 與新 run output 全部有效 |
| Pi acceptance | preflight 通過後 | 部署 runtime 執行完整 RPI-NATIVE suite，保存 result 與 raw log |

前兩個 Developer row 依工作包是否 Pi 耦合擇一；同一工作包只要包含任一 target-coupled
行為，就使用 Pi convergence，不得拆成工作站修產品、Pi 只重測的雙 working-tree loop。
一般 development push 不跑三版本 matrix。Pi 開發 loop 使用正式部署 Python minor 執行
affected portable tests 與 target diagnostic；正式 Pi gate 只跑部署 runtime，不乘上三個
Python minor。

### 1.1 Pi 耦合工作的 candidate 前收斂

凡修改可能受 Pi 硬體、原生相依、部署 runtime、裝置權限、效能或資源行為影響，
Developer 必須在與 formal acceptance checkout 分離的 Pi working tree 直接修正，不在
工作站與 Pi 各留一套 WIP。每輪在 Pi 執行 affected portable tests 及 target diagnostic，
直到全部通過；affected scope 必須先依 test spec、工作包與直接 regression 記錄，遇到
失敗只能擴充直接影響範圍，不得縮減以取得綠燈。這些結果只標記為
`Developer Diagnostic`。

收斂後記錄 base SHA 與完整 task-path list，將包含新增檔案的 tracked-only patch 匯出並
計算 SHA-256。工作站 repo 必須位於同一 base SHA、task paths 乾淨；套用後重新匯出的
patch bytes與digest必須相同，再於主要 Python minor 執行一次 affected portable tests。
只有這次確認通過後才可請求 provisional candidate。若同步後修改任何 protected input，
Pi 結論立即失效，完整新 patch 必須回 Pi 重跑本節；不能以工作站追加修正直接送 candidate。

candidate 後不要求 Developer 例行返回 Pi 做第二次驗證。正式 exact-SHA 身分與硬體結果
由 Tester 的 preflight / acceptance 證明；若正式 gate 發現產品問題，另開隔離 Pi 開發
checkout 回到本節，不在 acceptance checkout 直接修正。

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

`portable` 固定使用 `-m "not rpi"`，`accept` / `debug` 固定使用 `-m rpi`。本節命令只適用
已建立的 exact candidate；candidate 前的 dirty working-tree 診斷依 milestone Developer
runbook 執行，不得偽造 `--candidate-sha`。Debug 可按診斷需要執行，不需先取得 formal
FAIL bundle；其結果只能是 diagnostic，不能改名、複製或合併為正式 Pass。

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

- Candidate 建立後修改 protected input：原 freeze / evidence 不得沿用；先回 Pi Developer
  convergence loop 收斂完整新 patch，再建立新 candidate SHA並跑一次三版本 matrix。
- 只有實體接線或 Git 外 artifact / config 改變：同一 frozen SHA 可保留，但須用新 run ID重做 preflight與完整 acceptance。
- Candidate / acceptance runner或可執行的candidate CI workflow修改：視為protected input，
  依第一項回Pi收斂、建立新candidate並重跑三版本matrix。
- 只有文字型runbook／workflow文件修改，且不改runner或受測輸入：只做受影響的文件／
  小型regression檢查，不撤銷既有candidate；下一個candidate直接遵循新流程。
- 不重跑 M3 hardware evidence，不要求六項 command-level dry run，也不為每個 failure stage建立完整 identity chain。
