# v0.3 Finding Disposition

對應 review：`DELIVERY-004-poc_display-m3-v0.2-review`

| Finding | 狀態 | v0.3 disposition | 定位／剩餘證據 |
|---|---|---|---|
| D1 | Resolved; Core re-review pending | 唯一 Protocol 位於 `display/base.py`；compatibility module 只 re-export。Adapter 改為 async `start/stop`、同步 render primitives、`bytes` full frame；POC 不擁有第二套 Renderer/Arbiter。 | Contract §1–§2；mock lifecycle、compatibility service 與 ctypes→stub native smoke 已通過。Core target chip directory landing 由 integration delivery 定位。 |
| D2 | Resolved; Core re-review pending | ABI v1 定義 version/size、fixed-width types、status enum、handle lifecycle、buffer/thread ownership、error mapping；Pi clean build 與 `ldd -r` PASS。 | Contract §3；Pi packet `M3-HW-SUMMARY-2026-08-12.md`。 |
| D3 | Resolved; Core re-review pending | Primary fixture 為 co-I2S：DC=BCM24/Board18、RST=BCM25/Board22、CE0=BCM8/Board24（SPI kernel-managed）；strict config、preflight、operator fixture/revision/owner gate PASS；不要求照片。 | Contract §4；Pi packet `M3-HW-SUMMARY-2026-08-12.md`。 |
| D4 | Resolved; Core re-review pending | 4 MHz baseline；10 warm-ups、100 samples、P50/P95/max；effective speed unavailable 且未推論 throughput。 | Contract §5；Pi packet `M3-HW-SUMMARY-2026-08-12.md`。 |
| D5 | Resolved; Core re-review pending | Tracked delivery 使用 candidate full Git SHA；Pi-built `.so`、actual config 與 raw evidence 記單一 checksum/custody。 | Candidate `5c2b6ba532a2661d5db79e27736e79890931515f`；summary 與 manifest。 |
| A1 | Resolved | 移除產品 Renderer/Arbiter/M3–M7 normative 建議，只保留 scope boundary。 | Contract opening、§1。 |
| A2 | Resolved | 使用 `single-flush / non-interleaved update`，明示不代表 hardware atomic。 | Contract §1。 |

## Pending owner/action

| Owner | Action |
|---|---|
| POC Display Team | 在指定 SSD1351 fixture 上完成 clean build、diagnostics、P50/P95/max、operator attestation 與 environment snapshot。 |
| POC Display Team | 確認實際 module/board revision、供電 pin、rotation、gpiochip resolution，保存使用中的 config 與 SHA-256。 |
| POC Display Team | 對無法納入 Git 提交包的 Pi artifact、actual config 與 raw evidence 記錄整包 checksum／custody reference。 |
| Core Team | 複審 D1–D5 與 regression；通過後另發 `Accepted as M3 design input` ACK。 |
| Core Tester / POC | 分別記錄 final M3 acceptance 與 fixture verification。 |

Audio POC-derived hardware flow：`poc_display/README.md`、`poc_display/tools/environment_pre_test.sh`、`poc_display/tools/m3_ssd1351_capability.sh`。
