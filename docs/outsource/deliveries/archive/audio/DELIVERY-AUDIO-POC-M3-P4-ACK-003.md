# Core Team → POC Audio Team: M3 P4 Option A — Receipt ACK / Final Selection Pending

- **Delivery ID**: `DELIVERY-AUDIO-POC-M3-P4-ACK-003`
- **Reviewed POC commit**: `7497fee91ff2b8ce822ea7d5b535a54a3b594fb3`
- **Parent request**: `DELIVERY-AUDIO-POC-M3-VALIDATION-001`
- **Review role**: Core Team Designer
- **Date**: 2026-08-15
- **Decision**: `RECEIVED — FINAL SELECTION ACK NOT ISSUED`

## 1. Receipt and review conclusion

Core has received the POC's tracked P4 summaries. They report `PASS` for
P4-A01 through P4-A09 at the cited exact test commits, and the Core-approved
Option 2 clean-Pi rerun reports `PASS` for P4-A10 at
`de3b0bab4daaf47f62956d4b27f6697b3d4fa823`.

This is an acknowledgement of receipt, **not** the final selection ACK required
by `DELIVERY-AUDIO-POC-M3-VALIDATION-001` and
`DELIVERY-AUDIO-POC-M3-ACK-002`. The reviewed commit does not contain the
mandatory complete return packet, so Core cannot yet select a production
binding/resampler configuration or unblock the M3 Audio real package.

## 2. Blocking finding — required return packet is incomplete

| Contract requirement | Evidence at reviewed commit | Result |
| --- | --- | --- |
| `poc_audio/deliveries/DELIVERY-AUDIO-POC-M3-OPTION-A-VALIDATION-001.md` with the required decision table | Not present. The tracked materials contain P4 summaries and repro request/closure documents, but no complete validation delivery. | Blocking |
| `poc_audio/evidence/m3_option_a/manifest.json` | Not present. Therefore there is no single machine-readable record of the final POC SHA, hardware/wiring, config hash, runner/fixture hashes, source hashes, licenses, statuses, raw paths, time bounds, and reproduction command. | Blocking |
| `environment.txt`, sanitized config, and results with manifest-relative paths | Not present under `evidence/m3_option_a/`. A config exists elsewhere, but it is not bound to a final manifest. | Blocking |
| Locatable raw-artifact retention and fixture provenance | Summaries name Git-ignored directories, but no manifest binds their paths, hashes, retention location, and fixture-generator identity. | Blocking |
| Required selection recommendations | No single return decision table states the selected binding/resampler, exact versions/source hashes/licenses, valid-bit mapping, buffering, async model, deployment steps, rejected alternatives, and residual risks. | Blocking |

The missing information is contractual: the final selection ACK must explicitly
freeze these choices. It is not a request to commit Pi-built wheels, binaries,
or raw PCM into Core Git.

## 3. Accepted preliminary evidence

The following is recorded as reviewed preliminary evidence only:

| P4 IDs | Reviewed summary | Reported result |
| --- | --- | --- |
| A01, A10 (initial) | `P4-A01-A10-001.md` | PASS summaries; A10 subsequently superseded by clean rerun |
| A02–A05 | `P4-A02-A05-001.md` | PASS summaries |
| A06–A09 | `P4-A06-A09-001.md` | PASS summaries |
| A10 (final rerun) | `P4-A10-RERUN-002.md` | PASS summary at `de3b0bab4daaf47f62956d4b27f6697b3d4fa823` |

The retained failed controller attempt in the A10 rerun is appropriately
documented and does not itself block acceptance; the missing final return packet
does.

## 4. Minimum completion criteria

POC must return one complete, internally consistent validation packet satisfying
sections 4 and 5 of `DELIVERY-AUDIO-POC-M3-VALIDATION-001`. In particular, its
manifest must bind every P4 result to the selected final source SHA and provide
the required paths, hashes, timestamps, and reproduction command. The delivery
decision table must provide all seven required recommendations and explicitly
name any residual risk.

After that return is available, Core Designer will review the selected package
and may issue a separate final selection ACK. Core Tester must still independently
validate the resulting Core exact implementation SHA; POC evidence cannot mark
M3 Audio accepted.

## 5. Gate status

- Audio Protocol, mock/null, config schema, and fake-source seam: unchanged.
- M3 Audio direct ALSA backend, production dependency lock, valid-bit allowlist,
  buffering, and async-I/O final implementation: **Blocked by Audio P4**.
- Display, Camera, GPIO, and other M3 packages: not blocked by this finding.

> This receipt ACK records Core's disposition without modifying POC source or
> treating target-built wheels, `.so` files, raw PCM, or Git-ignored evidence as
> Core reference artifacts.
