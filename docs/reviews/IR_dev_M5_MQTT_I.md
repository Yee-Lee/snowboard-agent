---
requestor: Developer
owner: Designer
status: Open
---

# IR_dev_M5_MQTT_I — read wrapper bound conflicts with 160-character acceptance

## USER decision — 2026-10-25

USER explicitly reduced the external message body limit to **32 Unicode code points**. This supersedes the 160-character design/Test Spec boundary for active M5 MQTT work. Developer implements 32 in the wire adaptor and read projector, retains the existing 320-character serialized wrapper guard, and tests 32 accepted versus 33 rejected. Designer/Tester should update the current M5 MQTT design, protocol §8, and Test Spec, including Pi `M5M-FLOW-001` length stimuli. The 160-character native POC remains historical diagnostic evidence and is not an active acceptance target.

## Blocking B1: fixed wrapper exceeds the stated bound

- Authority: `docs/implement/ch_m5_mqtt.md` §5.1 and `docs/test_spec/test_spec_M5_mqtt.md` `M5M-PRJ-001` require the exact JSON read wrapper, a 160-code-point message to pass, and `READ_MAX_WRAPPER_CODEPOINTS = 320`; the design says the serialized wrapper is at most 276 code points.
- Reproduction: with the exact instruction and compact `json.dumps(..., ensure_ascii=False, separators=(",", ":"))`, 160 ordinary CJK characters produce 341 code points for `application_result` and 334 for `notification`. A 160-character string of quotation marks produces 501 for `application_result` because JSON escaping adds one character per quote.
- Expected versus actual: the 160-character valid wire message should reach LLM; the mandatory wrapper limit rejects it before `MEASURE`. This makes `M5M-PRJ-001` and Pi `M5M-FLOW-001` mutually unsatisfiable for their documented 160-character case.
- Selected correction: set `MQTT_TEXT_MAX_CODEPOINTS = READ_MAX_TEXT_CODEPOINTS = 32`, retain `READ_MAX_WRAPPER_CODEPOINTS = 320`, and change the 160/161 boundary cases to 32/33. With the fixed exact-key wrapper, a 32-character message containing only escaped quotation marks remains below 320; a separate 320/321 projector case is now unreachable and should be removed as redundant.
- Minimum acceptance: 32-character ordinary and escaped text passes projection, 33-character text is rejected at the wire and read layers, and the matching Test Spec and design state the same bound. No Pi run or commit is claimed for this review.
