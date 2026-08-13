# Display POC M3 v0.3 — External Source Locator

本檔只定位已接受的外部design input，不保存Display POC repository副本。

| Item | Authority |
| :--- | :--- |
| Repository | `git@github.com:Yee-Lee/poc_display.git` |
| Accepted source candidate SHA | `5c2b6ba532a2661d5db79e27736e79890931515f` |
| Stage-exit evidence SHA | `055517a905bd2c8f8531c05acfa658854e25491f` |
| Stage-exit review SHA | `4ed5f64a2604fa3c388cfa60fb971bb508a4ee40` |
| Contract | `poc_display/deliveries/display_m3_contract_draft.md` at source candidate SHA |
| Manifest | `poc_display/deliveries/manifest_001.md` at source candidate SHA |
| Header / adapter / config / tests | tracked tree at source candidate SHA；以manifest列出的path / checksum為準 |
| Review disposition | `reviews/P4_STAGE_EXIT_REVIEW_FEEDBACK.md` at stage-exit review SHA |
| Core decision | `DELIVERY-005-poc_display-m3-v0.3-ack` |

## Temporary checkout

Developer只在需要查閱／target build時執行；目標路徑必須位於`mktemp`建立的temporary directory，不得位於Core repository或一般workspace：

```bash
poc_checkout_dir="$(mktemp -d -t snowboard-display-poc.XXXXXXXXXX)"
git clone --filter=blob:none --no-checkout \
  git@github.com:Yee-Lee/poc_display.git \
  "$poc_checkout_dir/poc_display"
git -C "$poc_checkout_dir/poc_display" cat-file -e \
  '5c2b6ba532a2661d5db79e27736e79890931515f^{commit}'
git -C "$poc_checkout_dir/poc_display" switch --detach \
  5c2b6ba532a2661d5db79e27736e79890931515f
test "$(git -C "$poc_checkout_dir/poc_display" rev-parse HEAD)" = \
  5c2b6ba532a2661d5db79e27736e79890931515f
```

Stage-exit evidence／review以`git show <exact-sha>:<authority-path>`查閱，不把不同SHA內容拼成一個working tree。若private repository無read權限，相關工作包保持`Blocked`並由USER / POC提供access；不得改用fork、branch HEAD或手動副本。

使用完畢即刪除整個`poc_checkout_dir`。POC `.so`不搬入Core repository；Developer在target Pi從accepted source SHA編譯，並依ACK與manifest驗證header、adapter、config、artifact checksum、license及runtime identity。
