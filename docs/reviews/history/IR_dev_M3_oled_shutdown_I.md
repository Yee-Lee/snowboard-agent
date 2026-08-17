---
requestor: "Developer"
owner: "Designer"
status: "Resolved"
---

# IR_dev_M3_oled_shutdown_I — deferred OLED blank-on-stop requirement

## Scope

This is a deferred follow-up for a **future candidate**.  It must not change
or invalidate candidate `5c9e5aac47e7f4f0dd168d8c75541438ee74f858`, which is
being submitted for direct Designer review.

## Observed issue

The SSD1351 native driver currently closes its handle in `DisplayDriver.stop()`
without presenting a final black RGB565 frame.  The panel retains its last
image after the transport closes, so an RPi target test can finish while the
OLED remains visibly on.

## Requested future behaviour

Before closing a normally started SSD1351 driver, present one full all-zero
RGB565 frame while the native handle is still valid, then close and release all
driver resources.  Repeated `stop()` remains idempotent.  A present failure
must not prevent native-handle cleanup.

## Required verification for the future candidate

1. Host bridge test proves stop emits exactly one final all-zero frame after a
   non-black frame, then closes the native handle.
2. Failure-path test proves close/release still occurs if final blank present
   fails.
3. RPi card or shutdown-runner check confirms the OLED is visually black after
   normal test completion and application shutdown.
4. The target runner performs this final display shutdown even when another
   card fails or the run is interrupted.

## Acceptance boundary

This request is Advisory for the current M3 candidate and becomes a blocking
acceptance criterion only when Designer schedules it into a future milestone
or candidate scope.

## Designer disposition — 2026-08-17

**Resolved and scheduled for M4c.** Candidate
`5c9e5aac47e7f4f0dd168d8c75541438ee74f858` remains M3 Accepted; this advisory does
not invalidate or modify its evidence.

The requested behavior is accepted for the next M4c product candidate.  The SSD1351
adapter must best-effort present exactly one all-zero RGB565 frame while the native
handle remains valid, then release the handle and related resources in a cleanup path
that still executes if presentation fails.  Repeated `stop()` remains idempotent.
Host success/failure regressions and target shutdown observation are required by the
updated Ch 2a, `display_spec.md`, and M4c acceptance criteria.  The M4 acceptance
runner must execute final Display shutdown on normal completion, failure, and
interruption.
