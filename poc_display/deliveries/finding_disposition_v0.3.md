# v0.3 Finding Disposition

對應 review：`DELIVERY-004-poc_display-m3-v0.2-review`

| Finding | 狀態 | v0.3 disposition | 定位／剩餘證據 |
|---|---|---|---|
| D1 | Resolved in working tree; Core re-review pending | 唯一 Protocol 位於 `display/base.py`；compatibility module 只 re-export。Adapter 改為 async `start/stop`、同步 render primitives、`bytes` full frame；POC 不擁有第二套 Renderer/Arbiter。 | Contract §1–§2；mock lifecycle、compatibility service 與 ctypes→stub native smoke 已通過。Core target chip directory landing 由 integration delivery 定位。 |
| D2 | Resolved in contract/header and host verification; Pi build pending | ABI v1 定義 version/size、fixed-width types、status enum、handle lifecycle、buffer/thread ownership、error mapping；移除 native clear flush。 | Contract §3；public header C11 check PASS；stub native 驗證 bad 60 MHz config、wrong length/thread、repeated close PASS；Pi clean build 尚待完成。 |
| D3 | Partially resolved / Hardware run ready | 改正 DC=BCM25/Board22、RST=BCM27/Board13；primary/optional fixture 分離；新增 strict local config、read-only pre-test、revision/photo/owner gate。 | Contract §4、`poc_display/config/`、`poc_display/tools/`；panel/board revision、fixture photo、resolved gpiochip 與實際 config hash 待 Pi packet。 |
| D4 | Partially resolved / Hardware run ready | 移除 60 MHz、`<20 ms`、60 fps 承諾；baseline 改 4 MHz；packet 固定 10 warm-ups、100 samples、P50/P95/max 與 measurement boundary。 | Contract §5；真實 Pi latency、effective-speed availability 與人工 flicker 觀察待 Pi packet。 |
| D5 | Partially resolved / Candidate frozen; Pi materials pending | Tracked delivery 以 candidate full Git SHA 作單一提交包；只有無法上傳的 generated artifact、actual config 與 raw evidence 另記 checksum／custody。 | Candidate `3120c08c2b15b19c2b2b16a35577e456ad394937`；`.so`、actual config、raw evidence 與 Core integration SHA 待後續 gate。 |
| A1 | Resolved | 移除產品 Renderer/Arbiter/M3–M7 normative 建議，只保留 scope boundary。 | Contract opening、§1。 |
| A2 | Resolved | 使用 `single-flush / non-interleaved update`，明示不代表 hardware atomic。 | Contract §1。 |

## Pending owner/action

| Owner | Action |
|---|---|
| POC Display Team | 在指定 SSD1351 fixture 上完成 clean build、diagnostics、P50/P95/max、照片與 environment snapshot。 |
| POC Display Team | 確認實際 module/board revision、供電 pin、rotation、gpiochip resolution，保存使用中的 config 與 SHA-256。 |
| POC Display Team | 對無法納入 Git 提交包的 Pi artifact、actual config 與 raw evidence 記錄整包 checksum／custody reference。 |
| Core Team | 複審 D1–D5 與 regression；通過後另發 `Accepted as M3 design input` ACK。 |
| Core Tester / POC | 分別記錄 final M3 acceptance 與 fixture verification。 |

Audio POC-derived hardware flow：`poc_display/README.md`、`poc_display/tools/environment_pre_test.sh`、`poc_display/tools/m3_ssd1351_capability.sh`。
