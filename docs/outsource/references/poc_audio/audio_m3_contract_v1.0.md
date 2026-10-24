# Audio POC M3 v1.0 — External Source Locator

本檔只定位已採用的外部技術輸入，不保存Audio POC repository副本。

| Item | Authority |
| :--- | :--- |
| Repository | `git@github.com:Yee-Lee/poc_audio.git` |
| Accepted delivery SHA | `87ff000559ded8c0d7499d621af7dfcccb81858c` |
| Native-capability evidence source SHA | `0edeb7d9f8ff3811d1480ab4b464db2842978233` |
| Contract | `poc_audio/deliveries/audio_m3_contract_v1.0.md` at accepted delivery SHA |
| Option A change request | `poc_audio/deliveries/CR-AUDIO-M3-PCM-001.md` at accepted delivery SHA |
| Design correction | `poc_audio/deliveries/DELIVERY-AUDIO-POC-M3-DESIGN-CORRECTION-001.md` at accepted delivery SHA |
| Native evidence | `poc_audio/evidence/m1/M1-NATIVE-AUDIO-001.md` at evidence source SHA |
| Core decisions | `DELIVERY-AUDIO-POC-M3-ACK-001/002`、`DELIVERY-AUDIO-POC-M3-VALIDATION-001` |

## Temporary checkout

Developer只在需要查閱時執行；目標路徑必須位於`mktemp`建立的temporary directory，不得位於Core repository或一般workspace：

```bash
poc_checkout_dir="$(mktemp -d -t snowboard-audio-poc.XXXXXXXXXX)"
git clone --filter=blob:none --no-checkout \
  git@github.com:Yee-Lee/poc_audio.git \
  "$poc_checkout_dir/poc_audio"
git -C "$poc_checkout_dir/poc_audio" cat-file -e \
  '87ff000559ded8c0d7499d621af7dfcccb81858c^{commit}'
git -C "$poc_checkout_dir/poc_audio" switch --detach \
  87ff000559ded8c0d7499d621af7dfcccb81858c
test "$(git -C "$poc_checkout_dir/poc_audio" rev-parse HEAD)" = \
  87ff000559ded8c0d7499d621af7dfcccb81858c
```

若private repository無read權限，工作包保持`Blocked`並由USER / POC提供access；不得改用搜尋結果、fork、branch HEAD或手動複製檔案。使用完畢即刪除整個`poc_checkout_dir`；不得把clone、raw evidence、wheel或`.so`加入Core Git。

Audio Option A implementation仍受`DELIVERY-AUDIO-POC-M3-VALIDATION-001`的P4 gate約束；本locator不解除該gate。
