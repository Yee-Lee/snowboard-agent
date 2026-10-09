# M7 review-tool verification — 2026-10-09

- Scope: reusable offline theme-review tooling and synthetic scenario playback, not M7 acceptance.
- Target: Raspberry Pi 5 Model B Rev 1.1, aarch64; retained physical 128×128 SSD1351 fixture.
- Source parent commit: `4353fbc49a54494f05122a65cb6e05c5fe229f73`; new tool/theme/fixtures were uncommitted during verification. No existing accepted candidate was rewritten.
- Transfer: isolated temporary staging; 40/40 transferred source/support files matched workstation SHA-256 at each deliberate candidate boundary. Existing Pi checkouts were unchanged.
- Custody locator: `M7-REVIEW-20261009-A`; ignored local custody contains full transfer manifest, target timing arrays and console records. No endpoints, credentials or private target paths are returned here.

## Results

| Check | Result |
|---|---|
| Workstation behavioral tests plus existing mock HAL smoke | 12 passed |
| Python compilation and document/diff checks | PASS |
| Pi mock playback | 14/14 fixtures, exit 0 |
| First physical OLED pass | 14/14 fixtures; 56 successful shows; final black intent/show, stop and owner checks PASS |
| Physical terminal controls | next/previous/replay/pause/resume/typewriter toggle/quit exercised; 5 shows; final black/stop/owner checks PASS |
| Revised same-bytes OLED pass | 14/14 fixtures; 42 successful shows; final black/stop/owner checks PASS; exit 0 |
| Shutdown after evidence retrieval | USER requested system poweroff; request accepted, subsequent SSH unavailable |

The revised pass used 2-second scenario dwell and a 10 fps ceiling. Measured synchronous HAL `show()` wall
time across 42 successful calls ranged from 65.887 to 66.002 ms. This includes
panel command/native/SPI call costs; it is not isolated SPI bus time, actual optical latency or a measured
10 fps claim. No percentile, production budget, CPU/memory or representative LLM/TTS/Audio-load claim is made.
Static duplicate frames are skipped, so presentation count is lower than elapsed-time × frame ceiling.

Pi environment: Python 3.13.5, Pillow 11.1.0, kernel `6.12.47+rpt-rpi-2712`.
Requested SPI: 4 MHz, effective speed unavailable. DC=24, RST=25, kernel-owned CS0; pre/post device ownership
was checked with `fuser`. Retained fixture SHA-256: `973229d06ae7c2734e96ce350365e61d64e2074b47166497a09976e38246d679`.
Native artifact SHA-256 matches accepted M3: `2dd44a17abd57a195674ddcf12717bbb2759580e81bbf194723507232ad50493`;
`ldd -r` found no unresolved symbols. Offline Noto Sans TC Regular/Medium bytes matched the fixed
Core `80d79d6c74ff93a40a018a03529c275287f2693e` font inventory; no native/font binary was added to Git.

## Human feedback and disposition

USER observed the first playback and reported confusing「回應中」+「已中止」and insufficient visible
reply-color change. The review prototype now displays a stop icon +「中止中」with Main「已中止」and
uses white input / pale-green reply. The revised frames were successfully presented on OLED; final human
readability, flicker/smoothness and theme-color acceptance are still pending. These changes are prototype
recommendations, not Core adoption. The interrupt projection requires a focused contract finding; it adds
no State Manager state. Multiple-source icons are synthetic and do not prove availability of a live module set.

## Verified candidate files

| File | SHA-256 at final transfer |
|---|---|
| poc_display/tools/m7_review.py | `fd79d85e9b866438dcb0d14f9c6c610f9beaa3c6c5d5a195ac641161207c132b` |
| poc_display/review/scenes.json | `5fbb32007cdff660b88ef4b938d292a48d75b11730de712ebc3d1f7c2885f5a1` |
| poc_display/review/themes/THM-baseline.json | `7caccc531f7f21bb5b7b286e84882b73a233bea6c15fff0997bdb838abf00265` |
| poc_display/tests/test_m7_review.py | `d5f1d9950c5388ba8f67a87f14ede131e9ed332920f65c975907964c99d3193c` |

Only documentation/evidence may change after this code verification; changing these files requires
appropriate repeat host/target checks. This manifest is a deliberate transfer record, not a startup check.

Repeat commands and operational limits: [review README](../../review/README.md).
M7D1 remains IN PROGRESS; product-load measurements, full Core mappings and the final Core package remain open.
