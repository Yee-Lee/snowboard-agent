# P1 Operator Attestation Gate Review Request

狀態：`CLOSED_BY_OWNER_APPROVAL`

2026-08-12 Owner 判定此變更範圍極小並直接 `APPROVE`，明確免除本次第二次獨立 review。本文件保留為原始預備審核範圍，不表示 reviewer 曾執行或核准。

## Change intent

依 owner 決策，fixture、接線、顏色、方向與 flicker 使用人工 `PASS` attestation；照片不再是 P2/P3 gate，也不得因缺照片使 automated capability 成為 `INCONCLUSIVE`。

自動化 gate 仍必須包含 strict config、clean build、ABI/lifecycle/negative paths、latency、SPI/GPIO owner cleanup 與 exact clean SHA。

## Identity

| Field | Value |
|---|---|
| Diff baseline | `6fd126e4f68c7f253108ad1e7dd77aabd9797c0d` |
| Previous candidate | `3120c08c2b15b19c2b2b16a35577e456ad394937`（只作 reviewed baseline，不作最終 P3 target） |
| Replacement candidate | Owner-approved freeze commit full SHA |
| Pi preflight | Previous candidate PASS；replacement SHA 必須重跑 |

## Review target

- `poc_display/tools/m3_ssd1351_capability.sh`
- `docs/poc/milestone_plan.md`
- `poc_display/README.md`
- `poc_display/evidence/README.md`
- `poc_display/evidence/m3/M3-HW-SUMMARY-TEMPLATE.md`
- `poc_display/deliveries/display_m3_contract_draft.md`
- `poc_display/deliveries/finding_disposition_v0.3.md`
- `poc_display/deliveries/manifest_001.md`

Reviewer 不得修改 target files 或建立 commit；只填寫 `reviews/P1_OPERATOR_ATTESTATION_REVIEW_FEEDBACK.md`。

## Claimed verification

- `bash -n poc_display/tools/m3_ssd1351_capability.sh`：PASS。
- Full display suite：`26 passed, 8 skipped`。
- Explicit `--hardware=mock` run：`4 passed`。
- `git diff --check`：PASS。
- `M3_FIXTURE_PHOTO`、photo copy/hash 與 photo-required branch 已從 capability script 移除。
- Artifact checksum list 只保留 Pi-built `.so` 與 actual config；tracked content 由 full Git SHA 識別。

## Required review questions

1. 缺照片是否不再使 packet `INCONCLUSIVE`？
2. `M3_FIXTURE_RESULT=PASS` 是否與 panel revision、color、orientation、flicker 一起被記錄並強制驗證？
3. 是否仍保留所有 automated hardware/correctness/cleanup gates？
4. Script 在 failure/INCONCLUSIVE 下是否仍可靠 cleanup 且不掩蓋原始結果？
5. Milestone/contract/runbook/manifest/evidence 是否一致陳述「照片不要求、operator attestation 必須 PASS」？
6. 是否存在阻止 replacement candidate 的 blocking/high finding？

## Required output

將 findings、驗證命令與 `APPROVE`／`BLOCK` 寫入 `reviews/P1_OPERATOR_ATTESTATION_REVIEW_FEEDBACK.md`。`APPROVE` 只允許建立 replacement candidate；不代表 P2/P3/P4 完成。

本項已由 Owner decision 關閉，reviewer 不需填寫 feedback。
