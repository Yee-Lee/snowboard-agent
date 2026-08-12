# P1 Native Linker Fix Owner Decision

狀態：`OWNER_APPROVED`

> 這不是獨立 reviewer 結論。Owner 明確決定直接核准本次 linker fix。

## Decision identity

| Field | Value |
|---|---|
| Authority | `Owner / user` |
| Decided at UTC | `2026-08-12T14:38:55Z` |
| Diff baseline | `6b24dacbca63c9f9499f86748b64a0614190c096` |
| Independent reviewer | `WAIVED_BY_OWNER` |

## Scope

修正 SSD1351/ST7789 native link order、加入 `-Wl,-z,defs` 與 capability `ldd -r` gate，並同步 target-Pi user build 文件。

## Decision

Owner 指示直接 `APPROVE`，並要求未來只在每個 stage exit 請求 review，不因階段內小修正反覆停下。

結論：`APPROVE`

此決策只允許繼續本階段並建立 replacement candidate，不表示 P2/P3/P4 完成。
