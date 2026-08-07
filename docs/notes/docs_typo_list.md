外包設計文件缺失

審查範圍：外包設計基線 584aa89。核心 M1 契約大致完整；主要缺失如下。

類型

位置

缺失

語意矛盾

Ch 1 §1.8

P5 status="error" 寫成「降級後仍可用結果」，但 Ch 2 / Ch 2b 定義為「仍無可用結果」

Typo

Ch 2 §2.2

WakewordDetected 應為 WakeWordDetected

Typo

Ch 2a §1

「被 abort 的是 worker 而是 HAL」缺少「非」

Typo

Ch 4 §4.3

FatalDispatcherError 應為 FatalDispatcherError

Typo

Ch 4 §4.3

workerContractViolation 應統一為 WorkerContractViolation

驗收歧義

Ch 4 §7.4–§7.5 M1-SM-006

Ch 4 允許 discard 在收斂開始時執行，但 Test Spec 要求所有 buffer action 先等 in-flight empty；需由 Designer 統一。此矛盾亦存在正式版

可維護性

多數草節

Markdown heading、章節連結、Reviewer finding 與處置追蹤被移除或攤平，降低規格來源與收斂理由的可追溯性

版本標示

各章頁首

標為 IR-final 2026-08-01，但未保留對應 review round / 來源 commit，難以證明與正式 IR-final 等價

上述缺失應修正，但不足以解釋多數 M1 程式缺陷；Ch 3 / 4 / 5 / 10 / 11 的主要實作要求在外包文件中均已明確存在。
