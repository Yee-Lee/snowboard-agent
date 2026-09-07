# Delivery registry

此處保存 Core 對外 task、ACK、decision 與 receipt。日常工作只從 `active/` 開始；
`archive/` 保留原文與 provenance，不應整批載入。

## Active

| Area | Document | State / next action |
|---|---|---|
| Shared Pi | [`PI-MIGRATION-STATUS-001`](active/PI-MIGRATION-STATUS-001.md) | current migration state |
| LLM MVA | [`RECEIPT-LLM-POC-M4B-MVA-EFFICIENCY-002`](active/RECEIPT-LLM-POC-M4B-MVA-EFFICIENCY-002.md) | gate open; incoming bytes verified |
| LLM MVA | [`REQUEST-LLM-POC-M4B-MVA-EFFICIENCY-002`](active/REQUEST-LLM-POC-M4B-MVA-EFFICIENCY-002.md) | execute efficiency gate |
| Audio Pi | [`REQUEST-POC-AUDIO-PI-MIGRATION-PUBLISH-001`](active/REQUEST-POC-AUDIO-PI-MIGRATION-PUBLISH-001.md) | authorized: reconcile and push |
| Audio Pi | [`REQUEST-POC-AUDIO-PI-STORAGE-PHASE3-001`](active/REQUEST-POC-AUDIO-PI-STORAGE-PHASE3-001.md) | open: implement and validate |
| Audio Pi | [`FEEDBACK-POC-AUDIO-PI-STORAGE-PHASE3-001`](active/FEEDBACK-POC-AUDIO-PI-STORAGE-PHASE3-001.md) | blocking: revise and return |
| LLM Pi | [`REQUEST-POC-LLM-M4B-MVA-OFFLINE-EXECUTION-001`](active/REQUEST-POC-LLM-M4B-MVA-OFFLINE-EXECUTION-001.md) | authorized: execute and report |
| LLM Pi | [`REQUEST-POC-LLM-PI-STORAGE-PHASE3-001`](active/REQUEST-POC-LLM-PI-STORAGE-PHASE3-001.md) | open: implement and validate |
| LLM Pi | [`FEEDBACK-POC-LLM-PI-STORAGE-PHASE3-001`](active/FEEDBACK-POC-LLM-PI-STORAGE-PHASE3-001.md) | blocking: revise and return |

## Archive

Closed, superseded or reference-only records are grouped without rewriting their contents:

- [`archive/audio/`](archive/audio/) — Audio POC and Pi storage history
- [`archive/llm/`](archive/llm/) — LLM POC, MVA and P9 history
- [`archive/display/`](archive/display/) — Display POC history
- [`archive/project/`](archive/project/) — cross-project roadmap, milestone and migration receipts

Archive 表示該文件不再驅動目前工作，不代表要改寫它當時的 `Status`。例如 MVA measure 001
保留原本的 `NOT DELIVERED` 記錄，但已由 active 的 efficiency 002 取代。

Search archive only when an active document or task names a specific ID or SHA:
`rg -n '<ID-or-SHA>' docs/outsource/deliveries/archive`.

## Filing rule

New actionable records go to `active/` and must state owner, status and next exit condition near the top.
When no Core action remains, move the file to the matching archive area and update this active table.
Do not create a new file merely to restate an existing status; update the active record or authoritative spec.
