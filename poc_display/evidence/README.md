# POC Display evidence workflow

狀態：`IN_PROGRESS`；尚未宣稱 Pi fixture 已通過。

流程沿用 Audio POC 經驗：先跑 read-only remote pre-test，再於 exact clean SHA 的 Pi checkout 跑 capability packet。環境不足回報 `INCONCLUSIVE`，契約行為失敗才回報 `FAIL`；不能把「畫面看得到」或 SSH command 結束當作 cleanup 證據。

正式入口與 operator 設定見 `poc_display/README.md`：

- `poc_display/tools/environment_pre_test.sh`
- `poc_display/tools/m3_ssd1351_capability.sh`

Raw run 目錄位於 `poc_display/evidence/m3/<timestamp>-ssd1351/`，並由 `.gitignore` 排除。Packet 產出：

```text
result.txt
environment.txt
build.log
artifacts.sha256
diagnostics.log
lifecycle.txt
visual-checklist.txt
fixture-photo.bin
runner/
  config.json
  config.sha256
  environment.txt
  latency.json
```

最低 gate：

- Pi 5 / aarch64、clean full SHA，且 local/Pi SHA 一致；
- strict config hash、resolved gpiochip、SPI device 與 boot SPI inventory；
- packet 前後均無 SPI/gpiochip owner；
- clean native build、`.so`/header/adapter checksums；
- black/white/red/green/blue/gradient、clear/show；
- wrong length 與 missing SPI device 在邊界失敗；
- stop 冪等、3/3 reopen；
- 10 warm-ups、至少 100 samples、P50/P95/max；
- panel revision 與 config 一致；fixture photo hash、RGB565 color、orientation、flicker 人工 gate 全數 PASS。

Raw evidence 只留在核准的 evidence custody。Review 後使用 `poc_display/evidence/m3/M3-HW-SUMMARY-TEMPLATE.md` 建立 sanitized summary；不得提交 endpoint、account、key path、private absolute path、完整私人終端輸出或未審查照片。
